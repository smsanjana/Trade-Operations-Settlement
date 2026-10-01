# Implementation Plan: Trade Operations & Settlement

**Branch**: `001-trade-operations-settlement` | **Date**: 2026-09-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-trade-operations-settlement/spec.md`

## Summary

Build a governed Trade Operations & Settlement application in which PortAgent is the explicit
agentic runtime and workflow orchestrator for evidence interpretation, while versioned deterministic
components perform retrieval, validation, calculations, state transitions, idempotency, and policy
authorization. A responsive Next.js console gives analysts and approvers a complete cited evidence
pack, controlled approve/amend/reject actions, dual-control handling, posting reconciliation, and an
audit history that can reconstruct every outcome without rerunning a model. Ledger mutation remains
behind a separately privileged posting boundary.

Delivery is test-first: establish versioned contracts and durable state semantics, implement
deterministic controls and fail-closed workflows, integrate PortAgent agents only for ambiguous
evidence, then add the operator UI and governed posting path. Production autonomy remains disabled
until historical replay, shadow operation, risk approval, and operational readiness gates pass.

## Technical Context

**Language/Version**: Python 3.12 backend; TypeScript 5.7, Next.js 15.5, React 19.1 frontend

**Primary Dependencies**: PortAgent runtime and model adapters; a non-Pydantic ASGI HTTP boundary;
JSON Schema validation for external and inter-component contracts; Google Cloud adapters for
Pub/Sub/Eventarc, Cloud Run, Cloud Storage/Document AI, AlloyDB, BigQuery, Vertex AI/Gemini,
Model Armor, IAM, Cloud Audit Logs, and the governed posting boundary. The existing FastAPI/Pydantic
prototype dependency is not part of the approved target and must be reconciled before implementation.

**Storage**: AlloyDB for transactional case, approval, idempotency, policy, and posting state;
content-addressed Cloud Storage with approved retention controls for evidence and immutable audit
artifacts; BigQuery for audit/evaluation projections and operational measurement. Local synthetic
adapters are optional test fixtures only and are never authoritative runtime state.

**Testing**: pytest for deterministic unit, property/boundary, workflow, contract, integration,
security, replay, and recovery tests; TypeScript type checking plus component/accessibility tests
and Playwright end-to-end tests for the Next.js console; versioned historical and adversarial
evaluation sets for model-dependent behavior

**Target Platform**: Containerized Linux services on Google Cloud Run with an internal responsive
web console; enterprise identity and separately scoped service identities

**Project Type**: Web application with an event-driven backend, agentic orchestration, and a
Next.js analyst/approver frontend

**Performance Goals**: At least 95% of queue, case-detail, and decision actions return a result or
clear progress state within two seconds under the approved workload profile; at least 90% of
reviewers decide a complete-evidence case within five minutes; asynchronous workflows expose durable
progress rather than holding UI requests open

**Constraints**: PortAgent is the only agentic runtime; agents are read-only and cannot calculate,
authorize, or post; all financial outputs and policy decisions are deterministic and versioned;
all untrusted content is screened before model access; durable concurrency-safe state and stable
idempotency keys are mandatory; audit writes fail closed; dual control uses distinct identities;
posting is idempotent and separately privileged; unknown posting outcomes enter reconciliation
without blind retry; no Pydantic introduction; no production claims based on seed or in-memory data

**Scale/Scope**: Release 1 covers fee, commission, settlement-date, and SSI breaks; mandatory stock
splits and cash dividends; and extraction/deadline tracking for voluntary events without agent-made
elections. Production volume targets come from the desk-approved workload profile before pilot;
services must scale horizontally and preserve per-case ordering, unique idempotency, and consistent
policy/approval transactions at that measured load.

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

| Gate | Plan evidence | Status |
|---|---|---|
| Evidence-grounded, reconstructable decisions | Evidence is content-addressed and cited; findings, calculations, policy inputs, approvals, versions, and posting results are retained; audit is append-only and exportable to immutable retention. | PASS |
| Deterministic financial outcomes | Arithmetic, population selection, validation, confidence aggregation, idempotency, payload construction, and policy are deterministic; model output is never executable value. | PASS |
| Bounded autonomy and segregated execution | Policy gate is outside PortAgent agents; review and dual-control states are explicit; a separate identity and service own ledger posting. | PASS |
| Secure untrusted-content handling | Every external artifact is screened before agent use; content/tool allowlists, least privilege, masking, and fail-closed behavior are part of contracts and tests. | PASS |
| Test-first measurable quality | The plan starts with failing unit/contract/workflow/security tests and requires replay metrics and release blockers before autonomy. | PASS |
| Explicit architecture boundaries | Work stays within `api`, `application/agents`, `application/prompts`, `application/tools`, `application/workflows`, `config`, and `data`; no unnecessary application layer is added. | PASS |
| Durable state and versioned contracts | AlloyDB-backed transactional state, unique idempotency constraints, optimistic concurrency, immutable decisions, and JSON Schema/OpenAPI/AsyncAPI contracts are specified. | PASS |
| Safe delivery and governance | Migration, permissions, threat scenarios, observability, rollback/forward correction, staged rollout, and independent risk/security review are included. | PASS |

### Post-design re-check

The Phase 1 data model, contracts, and quickstart preserve every gate above. The design adds no
agent write path, no source-precedence rule for conflicting evidence, no mutable audit record, and
no authorization based on free-form model output. There are no constitution exceptions to track.

## Project Structure

### Documentation (this feature)

```text
specs/001-trade-operations-settlement/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- openapi.yaml
|   `-- events.asyncapi.yaml
`-- tasks.md                 # Created later by $speckit-tasks
```

### Source Code (repository root)

```text
backend/
|-- src/trade_operations_settlement/
|   |-- api/                 # Authenticated HTTP/event ingress and response mapping
|   |-- application/
|   |   |-- agents/          # PortAgent-managed evidence interpreters
|   |   |-- prompts/         # Versioned prompts
|   |   |-- tools/           # Read-only retrieval, screening, deterministic calculations,
|   |   |                    # policy, state, audit, and segregated adapter interfaces
|   |   `-- workflows/       # PortAgent workflow definitions and approval handoff
|   |-- config/              # Runtime/model/connector/policy references; no secrets
|   `-- data/                # Optional synthetic/evaluation inputs only
|-- tests/
|   |-- unit/
|   |-- contract/
|   |-- integration/
|   |-- workflow/
|   |-- security/
|   `-- replay/
`-- pyproject.toml

