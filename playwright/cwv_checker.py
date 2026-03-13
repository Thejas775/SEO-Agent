#!/usr/bin/env python3
"""
Core Web Vitals measurement using Playwright.
Measures LCP, CLS, FID/INP, TTFB for given URLs.
"""

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


CWV_JS = """
() => {
  return new Promise((resolve) => {
    const metrics = {
      lcp: null,
      cls: 0,
      fcp: null,
      ttfb: null,
      load_time: null,
    };

    // LCP
    const lcpObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      if (entries.length > 0) {
        metrics.lcp = entries[entries.length - 1].startTime;
      }
    });
    try { lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true }); } catch(e) {}

    // CLS
    const clsObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (!entry.hadRecentInput) {
          metrics.cls += entry.value;
        }
      }
    });
    try { clsObserver.observe({ type: 'layout-shift', buffered: true }); } catch(e) {}

    // Navigation timing
    const navEntry = performance.getEntriesByType('navigation')[0];
    if (navEntry) {
      metrics.ttfb = navEntry.responseStart - navEntry.requestStart;
      metrics.load_time = navEntry.loadEventEnd - navEntry.startTime;
      metrics.fcp = navEntry.responseEnd;
    }

    // Wait for LCP to settle
    setTimeout(() => {
      metrics.cls = Math.round(metrics.cls * 1000) / 1000;
      resolve(metrics);
    }, 3000);
  });
}
"""


def measure_url(page, url: str, device: str = "desktop") -> dict:
    from playwright.sync_api import TimeoutError as PWTimeout

    result = {"url": url, "device": device, "error": None}

    try:
        start = __import__("time").time()
        response = page.goto(url, wait_until="networkidle", timeout=30000)
        load_time = round((__import__("time").time() - start) * 1000, 0)

        result["status_code"] = response.status if response else 0
        result["load_time_ms"] = load_time

        # Evaluate CWV
        cwv = page.evaluate(CWV_JS)
        result["lcp_ms"] = round(cwv.get("lcp") or 0, 0)
        result["cls"] = cwv.get("cls", 0)
        result["ttfb_ms"] = round(cwv.get("ttfb") or 0, 0)
        result["fcp_ms"] = round(cwv.get("fcp") or 0, 0)

        # Scoring
        result["lcp_status"] = (
            "good" if result["lcp_ms"] <= 2500
            else "needs_improvement" if result["lcp_ms"] <= 4000
            else "poor"
        )
        result["cls_status"] = (
            "good" if result["cls"] <= 0.1
            else "needs_improvement" if result["cls"] <= 0.25
            else "poor"
        )
        result["ttfb_status"] = (
            "good" if result["ttfb_ms"] <= 800
            else "needs_improvement" if result["ttfb_ms"] <= 1800
            else "poor"
        )

        # Overall pass/fail
        result["passes_cwv"] = (
            result["lcp_status"] == "good"
            and result["cls_status"] == "good"
            and result["ttfb_status"] == "good"
        )

    except PWTimeout:
        result["error"] = "timeout"
    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(description="Core Web Vitals Checker")
    parser.add_argument("--url", help="Single URL to check")
    parser.add_argument("--urls-file", help="File with one URL per line")
    parser.add_argument("--device", choices=["desktop", "mobile", "both"], default="desktop")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    urls = []
    if args.url:
        urls = [args.url]
    elif args.urls_file:
        with open(args.urls_file) as f:
            urls = [line.strip() for line in f if line.strip()]
    else:
        sys.exit("ERROR: --url or --urls-file required")

    devices = ["desktop", "mobile"] if args.device == "both" else [args.device]
    results = []

    with sync_playwright() as pw:
        for device_name in devices:
            print(f"Measuring {len(urls)} URLs on {device_name}...")
            browser = pw.chromium.launch(headless=True)

            if device_name == "mobile":
                context = browser.new_context(
                    viewport={"width": 390, "height": 844},
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
                    device_scale_factor=3,
                )
            else:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                )

            page = context.new_page()

            for url in urls:
                print(f"  {url} ({device_name})...", end="", flush=True)
                result = measure_url(page, url, device_name)
                results.append(result)
                status = "✓" if result.get("passes_cwv") else "✗"
                lcp = result.get("lcp_ms", "?")
                print(f" {status} LCP={lcp}ms")

            browser.close()

    # Summary
    passed = sum(1 for r in results if r.get("passes_cwv"))
    poor_lcp = [r for r in results if r.get("lcp_status") == "poor"]

    output = {
        "total_measured": len(results),
        "passed_cwv": passed,
        "failed_cwv": len(results) - passed,
        "poor_lcp_pages": len(poor_lcp),
        "results": results,
    }

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults: {passed}/{len(results)} passed CWV")
    print(f"Output saved: {args.output}")


if __name__ == "__main__":
    main()
