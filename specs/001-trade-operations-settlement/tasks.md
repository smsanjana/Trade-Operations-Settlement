---

description: "Dependency-ordered implementation tasks for Trade Operations & Settlement"
---

# Tasks: Trade Operations & Settlement

**Input**: Design documents from `specs/001-trade-operations-settlement/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`,
`quickstart.md`, and `.specify/memory/constitution.md`

**Tests**: Tests are mandatory because the constitution requires red-green-refactor and executable
failing tests before implementation or defect repair. Within each story, complete the listed tests
first and verify that they fail for the intended reason.

**Organization**: Tasks are grouped by user story. P1 control stories are ordered so bounded
autonomy exists before workflows consume it. Each story remains independently testable at its
checkpoint.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: May run in parallel because it targets different files and has no dependency on an
  incomplete task in the same phase.
- **[Story]**: Maps the task to its specification user story.
- Every task names the exact file or directory it changes.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Align the prototype scaffold with the approved non-Pydantic architecture and establish
the test and deployment structure.

- [X] T001 Replace FastAPI, Pydantic, and Pydantic Settings with the selected non-Pydantic ASGI, JSON Schema, PostgreSQL, migration, and test dependencies in `backend/pyproject.toml` and regenerate `backend/uv.lock`
- [X] T002 Create unit, contract, integration, workflow, security, replay, and fixture package structure under `backend/tests/`
- [X] T003 [P] Add frontend component, accessibility, and Playwright test dependencies and scripts in `frontend/package.json` and regenerate `frontend/npm-shrinkwrap.json`
- [X] T004 [P] Add non-secret synthetic environment keys and explicit no-ledger adapter selections in `.env.synthetic.example`
- [X] T005 Configure API, frontend, transactional database, and synthetic object-store services with health checks in `compose.yaml`
- [X] T006 [P] Update backend and frontend container builds for the approved runtime and non-root execution in `backend/Dockerfile` and `frontend/Dockerfile`
- [X] T007 Update lint, typecheck, unit, contract, integration, security, replay, frontend, and artifact-validation stages in `bitbucket-pipelines.yml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish strict contracts, durable transaction semantics, security context, audit,
and PortAgent runtime boundaries used by every story.

**CRITICAL**: No user-story implementation starts until this phase passes.

### Tests first

- [X] T008 [P] Add OpenAPI and AsyncAPI parse, lint, version, strict-property, decimal, currency, and decision-identity contract tests in `backend/tests/contract/test_spec_contracts.py`
- [X] T009 [P] Add failing datastore tests for intake uniqueness, optimistic case versions, immutable audit ordering, transactional outbox creation, and rollback behavior in `backend/tests/integration/test_control_state.py`
- [X] T010 [P] Add failing authentication and role-scope tests for analyst, approver, risk, auditor, agent, and posting identities in `backend/tests/security/test_identity_boundaries.py`
- [X] T011 [P] Add failing evidence-store tests for content hashing, role-scoped retrieval, retention metadata, and immutable artifact references in `backend/tests/integration/test_evidence_store.py`

### Implementation

- [X] T012 Define JSON Schema loading, version dispatch, strict validation, and canonical decimal/date normalization in `backend/src/trade_operations_settlement/application/tools/schema_validation.py`
- [X] T013 [P] Define ordinary typed Python records for case, evidence, workflow, finding, calculation, proposal, policy, approval, posting, and audit data in `backend/src/trade_operations_settlement/application/tools/records.py`
- [X] T014 Create expand-phase SQL migrations for cases, evidence links/sets, workflow and agent runs, calculations, proposals, policy, approvals, posting, audit, inbox, and outbox tables in `backend/migrations/001_control_state.sql`
- [X] T015 Implement transactional case versioning, idempotent inbox, immutable append operations, and outbox persistence in `backend/src/trade_operations_settlement/application/tools/state_store.py`
- [X] T016 [P] Implement content-addressed evidence storage and authorized metadata/content retrieval interfaces in `backend/src/trade_operations_settlement/application/tools/evidence_store.py`
- [X] T017 [P] Implement enterprise identity extraction, role/desk/region authorization, and service-identity denial rules in `backend/src/trade_operations_settlement/api/security.py`
- [X] T018 Implement append-only audit writing with per-case sequence and integrity chaining in `backend/src/trade_operations_settlement/application/tools/audit.py`
- [X] T019 [P] Implement structured correlation logging, masking, and base outcome metrics in `backend/src/trade_operations_settlement/config/observability.py`
- [X] T020 Define the PortAgent runtime adapter, allowlisted read-only tool catalog, durable workflow checkpoint contract, and explicit absence of ledger tools in `backend/src/trade_operations_settlement/application/workflows/runtime.py`
- [X] T021 Implement the ASGI application, dependency health checks, non-sensitive problem responses, and API version routing in `backend/src/trade_operations_settlement/api/main.py`
- [X] T022 Replace hand-maintained frontend transport shapes with contract-aligned types, ETag handling, and explicit unavailable errors in `frontend/lib/api.ts` and `frontend/lib/types.ts`

**Checkpoint**: Contracts reject invalid data; durable state and audit invariants pass; authenticated
roles are enforced; PortAgent has no ledger path; the UI cannot silently substitute fixture data.

---

## Phase 3: User Story 5 - Enforce Bounded Autonomy (Priority: P1)

**Goal**: Decide reject, approval, dual-control, or autonomous eligibility through a deterministic,
versioned policy gate outside all agents.

**Independent Test**: Run the policy matrix over type, evidence completeness, confidence, value,
conflict, guardrail result, agent escalation, policy validity, and dual-control thresholds and verify
the exact outcome, reasons, and retained snapshot.

### Tests first

- [X] T023 [P] [US5] Add exhaustive policy decision-table and boundary tests in `backend/tests/unit/test_policy_gate.py`
- [X] T024 [P] [US5] Add workflow tests proving free-form reasoning is excluded and missing, invalid, expired, or unavailable policy fails closed in `backend/tests/workflow/test_policy_evaluation.py`
- [X] T025 [P] [US5] Add security tests proving guardrail blocks invalidate dependent proposals and deny all autonomous outcomes in `backend/tests/security/test_guardrail_policy.py`

### Implementation

- [X] T026 [P] [US5] Define approved policy configuration and gate-input JSON Schemas in `backend/src/trade_operations_settlement/application/tools/schemas/policy.schema.json`
- [X] T027 [US5] Implement effective-dated policy loading, overlap/expiry validation, and absence-of-default behavior in `backend/src/trade_operations_settlement/config/policy.py`
- [X] T028 [US5] Implement deterministic confidence aggregation, hard-block precedence, threshold evaluation, outcomes, and stable reason codes in `backend/src/trade_operations_settlement/application/tools/policy_gate.py`
- [X] T029 [US5] Persist immutable policy input/configuration snapshots and audit events within the case transaction in `backend/src/trade_operations_settlement/application/workflows/policy_evaluation.py`
- [X] T030 [US5] Add policy outcome and reason-code presentation to the contract-aligned case snapshot in `backend/src/trade_operations_settlement/api/cases.py`

**Checkpoint**: The full policy matrix is reproducible without a model and no missing or malformed
configuration can authorize autonomy.

---

## Phase 4: User Story 1 - Resolve Supported Trade Breaks (Priority: P1) - MVP

**Goal**: Ingest, deduplicate, investigate, calculate, and correctly route release-1 fee,
commission, settlement-date, and SSI breaks.

**Independent Test**: Submit controlled supported, unsupported, duplicated, superseded-term,
conflicting, and injection-bearing trade cases; verify one case, cited findings, deterministic values,
and the correct policy state.

### Tests first

- [X] T031 [P] [US1] Add intake contract tests for valid, invalid, duplicate, out-of-order, unknown, and unsupported settlement exception events in `backend/tests/contract/test_trade_intake.py`
- [X] T032 [P] [US1] Add golden and boundary tests for fee/commission differences, SSI checks, dates, signs, currencies, precision, confidence, and amendment payloads in `backend/tests/unit/test_trade_calculations.py`
- [X] T033 [P] [US1] Add agent-output tests for break classification, chronology, explicit supersession, citations, confidence, and chat-confirm conflicts in `backend/tests/workflow/test_trade_agents.py`
- [X] T034 [P] [US1] Add end-to-end workflow tests for supported, unsupported, conflict, duplicate, missing-evidence, connector-failure, and guardrail-blocked cases in `backend/tests/workflow/test_trade_break_workflow.py`

### Implementation

- [X] T035 [P] [US1] Define strict break-classification, trade-finding, confirmation-extraction, citation, and conflict schemas in `backend/src/trade_operations_settlement/application/agents/schemas/trade.schema.json`
- [X] T036 [P] [US1] Add versioned break-classifier, trade-evidence, and confirmation prompts in `backend/src/trade_operations_settlement/application/prompts/trade_break/`
- [X] T037 [US1] Implement PortAgent-managed break classifier, trade evidence interpreter, and confirmation extractor with schema/citation enforcement in `backend/src/trade_operations_settlement/application/agents/trade_break.py`
- [X] T038 [P] [US1] Implement bounded booked-trade, SSI, confirmation, and chat retrieval with evidence-set capture in `backend/src/trade_operations_settlement/application/tools/trade_retrieval.py`
- [X] T039 [P] [US1] Implement deterministic trade validation, fee/commission difference, SSI comparison, weakest-evidence confidence, and proposal construction in `backend/src/trade_operations_settlement/application/tools/trade_calculations.py`
- [X] T040 [US1] Implement deduplicated settlement-exception ingestion and reviewable unsupported-type handling in `backend/src/trade_operations_settlement/api/intake.py`
- [X] T041 [US1] Compose screening, minimum-agent selection, cited reconciliation, deterministic processing, proposal invalidation, policy evaluation, and durable recovery in `backend/src/trade_operations_settlement/application/workflows/trade_break.py`
- [X] T042 [US1] Implement queue/detail views, cited side-by-side chat/confirmation evidence, deterministic proposal labeling, and conflict suppression in `frontend/components/operations-console.tsx`

**Checkpoint**: User Story 1 passes independently and is the first operational value slice, with
policy controls from User Story 5 as its safety prerequisite.

---

## Phase 5: User Story 2 - Review and Decide an Escalated Case (Priority: P1)

**Goal**: Let authorized reviewers inspect a complete version-bound evidence pack and record an
immutable approve, amend, or reject decision.

**Independent Test**: Open an escalated case, exercise all three decisions, required fields,
unauthorized access, stale versions, and replay; verify exact snapshot attribution and no state
change on refusal.

### Tests first

- [ ] T043 [P] [US2] Add OpenAPI contract tests for queue/detail/evidence and decision success, 403, 409, and 422 responses in `backend/tests/contract/test_review_api.py`
- [ ] T044 [P] [US2] Add approval-cycle tests for authenticated identity, immutable snapshot binding, amend succession, rejection, replay, and optimistic concurrency in `backend/tests/unit/test_approval_workflow.py`
- [ ] T045 [P] [US2] Add frontend component and accessibility tests for evidence review, separate decision controls, required inputs, focus, status messages, and preserved form data in `frontend/tests/review-decision.spec.tsx`

### Implementation

- [ ] T046 [P] [US2] Define approval-cycle, decision-command, amendment, and decision-result schemas in `backend/src/trade_operations_settlement/application/tools/schemas/approval.schema.json`
- [ ] T047 [US2] Implement immutable approval-cycle creation, authenticated decisions, amendment successor proposals, policy reevaluation, rejection, replay denial, and stale-version checks in `backend/src/trade_operations_settlement/application/workflows/approval.py`
- [ ] T048 [US2] Implement cursor-paginated queue, case review snapshot, role-scoped evidence, and ETag responses in `backend/src/trade_operations_settlement/api/cases.py`
- [ ] T049 [US2] Implement approve/amend/reject endpoint mapping without client-authored approver identity in `backend/src/trade_operations_settlement/api/decisions.py`
- [ ] T050 [P] [US2] Implement stable queue filters/sorts and selection-context preservation in `frontend/components/case-queue.tsx`
- [ ] T051 [P] [US2] Implement version-bound evidence, proposal, policy-reason, and workflow-trace review panels in `frontend/components/case-review.tsx`
- [ ] T052 [US2] Implement approve, amend, and reject dialogs with `If-Match`, snapshot references, confirmation, stale refresh, and recoverable-input preservation in `frontend/components/decision-dialog.tsx`
- [ ] T053 [US2] Wire queue/detail/evidence/decision calls and non-sensitive error mapping through `frontend/lib/api.ts`

**Checkpoint**: A reviewer completes approve, amend, or reject from one evidence pack; identity,
version, and audit attribution are enforced server-side.

---

## Phase 6: User Story 3 - Process Mandatory Corporate Actions (Priority: P1)

**Goal**: Reconcile mandatory stock-split and cash-dividend notices into a field-level golden copy
and calculate account/tax-lot entitlements deterministically.

**Independent Test**: Process agreeing, partially populated, materially conflicting, incomplete
position, fractional, and jurisdictional-withholding scenarios and verify provenance, calculations,
and safe routing.

### Tests first

- [ ] T054 [P] [US3] Add contract tests for mandatory corporate-action intake and strict extraction/golden-copy structures in `backend/tests/contract/test_corporate_action_contracts.py`
- [ ] T055 [P] [US3] Add golden/property tests for record-date population, split ratios, per-lot fractions, cash in lieu, withholding, rounding, and incomplete inputs in `backend/tests/unit/test_entitlement_calculations.py`
- [ ] T056 [P] [US3] Add agent tests for field extraction, per-source provenance, agreement/partial/conflict status, and no source precedence in `backend/tests/workflow/test_corporate_action_agents.py`
- [ ] T057 [P] [US3] Add end-to-end mandatory-event workflow tests for agreeing sources, conflicts, incomplete snapshots, unsupported types, and failures in `backend/tests/workflow/test_mandatory_corporate_action.py`

### Implementation

- [ ] T058 [P] [US3] Define corporate-action finding, source-value, golden-copy, position, tax-lot, and entitlement schemas in `backend/src/trade_operations_settlement/application/agents/schemas/corporate_action.schema.json`
- [ ] T059 [P] [US3] Add versioned corporate-action extraction and semantic-reconciliation prompts in `backend/src/trade_operations_settlement/application/prompts/corporate_action/`
- [ ] T060 [US3] Implement PortAgent-managed corporate-action extractor and semantic source reconciler with field-level citations in `backend/src/trade_operations_settlement/application/agents/corporate_action.py`
- [ ] T061 [P] [US3] Implement bounded announcement, record-date position, and tax-lot retrieval with snapshot completeness validation in `backend/src/trade_operations_settlement/application/tools/corporate_action_retrieval.py`
- [ ] T062 [P] [US3] Implement deterministic golden-copy construction without source precedence in `backend/src/trade_operations_settlement/application/tools/golden_copy.py`
- [ ] T063 [P] [US3] Implement split, dividend, fractional, cash-in-lieu, withholding, rounding, and per-lot calculation records in `backend/src/trade_operations_settlement/application/tools/entitlements.py`
- [ ] T064 [US3] Compose screening, extraction, reconciliation, population, calculation, policy, escalation, and durable failure states in `backend/src/trade_operations_settlement/application/workflows/mandatory_corporate_action.py`
- [ ] T065 [US3] Implement golden-copy source comparison, entitlement breakdown, provenance, and conflict presentation in `frontend/components/corporate-action-review.tsx`

**Checkpoint**: Mandatory stock splits and cash dividends are reproducible at account/tax-lot level;
material conflicts or incomplete positions cannot progress autonomously.

---

## Phase 7: User Story 6 - Complete Dual Control and Governed Posting (Priority: P1)

**Goal**: Require distinct approvers for high-value cases and release exactly one immutable posting
instruction to a separately privileged, idempotent posting service.

**Independent Test**: Exercise first approval, identity reuse, distinct second approval, duplicate
instruction delivery, success, rejection, timeout, unknown outcome, and late acknowledgement.

### Tests first

- [ ] T066 [P] [US6] Add transactional dual-control tests for approval slots, same-identity refusal, stale cycles, and exactly-one instruction creation in `backend/tests/integration/test_dual_control.py`
- [ ] T067 [P] [US6] Add posting contract tests for immutable payloads, authorization fingerprints, idempotent replay, acknowledgements, rejection, and unknown outcomes in `backend/tests/contract/test_posting_contract.py`
- [ ] T068 [P] [US6] Add workflow/recovery tests proving no blind retry and correct late-acknowledgement reconciliation in `backend/tests/workflow/test_posting_reconciliation.py`

### Implementation

- [ ] T069 [P] [US6] Define posting-instruction, posting-result, authorization-fingerprint, and reconciliation schemas in `backend/src/trade_operations_settlement/application/tools/schemas/posting.schema.json`
- [ ] T070 [US6] Add datastore constraints and transaction operations for distinct approval actors and one instruction per authorization in `backend/migrations/002_dual_control_posting.sql`
- [ ] T071 [US6] Extend approval workflow to allocate immutable approval slots and create the instruction/audit/outbox records atomically in `backend/src/trade_operations_settlement/application/workflows/approval.py`
- [ ] T072 [P] [US6] Implement separately credentialed posting transport, original-result replay, and status inquiry operations in `backend/src/trade_operations_settlement/application/tools/posting.py`
- [ ] T073 [US6] Implement outbox dispatch, acknowledgement correlation, rejection, outcome-unknown, and reconciliation transitions in `backend/src/trade_operations_settlement/application/workflows/posting.py`
- [ ] T074 [US6] Implement posting-result event intake and idempotent reconciliation API handling in `backend/src/trade_operations_settlement/api/posting_results.py`
- [ ] T075 [P] [US6] Implement dual-control identity guidance and first-approval display in `frontend/components/dual-control.tsx`
- [ ] T076 [US6] Implement ready, submitted, posted, rejected, failed, and reconciling status presentation with external references in `frontend/components/posting-status.tsx`

**Checkpoint**: Two distinct approvals release one instruction; posting replay cannot create a
second ledger action; unknown outcomes remain visible until reconciled.

---

## Phase 8: User Story 4 - Track Voluntary Corporate Actions (Priority: P2)

**Goal**: Extract voluntary-event options, population, and deadlines while reserving every election
for an authorized human desk actor.

**Independent Test**: Submit a voluntary event, approach its deadline, record/link a human election,
and attempt an agent/service election; verify priority, uninstructed accounts, attribution, and denial.

### Tests first

- [ ] T077 [P] [US4] Add workflow tests proving all voluntary events route to the desk regardless of confidence and prioritize inside the deadline window in `backend/tests/workflow/test_voluntary_corporate_action.py`
- [ ] T078 [P] [US4] Add API/security tests for valid human instructions, missing data, stale versions, and denied agent/service identities in `backend/tests/security/test_voluntary_elections.py`
- [ ] T079 [P] [US4] Add frontend tests for options, deadlines, impacted/uninstructed accounts, urgency, and decision accessibility in `frontend/tests/voluntary-event.spec.tsx`

### Implementation

- [ ] T080 [P] [US4] Define voluntary option, deadline, impacted-account, and human election schemas in `backend/src/trade_operations_settlement/application/tools/schemas/voluntary_event.schema.json`
- [ ] T081 [US4] Compose extraction, population visibility, deadline calculation, mandatory desk routing, and durable tracking in `backend/src/trade_operations_settlement/application/workflows/voluntary_corporate_action.py`
- [ ] T082 [US4] Implement human-only immutable election recording and account instruction status in `backend/src/trade_operations_settlement/application/workflows/elections.py`
- [ ] T083 [US4] Implement `POST /cases/{caseId}/desk-instructions` with authenticated actor and ETag checks in `backend/src/trade_operations_settlement/api/desk_instructions.py`
- [ ] T084 [P] [US4] Implement deadline, option, impacted-account, and uninstructed-account views in `frontend/components/voluntary-event-review.tsx`
- [ ] T085 [US4] Add deadline/type filters and visible urgency ordering to `frontend/components/case-queue.tsx`

**Checkpoint**: Every voluntary event remains human-controlled, deadline-visible, and attributable;
no agent or service identity can elect.

---

## Phase 9: User Story 7 - Reconstruct Every Decision (Priority: P2)

**Goal**: Let an authorized auditor reconstruct autonomous, reviewed, conflicted, blocked, and
posting outcomes from immutable retained records without rerunning a model.

**Independent Test**: Reconstruct representative outcomes under full and metadata-only access and
verify hashes, locators, component versions, deterministic steps, policy, decisions, and posting.

### Tests first

- [ ] T086 [P] [US7] Add reconstruction tests for autonomous, approved, amended, rejected, conflicted, blocked, and reconciled cases in `backend/tests/integration/test_audit_reconstruction.py`
- [ ] T087 [P] [US7] Add audit authorization tests for full-content, metadata-only, desk/region mismatch, and sensitive-excerpt denial in `backend/tests/security/test_audit_access.py`
- [ ] T088 [P] [US7] Add frontend timeline tests for chronology, component versions, restricted evidence, and posting outcome in `frontend/tests/audit-timeline.spec.tsx`

### Implementation

- [ ] T089 [US7] Implement deterministic reconstruction projection across evidence, agent, calculation, policy, approval, posting, and integrity-chain records in `backend/src/trade_operations_settlement/application/tools/reconstruction.py`
- [ ] T090 [US7] Implement cursor-paginated audit history and role-filtered reconstruction responses in `backend/src/trade_operations_settlement/api/audit.py`
- [ ] T091 [P] [US7] Implement immutable audit-artifact export and authorized BigQuery projection interfaces in `backend/src/trade_operations_settlement/application/tools/audit_export.py`
- [ ] T092 [P] [US7] Implement chronological workflow/agent/deterministic/policy/human/posting timeline in `frontend/components/audit-timeline.tsx`
- [ ] T093 [US7] Implement restricted-evidence metadata fallbacks and authorized evidence drill-down in `frontend/components/evidence-viewer.tsx`
- [ ] T094 [US7] Document reconstruction evidence, access review, retention coordination, and integrity verification in `docs/runbooks/audit-reconstruction.md`

**Checkpoint**: Every sampled outcome is explainable from retained records alone, while unauthorized
evidence content remains undisclosed.

---

## Phase 10: User Story 8 - Validate Changes Before Release (Priority: P2)

**Goal**: Replay versioned historical/adversarial cases and enforce release blockers for every
controlled component change.

**Independent Test**: Change each controlled category, run the relevant evaluation set, and inject
precision, posting, audit, security, recovery, and reconciliation failures; verify release denial.

### Tests first

- [ ] T095 [P] [US8] Add evaluation-schema and dataset-version contract tests in `backend/tests/contract/test_evaluation_contract.py`
- [ ] T096 [P] [US8] Add replay metric tests for autonomous precision, straight-through rate, false escalation, and per-outcome reporting in `backend/tests/replay/test_metrics.py`
- [ ] T097 [P] [US8] Add release-gate tests for unexplained/duplicate posting, missing audit, critical security, failed recovery, unresolved reconciliation, and low precision in `backend/tests/replay/test_release_gate.py`
- [ ] T098 [P] [US8] Add adversarial datasets for indirect injection, tool misuse, leakage, malformed content, and over-redaction under `backend/src/trade_operations_settlement/data/evaluations/security/`

### Implementation

- [ ] T099 [P] [US8] Define evaluation-set, evaluation-run, metric, control-failure, and release-decision schemas in `backend/src/trade_operations_settlement/application/tools/schemas/evaluation.schema.json`
- [ ] T100 [US8] Implement version-pinned historical/adversarial replay and expected-versus-actual comparison in `backend/src/trade_operations_settlement/application/workflows/evaluation.py`
- [ ] T101 [US8] Implement separate precision, straight-through, false-escalation, security, recovery, and outcome metrics in `backend/src/trade_operations_settlement/application/tools/evaluation_metrics.py`
- [ ] T102 [US8] Implement deterministic release eligibility with mandatory blocker reason codes in `backend/src/trade_operations_settlement/application/tools/release_gate.py`
- [ ] T103 [US8] Publish immutable evaluation and release evidence artifacts from `backend/src/trade_operations_settlement/application/tools/evaluation_export.py`
- [ ] T104 [US8] Wire controlled-change detection, replay suites, artifact retention, and release blocking in `bitbucket-pipelines.yml`

**Checkpoint**: Every controlled change has versioned evaluation evidence and no mandatory blocker
can be overridden by throughput or straight-through performance.

---

## Phase 11: Polish and Cross-Cutting Concerns

**Purpose**: Verify cross-story security, resilience, usability, observability, deployment, and
governance before any controlled promotion.

- [ ] T105 [P] Add indirect-injection, unauthorized-tool, data-leakage, malformed-document, over-redaction, and log-masking end-to-end tests in `backend/tests/security/test_end_to_end_security.py`
- [ ] T106 [P] Add failure-injection and recovery tests for evidence, connector, model, policy, identity, datastore, audit, approval, posting, and acknowledgement outages in `backend/tests/integration/test_failure_recovery.py`
- [ ] T107 [P] Add keyboard, screen-reader, focus, contrast, responsive-layout, and complete reviewer-journey tests in `frontend/tests/operations-console.e2e.ts`
- [ ] T108 Add outcome, latency, queue-age, guardrail, stale-write, posting, reconciliation, and evaluation dashboards/alerts in `deploy/observability/trade-operations.yaml`
- [ ] T109 Add least-privilege API, PortAgent, connector, auditor, CI, and separate posting workload identity definitions in `deploy/iam/trade-operations.yaml`
- [ ] T110 Add expand/migrate/contract database rollout, autonomy-disable rollback, outbox drain, reconciliation, and forward-correction procedures in `docs/runbooks/deployment-and-rollback.md`
- [ ] T111 Add synthetic, grounded non-production, historical replay, shadow, limited-autonomy, incident, and risk/security approval gates in `docs/runbooks/release-readiness.md`
- [ ] T112 Execute every scenario and command in `specs/001-trade-operations-settlement/quickstart.md` and record results in `specs/001-trade-operations-settlement/validation-report.md`

**Checkpoint**: All desired stories and cross-cutting controls pass; production autonomy remains
disabled until the named domain/risk and security owners approve measured readiness.

---

## Dependencies and Execution Order

### Phase dependencies

- **Phase 1 - Setup**: Starts immediately.
- **Phase 2 - Foundational**: Depends on Phase 1 and blocks every story.
- **Phase 3 - US5 Bounded Autonomy**: Depends on Phase 2 and is the safety prerequisite for US1,
  US3, US4, and US6.
- **Phase 4 - US1 Trade Breaks**: Depends on US5 for policy routing.
- **Phase 5 - US2 Review and Decision**: Depends on Phase 2 and consumes reviewable cases; it may
  proceed alongside US1 once its test fixtures are available.
- **Phase 6 - US3 Mandatory Corporate Actions**: Depends on US5; otherwise independent of US1.
- **Phase 7 - US6 Dual Control and Posting**: Depends on US2 and US5; integrates authorization with
  the separate posting boundary.
- **Phase 8 - US4 Voluntary Events**: Depends on Phase 2 and the shared corporate-action extraction
  contract from US3; it does not depend on posting.
- **Phase 9 - US7 Audit Reconstruction**: Depends on the stories selected for reconstruction and can
  be developed incrementally as their event records stabilize.
- **Phase 10 - US8 Release Validation**: Depends on all stories included in a release candidate.
- **Phase 11 - Polish**: Depends on all desired story phases.

### User-story dependency graph

```text
Setup -> Foundation -> US5 Bounded Autonomy -> US1 Trade Breaks
                    |                       -> US3 Mandatory Corporate Actions -> US4 Voluntary Events
                    |-> US2 Review/Decision -> US6 Dual Control/Posting
                    |                       -> US7 Audit Reconstruction
                    `-----------------------------------------------> US8 Release Validation

US1, US3, US4, US5, and US6 records also feed US7 and US8.
```