frontend/
|-- app/                     # Next.js routes, layouts, loading/error boundaries
|-- components/              # Queue, evidence, proposal, audit, and decision UI
|-- lib/                     # Contract types and API client
|-- tests/                   # Component, accessibility, and end-to-end tests
|-- package.json
`-- tsconfig.json
```

**Structure Decision**: Retain the approved two-project web layout and its existing backend
boundaries. Do not add a new domain, repository, service, or orchestration layer merely to mirror a
framework pattern. Durable adapters and deterministic operations are defined behind narrow
interfaces in `application/tools`; PortAgent workflow composition remains in
`application/workflows`; transport mapping remains in `api`. Existing prototype fixtures or tests
that assume seeded/in-memory state are not architectural evidence and must be replaced or confined
to explicit synthetic-test use during implementation.

## Phase 0: Research Decisions

The resolved decisions, rationales, and rejected alternatives are recorded in [research.md](research.md).
The critical outcomes are:

1. PortAgent owns agent selection and orchestration, but never policy authorization or posting.
2. Contract validation uses versioned JSON Schema at every trust boundary; the target uses a
   non-Pydantic ASGI boundary and ordinary typed Python structures.
3. Transactional state, approvals, idempotency, and posting outbox records share one durable
   transaction boundary; evidence and audit payloads are content-addressed and immutable.
4. The UI uses snapshot/version tokens and authenticated server-side identity, preventing stale
   decisions and client-supplied approver identity.
5. Posting uses an immutable instruction plus transactional outbox and reconciliation workflow;
   unknown outcomes are not blindly retried.
6. Production scale numbers are not invented: performance and resilience gates use a risk-approved
   workload profile established before pilot.

## Phase 1: Design Outputs

- [data-model.md](data-model.md) defines durable entities, invariants, relationships, security
  classification, and state transitions.
- [contracts/openapi.yaml](contracts/openapi.yaml) defines authenticated queue, case, evidence,
  decision, posting-status, and audit APIs.
- [contracts/events.asyncapi.yaml](contracts/events.asyncapi.yaml) defines intake, workflow, posting,
  acknowledgement, and reconciliation event envelopes and idempotency expectations.
- [quickstart.md](quickstart.md) defines the synthetic end-to-end verification path and the quality,
  security, audit, and release evidence required before promotion.

## Implementation Strategy

### 1. Establish contracts and durable control state

- Write failing JSON Schema/OpenAPI/AsyncAPI contract tests for supported and unsupported intake,
  strict additional-property handling, version compatibility, and non-sensitive error responses.
- Create safe migrations for case, evidence references, findings, calculations, proposals, policy
  decisions, approvals, posting instructions/results, audit events, and idempotency records.
- Enforce unique source/idempotency keys, immutable final records, actor separation, and optimistic
  case version checks in the datastore rather than only in process memory.
- Use a transactional outbox for external events and posting release. Migration rollback uses
  backward-compatible expand/migrate/contract steps or forward correction when retained audit data
  makes destructive rollback unsafe.

### 2. Implement deterministic controls before agents

- Write failing golden, property, and boundary tests for currency/date/sign/precision validation,
  fee differences, SSI rules, record-date population, ratios, fractional handling, cash in lieu,
  withholding, weakest-material-evidence confidence, and posting payload construction.
