# Phase 0 Research: Trade Operations & Settlement

## Scope and method

This research resolves the technical decisions required by the feature specification, project
constitution, approved PortAgent architecture, `UseCase.md`, and the repository's existing Python
and Next.js boundaries. Prototype tests, frontend fixtures, seed data, and an in-memory adapter are
not treated as implemented production capabilities.

## 1. PortAgent orchestration boundary

**Decision**: PortAgent is the sole agentic runtime and composes a case-specific workflow from the
approved agent, prompt, and tool catalog. It interprets ambiguous evidence but does not make policy
decisions, perform financial arithmetic, mutate authoritative state directly, or reach the ledger
write boundary.

**Rationale**: This preserves the approved architecture and makes probabilistic work observable
without combining interpretation and authorization.

**Alternatives rejected**: A general-purpose agent would weaken least privilege and replay. A fixed
roster adds cost, latency, and failures to cases that do not need every interpreter. Agent-owned
policy or posting violates segregation of duties.

## 2. HTTP, contracts, and validation

**Decision**: Use a non-Pydantic ASGI HTTP boundary and make OpenAPI 3.1 plus JSON Schema 2020-12 the
contract authority. Validate event envelopes, agent outputs, deterministic inputs, policy inputs,
and API payloads at their trust boundaries. Use ordinary typed Python structures internally. The
existing FastAPI/Pydantic dependency is a prototype inconsistency to remove or replace before
implementation, not an approved target dependency.

**Rationale**: JSON Schema is language-neutral, versionable, and usable from Python and TypeScript
without coupling business records to a framework object model.

**Alternatives rejected**: Framework-generated Pydantic schemas violate the stated constraint.
Untyped dictionaries cannot enforce compatibility. Independently hand-maintained frontend types can
drift and therefore cannot be the source of truth.

## 3. Durable state and immutable evidence

**Decision**: Use AlloyDB transactions for cases, versions, idempotency, approvals, policy snapshots,
posting instructions/results, audit indexes, and transactional outbox records. Store retained
evidence and audit payloads by content hash in Cloud Storage under approved retention controls;
publish authorized analytical projections to BigQuery.

**Rationale**: Approval, dual control, and idempotency need relational concurrency guarantees. Large
evidence and audit artifacts suit immutable object storage, while analytics must not be the
transaction authority.

**Alternatives rejected**: Process or agent memory is not durable. Seeded cases are permitted only
as explicit synthetic fixtures. BigQuery is not the approval transaction boundary. Mutable evidence
URLs alone cannot reconstruct what was reviewed.

## 4. Concurrency, idempotency, and posting release

**Decision**: Bind every mutation to the current case version; enforce stable intake and posting
idempotency keys with unique constraints; and create the immutable posting instruction plus outbox
record in the same transaction as the authorizing policy or approval transition. The separately
privileged posting consumer records a correlated result. Timeout or ambiguity moves the case to
`reconciliation_required`; only a status inquiry or matched acknowledgement resolves it.

**Rationale**: Datastore-enforced invariants prevent stale approvals, duplicate decisions, and
double posting even when requests or events are replayed.

**Alternatives rejected**: UI-only duplicate prevention does not handle concurrent clients. Blind
posting retry can duplicate ledger impact. A cross-system distributed transaction is less explicit
and practical than an idempotent boundary plus reconciliation.

## 5. Identity and approvals

**Decision**: Derive users and roles from the authenticated enterprise context; never accept
approver identity as client-authored data. Approval commands identify the reviewed case, evidence
set, proposal, policy decision, approval cycle, and case version. Amend retains the original and
creates a successor proposal. Dual control requires two distinct authorized identities in both the
workflow and datastore constraints.

**Rationale**: Approval is a financial control, so actor identity and the reviewed snapshot must be
server-verifiable and immutable.

**Alternatives rejected**: A request-body `approver_id` is spoofable. Overwriting a proposal or
approval destroys reconstruction. Existing approvals cannot survive a material amendment because
they would authorize different executable values.