### Within each user story

1. Write the story's tests and confirm they fail for the expected missing behavior.
2. Add or extend strict schemas and immutable records.
3. Implement deterministic tools and durable transitions before agent or UI integration.
4. Implement PortAgent agents only for ambiguous interpretation steps.
5. Add API and UI behavior.
6. Run the independent test and constitution controls at the checkpoint.

## Parallel Opportunities

- T003-T004 and T006 can run in parallel after T001 establishes dependency direction.
- T008-T011 can run in parallel; T013, T016-T017, and T019 can run in parallel after their failing
  tests exist.
- All test tasks marked `[P]` within a story can be authored simultaneously.
- US1 and US2 can proceed in parallel after US5 supplies stable policy outcomes and shared case
  fixtures; US3 can proceed in parallel with both.
- US7 reconstruction projections can be added story by story while US4 and US6 are completed.
- Frontend components marked `[P]` can proceed against contract fixtures while backend workflows
  are implemented, but integration tests must use the real contract boundary before checkpoint signoff.

## Parallel Examples by User Story

### US5

- Policy table tests: `backend/tests/unit/test_policy_gate.py`
- Fail-closed workflow tests: `backend/tests/workflow/test_policy_evaluation.py`
- Guardrail security tests: `backend/tests/security/test_guardrail_policy.py`

