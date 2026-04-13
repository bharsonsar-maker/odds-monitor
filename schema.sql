-- ============================================================
--   ODDS MONITOR — SUPABASE SCHEMA
--   Run this in Supabase → SQL Editor → New Query → Run
-- ============================================================


-- TABLE 1: Every scan result (all matches, every 30 min)
CREATE TABLE IF NOT EXISTS scans (
    id              BIGSERIAL PRIMARY KEY,
    match_id        TEXT        NOT NULL,
    home_team       TEXT        NOT NULL,
    away_team       TEXT        NOT NULL,
    league          TEXT        NOT NULL,
    commence_time   TIMESTAMPTZ,
    home_odds       NUMERIC(5,2),
    away_odds       NUMERIC(5,2),
    draw_odds       NUMERIC(5,2),
    home_bookmaker  TEXT,
    away_bookmaker  TEXT,
    is_opportunity  BOOLEAN     DEFAULT FALSE,
    scanned_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (match_id, scanned_at)
);

-- TABLE 2: Only opportunities (both teams > 2x) — detailed log
CREATE TABLE IF NOT EXISTS opportunities (
    id                   BIGSERIAL PRIMARY KEY,
    match_id             TEXT        NOT NULL,
    home_team            TEXT        NOT NULL,
    away_team            TEXT        NOT NULL,
    league               TEXT        NOT NULL,
    commence_time        TIMESTAMPTZ,
    home_odds            NUMERIC(5,2) NOT NULL,
    away_odds            NUMERIC(5,2) NOT NULL,
    draw_odds            NUMERIC(5,2),
    profit_if_home_wins  INTEGER,
    profit_if_away_wins  INTEGER,
    loss_if_draw         INTEGER,
    spotted_at           TIMESTAMPTZ  DEFAULT NOW(),

    -- filled in after match resolves (you update manually or via script)
    result               TEXT         CHECK (result IN ('home_win','away_win','draw') OR result IS NULL),
    actual_profit        INTEGER,

    notes                TEXT
);

-- Indexes for faster dashboard queries
CREATE INDEX IF NOT EXISTS idx_scans_scanned_at      ON scans (scanned_at DESC);
CREATE INDEX IF NOT EXISTS idx_scans_league          ON scans (league);
CREATE INDEX IF NOT EXISTS idx_scans_opportunity     ON scans (is_opportunity) WHERE is_opportunity = TRUE;
CREATE INDEX IF NOT EXISTS idx_opportunities_spotted ON opportunities (spotted_at DESC);
CREATE INDEX IF NOT EXISTS idx_opportunities_result  ON opportunities (result);

-- ── Enable Row Level Security (recommended) ────────────────
ALTER TABLE scans          ENABLE ROW LEVEL SECURITY;
ALTER TABLE opportunities  ENABLE ROW LEVEL SECURITY;

-- Allow the anon key to read (for dashboard)
CREATE POLICY "Allow anon read scans"         ON scans         FOR SELECT USING (true);
CREATE POLICY "Allow anon read opportunities" ON opportunities  FOR SELECT USING (true);

-- Allow the service role key to write (for bot)
CREATE POLICY "Allow service write scans"         ON scans         FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow service write opportunities" ON opportunities  FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow service upsert scans"        ON scans         FOR UPDATE USING (true);
CREATE POLICY "Allow service update opps"         ON opportunities  FOR UPDATE USING (true);


-- ── HELPER VIEW: daily summary ─────────────────────────────
CREATE OR REPLACE VIEW daily_summary AS
SELECT
    DATE(spotted_at)                                         AS day,
    COUNT(*)                                                 AS total_opportunities,
    COUNT(*) FILTER (WHERE result IN ('home_win','away_win')) AS wins,
    COUNT(*) FILTER (WHERE result = 'draw')                  AS draws,
    COUNT(*) FILTER (WHERE result IS NULL)                   AS pending,
    SUM(actual_profit) FILTER (WHERE actual_profit IS NOT NULL) AS total_profit,
    ROUND(
        COUNT(*) FILTER (WHERE result IN ('home_win','away_win'))::NUMERIC
        / NULLIF(COUNT(*) FILTER (WHERE result IS NOT NULL), 0) * 100
    , 1)                                                     AS win_rate_pct
FROM opportunities
GROUP BY DATE(spotted_at)
ORDER BY day DESC;


-- ── SAMPLE: manually update a result after match ───────────
-- UPDATE opportunities
-- SET result = 'home_win', actual_profit = 3200
-- WHERE home_team = 'Bayern Munich' AND away_team = 'Real Madrid'
--   AND DATE(commence_time) = '2026-04-15';
