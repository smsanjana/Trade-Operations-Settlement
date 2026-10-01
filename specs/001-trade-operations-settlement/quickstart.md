# Quickstart: Design and End-to-End Validation

This quickstart defines the implementation verification path for the Trade Operations & Settlement
feature. It is not evidence that the current prototype already has durable adapters, seeded cases,
PortAgent workflows, or production connectors.

## 1. Prerequisites

- Python 3.12 and the project-selected non-Pydantic ASGI stack
- Node.js 22 and the repository's Next.js dependencies
- PortAgent runtime/model adapter available in a controlled development environment
- A transactional datastore compatible with the AlloyDB target semantics
- Object storage for content-addressed synthetic evidence and audit artifacts
- Explicit synthetic implementations for source, model, evidence, identity, policy, audit, and
  posting boundaries
- Approved test-only policy values, identities, rule tables, and evaluation datasets

Do not use production credentials, evidence, counterparties, accounts, policy thresholds, or ledger
endpoints. Synthetic fixtures are opt-in test inputs; they are not authoritative runtime state.

## 2. Contract gate

Before application implementation, verify that:

1. `contracts/openapi.yaml` and `contracts/events.asyncapi.yaml` parse and lint.
2. Positive and negative fixtures validate against JSON Schema 2020-12.
3. Unknown required enums, unknown schema versions, malformed decimal strings, invalid currencies,
   missing idempotency keys, and extra prohibited properties fail closed.
4. Frontend types and API client tests are checked against the contract authority rather than
   maintained as a conflicting source of truth.
5. Decision requests contain no client-authored approver identity.

After the contract-test harness is implemented, run:

```powershell
Set-Location backend
uv sync --extra dev --frozen
uv run pytest tests/contract -q
```

## 3. Start an explicitly synthetic environment

Configure the local environment so that every adapter identifies itself as synthetic and the
posting boundary cannot reach a real ledger. Start the backend and frontend only after identity,
policy, audit, datastore, evidence-store, and PortAgent health checks pass.

Using the implementation-provided synthetic environment file, the expected launch command is:

```powershell
docker compose --env-file .env.synthetic up --build
```

`.env.synthetic` must contain only non-sensitive test values and must explicitly select synthetic
connectors plus a no-ledger posting adapter. The implementation must refuse this profile outside a
local or isolated test environment.

Required startup assertions:

- production or shared-environment mode refuses in-memory authoritative state;
- missing/expired policy refuses autonomous processing;
- missing audit persistence refuses material state transitions;
- the API shows a clear unavailable/error state rather than silently substituting UI fixtures;
- PortAgent and agent identities have no posting credential or ledger route.

## 4. Intake and idempotency

Submit a supported fee exception twice with the same `(source_system, idempotency_key)`.

Expected evidence:

- both deliveries resolve to one `case_id` and one case version sequence;
- the second delivery appends a deduplication audit event but starts no second workflow;
- at most one posting authorization fingerprint can exist;
- an invalid envelope is rejected without creating or advancing a case;
- an unsupported break type is retained in a reviewable state and has no drafted proposal.

## 5. Trade-break workflow

Run three synthetic cases:

1. A later chat message explicitly supersedes an earlier fee and matches the confirmation.
2. Chat and confirmation disagree on settlement date.
3. Evidence contains an indirect instruction intended to manipulate the model or tools.

Expected evidence:

- PortAgent selects only the agents required by each case;
- the final chat agreement has a message citation and chronological rationale;
- a valid amendment is calculated deterministically with retained decimal inputs, rule version,
  intermediate values, rounding, and output;
- chat-confirmation conflict shows both sources, suppresses an actionable autonomous proposal, and
  enters review;
- the injection case is blocked before actionable interpretation, dependent outputs are invalidated,
  and no unauthorized tool call occurs.

## 6. Mandatory corporate action

Run an agreeing-source cash dividend or stock split and then a material-conflict variant.

Expected evidence:

- all announcements remain retained and every golden-copy field shows source values, agreement
  state, confidence, and provenance;
- record-date population is resolved from a complete authoritative snapshot by account and tax lot;
- entitlement, fractional treatment, cash in lieu, withholding, and rounding are deterministic and
  reproducible;
- a conflicting material field or missing/incomplete position snapshot stops autonomous progress;
- no source is silently preferred.

## 7. Voluntary event

Submit a voluntary event with multiple options, impacted accounts, and a deadline inside the
configured priority window.

Expected evidence:

- the case always routes to the desk regardless of confidence;
- the UI displays deadline, options, impacted accounts, and accounts without an instruction;
- only an authenticated authorized human can record or link an election;
- an agent or service identity attempting the same operation receives a denial and causes no change.