### US1

- Intake contracts: `backend/tests/contract/test_trade_intake.py`
- Deterministic calculations: `backend/tests/unit/test_trade_calculations.py`
- Agent and workflow behavior: `backend/tests/workflow/test_trade_agents.py`

### US2

- Review API contracts: `backend/tests/contract/test_review_api.py`
- Approval concurrency: `backend/tests/unit/test_approval_workflow.py`
- Decision UI accessibility: `frontend/tests/review-decision.spec.tsx`

### US3

- Corporate-action contracts: `backend/tests/contract/test_corporate_action_contracts.py`
- Entitlement calculations: `backend/tests/unit/test_entitlement_calculations.py`
- Extractor/reconciler behavior: `backend/tests/workflow/test_corporate_action_agents.py`

### US6

- Dual-control transactions: `backend/tests/integration/test_dual_control.py`
- Posting contracts: `backend/tests/contract/test_posting_contract.py`
- Reconciliation workflow: `backend/tests/workflow/test_posting_reconciliation.py`

### US4

- Voluntary workflow: `backend/tests/workflow/test_voluntary_corporate_action.py`
- Election authorization: `backend/tests/security/test_voluntary_elections.py`
- Deadline UI: `frontend/tests/voluntary-event.spec.tsx`

### US7

- Reconstruction completeness: `backend/tests/integration/test_audit_reconstruction.py`
- Audit authorization: `backend/tests/security/test_audit_access.py`
- Audit UI: `frontend/tests/audit-timeline.spec.tsx`