- Implement the versioned policy matrix with explicit reject, one-approval, dual-control, and
  autonomous outcomes. Missing or invalid configuration produces reviewable failure, never an
  engineering default.
- Implement decision concurrency, immutable amend history, distinct dual-control identity checks,
  posting idempotency, acknowledgement correlation, and unknown-outcome reconciliation.

### 3. Integrate screened evidence and PortAgent workflows

- Add bounded read-only connectors and persist original evidence plus hash, locator, source time,
  capture time, trust classification, and screening result before agent use.
- Apply platform and application screening; invalidate all downstream outputs if blocked content is
  detected. Treat over-redaction of material fields as a tested correctness failure.
- Add only the agents justified by semantic ambiguity: break classifier, trade evidence interpreter,
  confirmation extractor, corporate-action extractor, and source reconciliation agent.
- Make PortAgent select the smallest roster per case and require structured cited outputs. Workflow
  code rejects uncited, invalid, or stale findings before deterministic processing.

### 4. Deliver analyst and approver UI

- Replace fixture fallback in controlled environments with explicit unavailable/error states; local
  synthetic fixtures remain opt-in test data only.
- Implement queue sorting/filtering, preserved selection context, side-by-side cited evidence,
  field-level corporate-action reconciliation, deterministic proposal labeling, audit timeline,
  voluntary deadlines, and posting/reconciliation status.
- Submit approve/amend/reject using authenticated server identity and `If-Match` case version.
  Preserve form input on recoverable failures and meet keyboard, screen-reader, contrast, focus,
  and smaller-screen requirements.

### 5. Integrate governed posting and operational controls

- Deploy the posting consumer under a separate workload identity and allow only the required ledger
  operation. Agents, UI services, and PortAgent identities receive no ledger-write permission.
- Correlate source event, case, workflow run, evidence, decision, posting instruction, and external
  acknowledgement identifiers. Mask source content in operational logs.
- Add dashboards and alerts separating autonomous, human-approved, amended, rejected, conflicted,
  guardrail-blocked, reconciling, and failed outcomes.
- Exercise connector, model, policy, audit, identity, datastore, and posting outages; each must stop
  autonomous progress and leave a retryable or reviewable state.

### 6. Validate and promote in controlled stages

- Run static analysis, deterministic tests, contract tests, integration/workflow tests, security
  tests, accessibility tests, recovery exercises, and historical/adversarial replay.
- Record prompt, schema, workflow, model route, policy, calculation, dataset, and container versions
  in the release evidence.
- Promote through synthetic prototype, grounded non-production, historical replay, shadow mode, and
  limited autonomy. Risk and security owners approve thresholds, eligible types, precision gate,
  rollback, monitoring, and incident procedures.
- Block release for any unexplained posting, duplicate action, missing audit evidence, critical
  security finding, failed recovery, unreconciled posting behavior, or precision below the approved
  gate.

## Threat, Permissions, and Failure Analysis

| Risk | Required control and verification |
|---|---|
| Indirect prompt injection or tool misuse | Pre-model screening, strict tool allowlist, read-only agent identity, adversarial tests, and invalidation of derived outputs. |
| Sensitive data leakage | Field-aware redaction, role-scoped evidence retrieval, structured masked logs, negative authorization tests, and no source text in client errors. |
| Evidence conflict or stale evidence | Preserve all source values and hashes, bind findings/decisions to evidence-set versions, escalate conflict, reject stale decisions. |
| Duplicate or out-of-order delivery | Unique idempotency constraints, per-case versioning, transactional outbox/inbox records, deterministic replay tests. |
| Policy drift or unavailable configuration | Effective-dated approved policy versions, snapshot binding, fail-closed outcome, policy matrix regression. |
| Same-person dual control | Server-derived identity, role checks, datastore uniqueness constraint, and negative tests. |
| Posting timeout with unknown result | Reconciliation state, status query/callback correlation, no blind retry, operator visibility and runbook. |
| Audit persistence failure | Commit business transition only with required audit/outbox record; fail autonomous progress and alert. |
| Model or connector outage | Durable resumable workflow state and explicit retryable/reviewable status; no silent drop or fallback authorization. |

## Observability and Release Evidence

- Structured telemetry carries `correlation_id`, `case_id`, `workflow_run_id`, `evidence_set_id`,
  `policy_decision_id`, and `posting_instruction_id` where applicable.
- Metrics report processing latency and error rate by deterministic/agent stage, policy outcomes,
  decision latency, stale-write conflicts, posting acknowledgements, reconciliation age, guardrail
  blocks, and autonomous precision/false escalation/STP on versioned datasets.
- Audit records contain exact component versions and hashes but operational logs contain only
  approved metadata.
- Rollback disables autonomy first, drains or halts posting release safely, preserves pending cases,
  and uses immutable deployment/config versions. Data corrections append attributable events.

## Complexity Tracking

No constitution violations or justified complexity exceptions are required.