## 8. Policy matrix

Execute the complete approved matrix across case type, evidence completeness, confidence, conflict,
guardrail result, value, escalation flag, policy availability, and dual-control threshold.

Expected evidence:

- each result is one of reject, one approval, dual control, or autonomous authorization;
- hard blocks and escalation conditions take precedence over value limits;
- the complete structured input, effective configuration version, outcome, reasons, and timestamp
  are retained;
- missing, invalid, expired, or unavailable configuration never falls back to an engineering default.

## 9. Human decision and concurrency

Open a review snapshot, record approve, amend, and reject cases, and submit a stale copy of one
decision.

Expected evidence:

- actor identity comes from authentication and is bound to the exact evidence, proposal, policy,
  approval-cycle, and case versions;
- amend requires a note and corrected value, retains the original proposal, reruns deterministic
  validation/policy, and creates a new approval cycle;
- reject requires a note and prevents the rejected proposal from posting;
- stale or replayed commands return a conflict, append no decision, and preserve entered UI data;
- the audit trail is append-only.

## 10. Dual control

Approve a dual-control case once, attempt a second approval with the same identity, then approve with
a different authorized identity.

Expected evidence:

- the first approval and reviewed snapshot are visible to the second approver;
- identity reuse is rejected transactionally with no posting instruction;
- the distinct second approval creates exactly one immutable posting instruction and outbox record;
- both approvals reference the same evidence, proposal, policy decision, and cycle.

## 11. Posting and reconciliation

Exercise acknowledgement, rejection, duplicate delivery, timeout, and late acknowledgement.

Expected evidence:

- only the separately privileged posting service reaches the ledger adapter;
- success displays the external reference and autonomous/human-approved classification;
- duplicate instruction delivery returns the original result without another ledger action;
- timeout enters `reconciliation_required` and emits no blind replacement;
- a late matched acknowledgement resolves the original instruction and retains the full chronology.

## 12. Audit reconstruction and access control

Without rerunning a model, reconstruct one autonomous, approved, amended, rejected, conflicted, and
guardrail-blocked case.

For every case, verify retained input/content hashes, citations, agent/prompt/workflow/schema/model
versions, deterministic inputs and outputs, policy snapshot and reasons, human decisions, posting
exchange, and final state. Repeat with an auditor who lacks evidence-content permission: permitted
metadata and outcome remain visible, while restricted content is withheld.

## 13. UI and accessibility

Verify the Next.js console with keyboard, screen reader, and supported smaller-screen viewport:

- filter/sort by open state, dual control, conflict, completion, priority, age, deadline, and type;
- preserve selected queue context while opening case detail;
- compare chat and confirmation citations side by side;
- inspect corporate-action source values and agreement states by field;
- distinguish deterministic proposals from agent findings;
- use separate approve, amend, and reject controls with correct validation and status announcements;
- view voluntary-event urgency, audit chronology, and posting/reconciliation state;
- preserve entered data after recoverable server or stale-state errors.

Measure the specification goals: 90% first-attempt task completion, 90% of complete-evidence cases
decided within five minutes, and 95% of supported UI actions returning a result or progress state
within two seconds under the approved workload profile.

## 14. Failure and recovery exercises

Independently fail evidence storage, source connectors, model access, policy lookup, identity,
transactional storage, audit persistence, approval state, posting transport, and acknowledgement.
Each failure must stop autonomous progress, preserve a named retryable/reviewable/reconciliation
state, avoid duplicate action, and produce non-sensitive operational telemetry plus an audit record
when the audit boundary is available.

## 15. Release evaluation

Replay the versioned historical and adversarial sets whenever an agent, prompt, model route,
retrieval rule, schema, policy, deterministic calculation, or posting contract changes. Record:

- component, prompt, schema, policy, rule, dataset, and deployment versions;
- autonomous precision as the primary release gate;
- straight-through rate and false escalation separately;
- idempotency, workflow, approval, dual-control, posting, security, accessibility, and recovery results.

The release is blocked for any unexplained posting, duplicate action, missing audit evidence,
critical unresolved security finding, failed recovery exercise, unreconciled posting behavior, or
precision below the approved threshold. Promotion proceeds only through synthetic validation,
grounded non-production, historical replay, shadow operation, and risk-approved limited autonomy.

Run the complete local quality gate after implementation:

```powershell
Set-Location backend
uv run ruff check src tests
uv run mypy
uv run pytest -q

Set-Location ../frontend
npm ci
npm run typecheck
npm run build
```
