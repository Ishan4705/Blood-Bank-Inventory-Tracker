CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS inventory (
    hospital_id VARCHAR(50) NOT NULL,
    blood_group VARCHAR(5) NOT NULL,
    available_units INTEGER NOT NULL DEFAULT 0 CHECK (available_units >= 0),
    reserved_units INTEGER NOT NULL DEFAULT 0 CHECK (reserved_units >= 0),
    expired_units INTEGER NOT NULL DEFAULT 0 CHECK (expired_units >= 0),
    low_stock_threshold INTEGER NOT NULL DEFAULT 10 CHECK (low_stock_threshold >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (hospital_id, blood_group)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('donation', 'request', 'expiry')),
    donor_id VARCHAR(50),
    request_id VARCHAR(50),
    blood_group VARCHAR(5) NOT NULL,
    units INTEGER NOT NULL CHECK (units > 0),
    hospital_id VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    shortage_units INTEGER NOT NULL DEFAULT 0 CHECK (shortage_units >= 0),
    event_payload JSONB NOT NULL,
    event_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_event_timestamp ON transactions (event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_blood_group ON transactions (blood_group);

CREATE TABLE IF NOT EXISTS daily_summary (
    summary_date DATE NOT NULL,
    blood_group VARCHAR(5) NOT NULL,
    total_units_available INTEGER NOT NULL DEFAULT 0,
    total_units_donated INTEGER NOT NULL DEFAULT 0,
    total_units_requested INTEGER NOT NULL DEFAULT 0,
    total_units_expired INTEGER NOT NULL DEFAULT 0,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (summary_date, blood_group)
);

CREATE INDEX IF NOT EXISTS idx_daily_summary_blood_group ON daily_summary (blood_group);
