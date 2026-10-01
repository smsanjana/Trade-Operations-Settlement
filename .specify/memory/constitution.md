<!--
Sync Impact Report
- Version change: unratified empty scaffold -> 1.0.0
- Modified principles: N/A (initial constitution)
- Added principles:
  - I. Evidence-Grounded and Auditable Decisions
  - II. Deterministic Financial Outcomes
  - III. Bounded Autonomy and Segregated Execution
  - IV. Secure-by-Design Data and Tool Access
  - V. Test-First, Measurable Quality
- Added sections:
  - Architecture and Security Constraints
  - Development Workflow and Delivery Gates
- Removed sections: None
- Follow-up TODOs: None
-->
# Trade Operations & Settlement Constitution

## Core Principles

### I. Evidence-Grounded and Auditable Decisions
Every proposed amendment, escalation, approval, rejection, and autonomous action MUST be
traceable to retained source evidence. Unstructured evidence MUST be cited at the smallest
practical unit, including message identity for chat and page or field provenance for documents.
The audit record MUST contain the input and content hashes, agent and prompt versions, model
routing, policy configuration, decision trace, calculated values, and final outcome needed to
reconstruct the decision without rerunning a model. Later agreements may supersede earlier ones
only when the evidence explicitly establishes that sequence. Contradictory sources MUST be
reported as a conflict and escalated; an agent MUST NOT silently choose a preferred source.

Rationale: Settlement actions must remain defensible after models, prompts, source systems, and
market conditions change.

### II. Deterministic Financial Outcomes
Agents MAY interpret ambiguous evidence, classify cases, and extract facts into strict schemas.
All table lookups, entitlement calculations, fee differences, rounding, withholding, population
selection, threshold comparisons, idempotency checks, and ledger payload construction MUST be
performed by deterministic, versioned code. Model prose or model-generated arithmetic MUST NOT
be used as an executable value. Deterministic components MUST validate currencies, dates, signs,
precision, reason codes, account identifiers, and schema versions before a proposal can advance.
The booked trade and other systems of record remain authoritative; this application proposes or
posts governed amendments and MUST NOT become an alternative book of record.

Rationale: Every financial figure and eligibility decision must be reproducible, testable, and
independent of probabilistic model behaviour.

### III. Bounded Autonomy and Segregated Execution
Autonomy MUST be decided by a deterministic policy gate outside every agent. The gate MUST read
validated structured fields only and MUST enforce desk-owned confidence and value limits, event
eligibility, evidence conflicts, guardrail outcomes, and dual-control rules. Unknown break types,
missing required evidence, low confidence, source conflicts, voluntary events, unsupported event
types, or any agent-requested escalation MUST enter the approver queue; no case may disappear.
Agents and their tools MUST have no ledger write path. Posting MUST occur through a governed API
under a separate workload identity after an auto-post decision or the required named approvals.
Approval is the posting event, dual control requires two distinct approvers, and a decided case
MUST reject replay or re-decision.

Rationale: Safe straight-through processing depends on enforceable limits and separation of
reasoning, authorization, and execution.

### IV. Secure-by-Design Data and Tool Access
All chat, confirmations, issuer documents, SWIFT messages, vendor content, and retrieved context
MUST be treated as untrusted. Content MUST pass platform guardrails and application-level
sanitisation before model use; detected prompt injection MUST fail closed and invalidate any
derived proposal. Redaction and screening MUST preserve financially meaningful dates, ratios,
amounts, identifiers, and source boundaries, with over-redaction treated as a correctness defect.
Every agent, service, connector, MCP tool, datastore, and human role MUST use least privilege,
explicit allowlists, scoped credentials, and environment separation. Secrets and sensitive data
MUST NOT be committed, embedded in prompts, or emitted in unrestricted logs. Encryption,
retention, access logging, regional controls, and data classification MUST follow approved bank
policy, with CMEK and VPC Service Controls used where the target environment requires them.

Rationale: Third-party evidence and high-impact financial tools make injection resistance,
privacy, and platform-enforced access control part of functional correctness.

### V. Test-First, Measurable Quality
Behaviour MUST be specified by an executable failing test before implementation or defect repair.
The suite MUST cover deterministic calculations, schema validation, policy boundaries,
idempotency and replay, workflow state transitions, approval and dual-control invariants,
connector and posting contracts, evidence provenance, and complete end-to-end scenarios. Security
tests MUST include indirect prompt injection, tool misuse, data leakage, malformed documents, and
over-redaction. Historical resolved cases MUST be replayed for every change to models, prompts,
retrieval, extraction, policy logic, or financial calculations. Release decisions MUST prioritize
precision of autonomous postings; throughput or straight-through rate MUST NOT compensate for an
unmet precision gate. Tests MUST be deterministic by default, and model-dependent evaluations
MUST use versioned datasets, recorded configuration, and explicit acceptance thresholds.

Rationale: The system earns autonomy through repeatable evidence that it acts correctly and
declines to act when evidence or controls are insufficient.

## Architecture and Security Constraints

- The PortAgent application MUST preserve explicit boundaries between agent definitions, prompts,
  tools, workflows, APIs, configuration, and data adapters. Domain and policy code MUST remain
  independent of model SDKs and cloud transport details.
