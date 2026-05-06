CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS config;
CREATE SCHEMA IF NOT EXISTS ai_core;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS config.cameras (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    rtsp_url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'inactive',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS config.zones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id UUID NOT NULL REFERENCES config.cameras(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    polygon JSONB NOT NULL,
    active BOOL NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS config.webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL,
    secret TEXT NOT NULL,
    active BOOL NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_core.customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vector VECTOR(512) NOT NULL,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS customers_vector_hnsw_idx
    ON ai_core.customers USING hnsw (vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE TABLE IF NOT EXISTS analytics.visits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID,
    zone_id UUID,
    camera_id UUID,
    entered_at TIMESTAMPTZ NOT NULL,
    left_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS analytics.events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    customer_id UUID,
    zone_id UUID,
    camera_id UUID,
    track_id TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'pending',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    webhook_response JSONB
);
