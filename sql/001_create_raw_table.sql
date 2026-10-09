CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.nyc_311_requests (
    unique_key      TEXT PRIMARY KEY,
    created_date    TIMESTAMPTZ NOT NULL,
    closed_date     TIMESTAMPTZ,
    complaint_type  TEXT,
    agency          TEXT,
    borough         TEXT,
    raw_record      JSONB NOT NULL,
    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_311_created_date
    ON raw.nyc_311_requests (created_date);

CREATE INDEX IF NOT EXISTS idx_311_complaint_type
    ON raw.nyc_311_requests (complaint_type);

CREATE INDEX IF NOT EXISTS idx_311_borough
    ON raw.nyc_311_requests (borough);
