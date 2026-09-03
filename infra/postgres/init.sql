CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS assistant_audit_event (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    request_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    customer_ref_hash TEXT NOT NULL,
    event_type TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_assistant_audit_request_id
    ON assistant_audit_event(request_id);
CREATE INDEX IF NOT EXISTS ix_assistant_audit_conversation_id
    ON assistant_audit_event(conversation_id);
CREATE INDEX IF NOT EXISTS ix_assistant_audit_created_at
    ON assistant_audit_event(created_at DESC);
