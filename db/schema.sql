-- SEO AI Employee — PostgreSQL Schema
-- Run: psql $DATABASE_URL -f schema.sql

-- ─────────────────────────────────────────────────────────────────────────────
-- EXTENSIONS
-- ─────────────────────────────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- for text search

-- ─────────────────────────────────────────────────────────────────────────────
-- GOOGLE SEARCH CONSOLE DATA
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS gsc_data (
    id              BIGSERIAL PRIMARY KEY,
    page            TEXT        NOT NULL,
    query           TEXT        NOT NULL,
    clicks          INT         NOT NULL DEFAULT 0,
    impressions     INT         NOT NULL DEFAULT 0,
    ctr             NUMERIC(6,3) NOT NULL DEFAULT 0,
    position        NUMERIC(6,1) NOT NULL DEFAULT 0,
    recorded_at     DATE        NOT NULL DEFAULT CURRENT_DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (page, query, recorded_at)
);

CREATE INDEX IF NOT EXISTS idx_gsc_data_page ON gsc_data (page);
CREATE INDEX IF NOT EXISTS idx_gsc_data_query ON gsc_data (query);
CREATE INDEX IF NOT EXISTS idx_gsc_data_recorded_at ON gsc_data (recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_gsc_data_position ON gsc_data (position);

-- ─────────────────────────────────────────────────────────────────────────────
-- KEYWORD RESEARCH
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS keywords (
    id              BIGSERIAL PRIMARY KEY,
    keyword         TEXT        NOT NULL UNIQUE,
    volume          INT,
    cpc             NUMERIC(8,2),
    competition     NUMERIC(4,3),
    kd              INT,          -- keyword difficulty 0-100
    intent          TEXT,         -- informational/commercial/transactional/navigational
    location_code   INT          DEFAULT 2840,
    language_code   TEXT         DEFAULT 'en',
    last_updated    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS keyword_clusters (
    id                  BIGSERIAL   PRIMARY KEY,
    primary_keyword     TEXT        NOT NULL UNIQUE,
    primary_volume      INT,
    supporting_keywords JSONB       NOT NULL DEFAULT '[]',
    intent              TEXT,
    content_type        TEXT,
    avg_kd              NUMERIC(5,1),
    total_volume        INT,
    member_count        INT         DEFAULT 1,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kc_primary_keyword ON keyword_clusters (primary_keyword);
CREATE INDEX IF NOT EXISTS idx_kc_intent ON keyword_clusters (intent);
CREATE INDEX IF NOT EXISTS idx_kc_total_volume ON keyword_clusters (total_volume DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- CONTENT CALENDAR
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS content_calendar (
    id                  BIGSERIAL   PRIMARY KEY,
    week                INT         NOT NULL,
    day                 TEXT,
    publish_date        DATE,
    title               TEXT        NOT NULL,
    primary_keyword     TEXT        NOT NULL,
    supporting_keywords JSONB       DEFAULT '[]',
    intent              TEXT,
    content_type        TEXT,
    target_word_count   INT         DEFAULT 1500,
    priority            TEXT        DEFAULT 'medium',
    status              TEXT        DEFAULT 'planned',  -- planned/in_progress/written/published/cancelled
    article_id          BIGINT      REFERENCES articles(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (publish_date, primary_keyword)
);

CREATE INDEX IF NOT EXISTS idx_cc_publish_date ON content_calendar (publish_date);
CREATE INDEX IF NOT EXISTS idx_cc_status ON content_calendar (status);

-- ─────────────────────────────────────────────────────────────────────────────
-- ARTICLES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS articles (
    id                  BIGSERIAL   PRIMARY KEY,
    title               TEXT        NOT NULL,
    content             TEXT,
    meta_title          TEXT,
    meta_description    TEXT,
    schema_markup       JSONB,
    primary_keyword     TEXT,
    slug                TEXT,
    word_count          INT         DEFAULT 0,
    status              TEXT        DEFAULT 'draft',
      -- draft / publishing / published / execution_failed / needs_review
    published_url       TEXT,
    published_at        TIMESTAMPTZ,
    cms_type            TEXT,       -- wordpress/webflow/shopify
    cms_id              TEXT,       -- ID in the CMS
    internal_links      JSONB       DEFAULT '[]',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_articles_status ON articles (status);
CREATE INDEX IF NOT EXISTS idx_articles_primary_keyword ON articles (primary_keyword);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_title_trgm ON articles USING gin (title gin_trgm_ops);

-- ─────────────────────────────────────────────────────────────────────────────
-- TECHNICAL AUDIT
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS audit_runs (
    id              BIGSERIAL   PRIMARY KEY,
    audit_type      TEXT        NOT NULL DEFAULT 'manual',  -- monthly/weekly/manual
    audit_date      DATE        NOT NULL DEFAULT CURRENT_DATE,
    pages_crawled   INT         DEFAULT 0,
    total_issues    INT         DEFAULT 0,
    health_score    INT,        -- 0-100
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (audit_type, audit_date)
);

CREATE TABLE IF NOT EXISTS audit_issues (
    id              BIGSERIAL   PRIMARY KEY,
    audit_run_id    BIGINT      REFERENCES audit_runs(id) ON DELETE CASCADE,
    url             TEXT        NOT NULL,
    issue_type      TEXT        NOT NULL,
      -- missing_meta_title / missing_meta_description / missing_alt_text /
      -- broken_link / duplicate_meta_title / redirect_chain_too_long /
      -- missing_canonical / meta_title_too_long / meta_description_too_long /
      -- lcp_poor / cls_poor
    severity        TEXT        NOT NULL DEFAULT 'medium',  -- critical/high/medium/low
    details         TEXT,
    proposed_fix    TEXT,
    status          TEXT        NOT NULL DEFAULT 'open',    -- open/in_progress/resolved/wont_fix
    resolved_at     TIMESTAMPTZ,
    resolved_by     TEXT,       -- agent name or human
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (url, issue_type)
);

CREATE INDEX IF NOT EXISTS idx_ai_status ON audit_issues (status);
CREATE INDEX IF NOT EXISTS idx_ai_severity ON audit_issues (severity);
CREATE INDEX IF NOT EXISTS idx_ai_issue_type ON audit_issues (issue_type);
CREATE INDEX IF NOT EXISTS idx_ai_url ON audit_issues (url);

-- ─────────────────────────────────────────────────────────────────────────────
-- SEO ANALYSIS RUNS
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS seo_analysis_runs (
    id                  BIGSERIAL   PRIMARY KEY,
    agent               TEXT        NOT NULL,
    analysis_date       DATE        NOT NULL DEFAULT CURRENT_DATE,
    ranking_drops       INT         DEFAULT 0,
    ctr_opportunities   INT         DEFAULT 0,
    quick_wins          INT         DEFAULT 0,
    raw_data            JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (agent, analysis_date)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- META PROPOSALS (title/description updates)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS meta_proposals (
    id                  BIGSERIAL   PRIMARY KEY,
    url                 TEXT        NOT NULL,
    current_title       TEXT,
    proposed_title      TEXT,
    current_description TEXT,
    proposed_description TEXT,
    confidence          TEXT        DEFAULT 'medium',   -- high/medium/low
    reason              TEXT,
    status              TEXT        DEFAULT 'pending_review',
      -- pending_review / approved / applied / rejected
    applied_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mp_status ON meta_proposals (status);

-- ─────────────────────────────────────────────────────────────────────────────
-- SEO PRIORITIES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS seo_priorities (
    id              BIGSERIAL   PRIMARY KEY,
    action          TEXT        NOT NULL,
    reason          TEXT,
    priority        TEXT        DEFAULT 'medium',
    source_agent    TEXT,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sp_priority ON seo_priorities (priority);
CREATE INDEX IF NOT EXISTS idx_sp_completed ON seo_priorities (completed_at);

-- ─────────────────────────────────────────────────────────────────────────────
-- REPORTS
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS reports (
    id              BIGSERIAL   PRIMARY KEY,
    period          TEXT        NOT NULL,   -- weekly/monthly
    report_date     DATE        NOT NULL,
    file_path       TEXT,
    content_html    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_period ON reports (period, report_date DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- COMPETITOR DATA
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS competitor_keywords (
    id              BIGSERIAL   PRIMARY KEY,
    domain          TEXT        NOT NULL,
    keyword         TEXT        NOT NULL,
    position        INT,
    url             TEXT,
    volume          INT,
    kd              INT,
    recorded_at     DATE        NOT NULL DEFAULT CURRENT_DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (domain, keyword, recorded_at)
);

CREATE INDEX IF NOT EXISTS idx_ck_domain ON competitor_keywords (domain);
CREATE INDEX IF NOT EXISTS idx_ck_keyword ON competitor_keywords (keyword);

-- ─────────────────────────────────────────────────────────────────────────────
-- USEFUL VIEWS
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW v_ranking_summary_7d AS
SELECT
    page,
    SUM(clicks) AS total_clicks,
    SUM(impressions) AS total_impressions,
    ROUND(AVG(ctr)::numeric, 2) AS avg_ctr,
    ROUND(AVG(position)::numeric, 1) AS avg_position
FROM gsc_data
WHERE recorded_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY page
ORDER BY total_clicks DESC;

CREATE OR REPLACE VIEW v_open_issues_by_severity AS
SELECT
    severity,
    issue_type,
    COUNT(*) AS count
FROM audit_issues
WHERE status = 'open'
GROUP BY severity, issue_type
ORDER BY
    CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END,
    count DESC;

CREATE OR REPLACE VIEW v_content_pipeline AS
SELECT
    cc.publish_date,
    cc.title,
    cc.primary_keyword,
    cc.status AS calendar_status,
    a.status AS article_status,
    a.word_count,
    a.published_url
FROM content_calendar cc
LEFT JOIN articles a ON cc.article_id = a.id
ORDER BY cc.publish_date;