### US8

- Evaluation contracts: `backend/tests/contract/test_evaluation_contract.py`
- Replay metrics: `backend/tests/replay/test_metrics.py`
- Mandatory blockers: `backend/tests/replay/test_release_gate.py`

## Implementation Strategy

### MVP scope

The smallest safe MVP is **Phase 1 + Phase 2 + US5 + US1**. US5 is included because User Story 1
cannot safely route an autonomous or review outcome without the external deterministic policy gate.
The MVP demonstrates supported trade-break intake, evidence interpretation, deterministic proposal
construction, conflict/unsupported escalation, deduplication, and bounded policy routing. It does
not enable production autonomy or ledger posting.

### Incremental delivery

1. Complete setup and foundation; verify contracts, durable state, identity, evidence, audit, and
   PortAgent boundaries.
2. Complete US5 and US1; validate the no-posting MVP in an isolated synthetic environment.
3. Add US2 to enable governed human decisions.
4. Add US3 and US4 for mandatory and voluntary corporate-action operations.
5. Add US6 for separately privileged dual-control posting and reconciliation.
6. Add US7 and US8 to complete reconstruction and release governance.
7. Complete cross-cutting validation, then promote only through the approved staged rollout.

### Parallel team strategy

After Phase 2 and US5 stabilize:

- Team A implements US1 trade breaks.
- Team B implements US2 approval and reviewer UI.
- Team C implements US3 corporate actions.
- Shared control ownership reviews policy, audit, identity, and posting invariants across all teams.

## Notes

- No task introduces Pydantic, an agent ledger-write path, or an in-memory/seeded production store.
- `backend/src/trade_operations_settlement/data/` is limited to versioned synthetic/evaluation data.
- Existing prototype fixture fallback and seed/in-memory assumptions must not survive controlled
  integration or production profiles.
- All money and rates cross contracts as canonical decimal strings and use fixed-precision decimal
  arithmetic internally.
- Every material transition commits its audit and outbox records transactionally.
- Commit after each task or coherent red-green-refactor group and re-run the affected constitution
  gates at every checkpoint.