- A workflow step MUST be an agent only when it must weigh evidence that can reasonably support
  more than one interpretation. Retrieval, bounded queries, validation, arithmetic, state
  transitions, and policy enforcement MUST remain deterministic services.
- Inter-component contracts MUST use versioned, strictly validated schemas. A schema or contract
  change MUST include compatibility analysis, migration handling, and contract tests.
- Event consumers MUST use stable idempotency keys. Durable workflow and approval state MUST be
  stored in a concurrency-safe datastore; process memory, agent sessions, and model memory MUST
  NOT be treated as authoritative transaction state.
- Evidence artifacts MUST be retained, content-addressed where practical, and linked to the case
  record. Derived golden copies MUST retain every source value and mark each field as agreed,
  partial, or conflicting.
- External systems MUST be integrated through read-only connectors by default. Write-capable tools
  MUST be isolated from agents, deny-by-default, allowlisted to the minimum operation, and exposed
  only through governed application services.
- The target architecture MAY use Google Cloud services identified by the PRD, including Pub/Sub,
  Eventarc, Cloud Run, Document AI, BigQuery, AlloyDB, Vertex AI services, Apigee, Workflows,
  Model Armor, IAM, Cloud Audit Logs, and CMEK. Product code MUST access them behind interfaces so
  local synthetic execution and controlled substitution remain possible.
- Observability MUST use correlation and case identifiers across ingestion, reasoning, policy,
  approval, and posting. Metrics MUST separate autonomous, human-approved, amended, rejected,
  conflicted, and guardrail-blocked outcomes. Logs MUST be structured and tamper-evident at the
  audit boundary while applying approved masking and access restrictions.
- Failure MUST be safe: unavailable evidence, connectors, models, policy configuration, audit
  persistence, approval state, or posting acknowledgements MUST stop autonomous progress and
  produce a retryable or reviewable state without duplicate posting.

## Development Workflow and Delivery Gates

1. Each change MUST begin with a specification that identifies the user outcome, data and trust
   boundaries, deterministic versus agent responsibilities, failure modes, audit evidence, and
   applicable autonomy rules.
2. Plans MUST document affected schemas, migrations, connectors, permissions, threat scenarios,
   observability, rollback, and test strategy. Any added agent or model call MUST justify why
   deterministic code is insufficient and account for latency, cost, and failure handling.
3. Implementation MUST follow red-green-refactor and keep changes small enough for meaningful
   review. Prompts, policy configuration, evaluation datasets, and schemas MUST be versioned with
   the code that consumes them.
4. Pull requests MUST pass formatting, static analysis, unit tests, contract tests, integration
   tests, security tests, workflow tests, and the relevant model evaluation or historical replay.
   Reviewers MUST verify this constitution explicitly and reject unexplained complexity or weakened
   controls.
5. Changes affecting autonomous eligibility, policy thresholds, posting payloads, financial
   calculations, approval semantics, sensitive-data handling, or write-path permissions MUST
   receive independent domain/risk and security review in addition to engineering review.
6. Environments MUST progress through synthetic prototype, grounded non-production validation,
   historical replay, shadow operation, and limited autonomy. Production autonomy MUST NOT be
   enabled until risk owners approve measured precision, desk-owned thresholds, eligible case
   types, monitoring, rollback, and incident procedures.
7. Deployments MUST be reproducible, use immutable version identifiers, run database migrations
   safely, support rollback or forward correction, and preserve audit continuity. CI/CD identities
   MUST be least-privileged and MUST NOT expose production secrets to untrusted builds.
8. A release MUST be blocked by any unexplained posting, precision below its approved gate,
   duplicate-action defect, missing audit evidence, unresolved critical security finding, failed
   recovery exercise, or inability to reconcile posting acknowledgements.

## Governance

This constitution is the highest-priority engineering policy for the project. Specifications,
plans, tasks, reviews, runbooks, and releases MUST demonstrate compliance. Where another project
document conflicts with this constitution, the constitution governs unless and until it is amended.

Amendments require a written proposal describing the change, rationale, affected controls,
compatibility impact, migration or remediation plan, and validation evidence. Approval requires the
engineering owner and product owner; amendments that affect autonomy, financial calculations,
posting, approval, security, privacy, or audit additionally require the relevant domain/risk and
security owners. Approved amendments MUST update this file, its Sync Impact Report, and any
affected specifications before dependent implementation is merged.

Constitution versions follow semantic versioning. MAJOR versions remove or incompatibly redefine
a principle or governance obligation. MINOR versions add a principle or materially expand an
obligation. PATCH versions clarify wording without changing required behaviour. Ratification date
records the first adoption; Last Amended records the latest approved change.

Every feature review and pull request MUST include a constitution check. At each release candidate,
the engineering owner MUST record evidence that mandatory tests and delivery gates passed, while
the product and risk owners MUST confirm the approved autonomy scope and thresholds. Exceptions
MUST be time-bounded, name an accountable owner, document compensating controls and expiry, and
receive the same approvals as the rule being waived. An exception MUST NOT bypass ledger-write
segregation, immutable audit evidence, named approval, or dual control.

**Version**: 1.0.0 | **Ratified**: 2026-09-22 | **Last Amended**: 2026-09-22