## 6. Evidence screening and citations

**Decision**: Retain the original artifact, calculate its content hash, classify trust, and run
platform plus application screening before any model access. Screening identifies redactions and
material-field preservation. Agents receive bounded evidence and return per-field citations,
confidence, conflicts, and escalation flags bound to the current evidence-set version.

**Rationale**: External financial content can carry indirect instructions; retained evidence and
precise locators are necessary for security and audit reconstruction.

**Alternatives rejected**: Post-model screening crosses the trust boundary too late. Whole-document
citations are insufficient where precise locators exist. Silent source precedence is prohibited;
material disagreement remains visible and escalates.

## 7. Deterministic calculations and policy

**Decision**: Implement calculations as pure, versioned operations over validated decimal, date,
currency, account, position, and rule inputs. Retain inputs, intermediate values, rounding, rule
versions, and outputs. Derive confidence from the weakest materially supporting evidence. The gate
consumes a fixed structured snapshot and returns `rejected`, `approval_required`,
`dual_control_required`, or `autonomous_authorized` with reason codes.

**Rationale**: Financial values and autonomy decisions must be reproduced without a model and fail
closed when data or configuration is unavailable.

**Alternatives rejected**: Model arithmetic and floating-point money are unsuitable for executable
values. Prompt-embedded thresholds and engineering default policies cannot grant authority.

## 8. API and UI interaction model

**Decision**: Provide cursor-paginated queue queries and a detailed case review snapshot containing
evidence, findings, reconciliation, proposal, policy, approvals, audit, and posting state. Decision
commands use `If-Match` plus immutable snapshot references and return the updated snapshot or a
precise stale-state conflict. Long-running work is event-driven and exposed through durable status.
The UI preserves queue context and form input across recoverable errors.

**Rationale**: Reviewers need one complete evidence pack and explicit concurrency behavior. A case
snapshot binds the decision to exactly what was reviewed.

**Alternatives rejected**: Offset pagination is unstable in a changing queue. Client-authored
identity and optimistic approval completion bypass server controls. Silent fixture fallback can show
false operational state and is allowed only behind an explicit local-demo mode.

## 9. Testing and evaluation

**Decision**: Follow red-green-refactor with deterministic unit/property tests, schema and contract
tests, datastore concurrency tests, workflow state-machine tests, connector/posting integration,
security/adversarial tests, accessibility tests, operator end-to-end journeys, and historical replay.
Model-dependent evaluation uses frozen versioned datasets and records prompt, model route, schema,
policy, and expected outcomes.

**Rationale**: Each control needs targeted evidence; a single end-to-end suite cannot isolate
arithmetic, contract, security, or model-quality regressions.

**Alternatives rejected**: Live-model tests are not deterministic enough for the default suite.
Straight-through rate cannot compensate for low autonomous precision. Manual approval testing alone
cannot prove concurrency, replay, or duplicate-posting controls.

## 10. Deployment, scale, and recovery

**Decision**: Deploy stateless API/workflow workers to Cloud Run and keep authoritative state in
durable services. Establish a desk/risk-approved workload profile before pilot and validate the
two-second UI target, queue age, event lag, and reconciliation age against it. Promote from
synthetic to grounded non-production, historical replay, shadow, then limited autonomy. Disable
autonomy first during rollback while preserving review and reconciliation access.

**Rationale**: Approved sources contain no credible production volume number, so inventing one
would create false assurance. Horizontal scaling plus measured pre-pilot gates resolves the design.

**Alternatives rejected**: Hard-coded volume assumptions lack approval. Direct production autonomy
after functional testing omits model and operational risk evidence. Destructive rollback of audit or
decision data is prohibited; corrections append events and schemas use compatible migration phases.

## Resolved unknowns

No unresolved clarification markers remain. Institution-specific policy values, retention periods,
regional controls, exact model routes, and workload numbers are fail-closed configuration and
approval inputs; engineering must not invent them.
