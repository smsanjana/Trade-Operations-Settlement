-- Migration 001: Control state, case lifecycle, evidence, audit, policy, approval, posting, and outbox tables

CREATE TABLE IF NOT EXISTS cases (
    case_id VARCHAR(64) PRIMARY KEY,
    schema_version VARCHAR(16) NOT NULL DEFAULT '1.0.0',
    case_version INTEGER NOT NULL DEFAULT 1,
    source_system VARCHAR(64) NOT NULL,
    source_event_id VARCHAR(128) NOT NULL DEFAULT '',
    intake_idempotency_key VARCHAR(128) NOT NULL,
    correlation_id VARCHAR(128) NOT NULL DEFAULT '',
    workflow_type VARCHAR(64) NOT NULL DEFAULT 'trade_break',
    case_type VARCHAR(64) NOT NULL,
    desk_id VARCHAR(64) NOT NULL DEFAULT 'DEFAULT',
    priority VARCHAR(16) NOT NULL DEFAULT 'Normal',
    state VARCHAR(32) NOT NULL DEFAULT 'received',
    counterparty_or_custodian VARCHAR(128) NOT NULL DEFAULT '',
    instrument_id VARCHAR(64) NOT NULL DEFAULT '',
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    exposure_amount NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    deadline_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    current_evidence_set_id VARCHAR(64),
    current_proposal_id VARCHAR(64),
    current_policy_decision_id VARCHAR(64),
    failure_class VARCHAR(64),
    failure_reason_codes JSONB DEFAULT '[]'::jsonb,
    CONSTRAINT uq_source_idempotency UNIQUE (source_system, intake_idempotency_key)
);

CREATE TABLE IF NOT EXISTS inbox (
    source_system VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    case_id VARCHAR(64),
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (source_system, idempotency_key)
);

CREATE TABLE IF NOT EXISTS evidence_artifacts (
    evidence_id VARCHAR(64) PRIMARY KEY,
    content_hash VARCHAR(64) NOT NULL,
    source_name VARCHAR(128) NOT NULL,
    media_type VARCHAR(64) NOT NULL,
    retention_class VARCHAR(64) NOT NULL,
    region VARCHAR(32) NOT NULL,
    storage_reference TEXT NOT NULL DEFAULT '',
    trust_classification VARCHAR(32) NOT NULL DEFAULT 'untrusted',
    legal_hold BOOLEAN NOT NULL DEFAULT FALSE,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evidence_case_links (
    case_id VARCHAR(64) NOT NULL REFERENCES cases(case_id),
    evidence_id VARCHAR(64) NOT NULL REFERENCES evidence_artifacts(evidence_id),
    purpose VARCHAR(64) NOT NULL,
    locator TEXT NOT NULL,
    is_screened BOOLEAN NOT NULL DEFAULT FALSE,
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    screening_metadata JSONB DEFAULT '{}'::jsonb,
    PRIMARY KEY (case_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS evidence_sets (
    evidence_set_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(case_id),
    evidence_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS deterministic_calculations (
    calculation_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(case_id),
    calculation_type VARCHAR(64) NOT NULL,
    rule_version VARCHAR(32) NOT NULL,
    inputs JSONB NOT NULL,
    intermediate_steps JSONB NOT NULL DEFAULT '{}'::jsonb,
    outputs JSONB NOT NULL,
    rounding_mode VARCHAR(32) NOT NULL DEFAULT 'ROUND_HALF_UP',
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS proposals (
    proposal_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(case_id),
    proposal_version INTEGER NOT NULL DEFAULT 1,
    account_id VARCHAR(64) NOT NULL,
    direction VARCHAR(16) NOT NULL,
    amount NUMERIC(18, 4) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    value_date DATE NOT NULL,
    reason_code VARCHAR(64) NOT NULL,
    calculation_id VARCHAR(64) REFERENCES deterministic_calculations(calculation_id),
    evidence_set_id VARCHAR(64) REFERENCES evidence_sets(evidence_set_id),
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    invalidation_reasons JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS policy_configurations (
    policy_version VARCHAR(32) PRIMARY KEY,
    desk_id VARCHAR(64) NOT NULL,
    confidence_threshold NUMERIC(5, 4) NOT NULL,
    auto_post_limit NUMERIC(18, 4) NOT NULL,
    dual_control_threshold NUMERIC(18, 4) NOT NULL,
    eligible_case_types JSONB NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS policy_decisions (
    decision_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(case_id),
    policy_version VARCHAR(32) NOT NULL REFERENCES policy_configurations(policy_version),
    outcome VARCHAR(32) NOT NULL,
    reason_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    inputs_snapshot JSONB NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS approval_cycles (
    approval_cycle_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(case_id),
    case_version INTEGER NOT NULL,
    proposal_id VARCHAR(64) NOT NULL REFERENCES proposals(proposal_id),
    policy_decision_id VARCHAR(64) NOT NULL REFERENCES policy_decisions(decision_id),
    required_approvals INTEGER NOT NULL DEFAULT 1,
    state VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS approval_decisions (
    decision_id VARCHAR(64) PRIMARY KEY,
    approval_cycle_id VARCHAR(64) NOT NULL REFERENCES approval_cycles(approval_cycle_id),
    approver_id VARCHAR(64) NOT NULL,
    action VARCHAR(16) NOT NULL,
    slot_number INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    amended_amount NUMERIC(18, 4),
    decided_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_cycle_slot UNIQUE (approval_cycle_id, slot_number)
);

CREATE TABLE IF NOT EXISTS posting_instructions (
    instruction_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(case_id),
    proposal_id VARCHAR(64) NOT NULL REFERENCES proposals(proposal_id),
    idempotency_key VARCHAR(128) NOT NULL UNIQUE,
    payload_hash VARCHAR(64) NOT NULL,
    classification VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'created',
    external_reference VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS posting_results (
    result_id VARCHAR(64) PRIMARY KEY,
    instruction_id VARCHAR(64) NOT NULL REFERENCES posting_instructions(instruction_id),
    status VARCHAR(32) NOT NULL,
    external_reference VARCHAR(128),
    acknowledgement_payload JSONB DEFAULT '{}'::jsonb,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_events (
    audit_event_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(case_id),
    sequence_number INTEGER NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    actor VARCHAR(64) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    correlation_id VARCHAR(128) NOT NULL DEFAULT '',
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_case_audit_seq UNIQUE (case_id, sequence_number)
);

CREATE TABLE IF NOT EXISTS outbox (
    event_id VARCHAR(64) PRIMARY KEY,
    channel VARCHAR(128) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
