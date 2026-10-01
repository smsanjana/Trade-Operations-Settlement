# Trade Operations & Settlement Use Cases

## Purpose and scope

The application resolves supported settlement exceptions from retained evidence, computes
mandatory corporate action entitlements, and prepares controlled human decisions for cases that
cannot be handled autonomously. Release 1 covers fee, commission, settlement-date, and SSI breaks;
mandatory stock splits and cash dividends; voluntary-event extraction and deadline tracking; and
the complete approval record. It does not replace the book of record, make voluntary elections,
settle counterparty disputes, or resolve price, quantity, FX, nostro, depot, or interest-claim
breaks.

## Actors

| Actor | Responsibilities |
|---|---|
| Settlement analyst | Reviews escalated trade breaks, evidence, and proposals |
| Approver or supervisor | Approves, amends, rejects, and completes dual control |
| Corporate actions analyst | Reviews golden copies, conflicts, populations, and deadlines |
| Risk and internal audit | Owns policy limits and verifies reconstructable decisions |
| PortAgent orchestrator | Executes the controlled workflow without ledger write access |
| Evidence agents | Interpret ambiguous source material into cited structured findings |
| Deterministic services | Retrieve records, calculate values, validate, deduplicate, and gate |
| Posting service | Uses a separate identity to submit governed instructions to the ledger |
| External systems | Supply trade, settlement, chat, confirmation, SSI, holdings, and event data |

## Shared preconditions and invariants

- Every input event carries a stable idempotency key.
- All third-party text is untrusted and screened before model access.
- Agent outputs conform to versioned schemas and cite retained evidence.
- Agents never calculate ledger values and never receive write-capable tools.
- The policy gate consumes structured fields only.
- A case that is not auto-posted always lands in a reviewable queue state.
- Approval is attributed; amend and reject include a note; dual control uses distinct identities.
- A final decision is immutable and a posted instruction cannot be replayed.

## UC-01 Ingest and deduplicate an exception

**Primary actor:** External matching or settlement platform

**Trigger:** A settlement fail or matching exception event arrives.

**Main flow:**

1. Validate the envelope and supported schema version.
2. Reserve the idempotency key and create the case record.
3. Link source-system identifiers and record the ingestion audit event.
4. Route the case by known exception type.

**Alternate flows:** A repeated idempotency key returns the existing case without creating a second
posting path. An invalid or unknown type is retained and escalated rather than drafted.

**UI interactions:** The queue shows the new case once, with source, age, priority, type, and current
workflow state.

## UC-02 Resolve a trade break from evidence

**Primary actor:** PortAgent orchestrator

**Trigger:** A known fee, commission, settlement-date, or SSI break is ready for processing.

**Main flow:**

1. Retrieve the booked trade, SSI record, bounded trader-broker thread, and confirmation.
2. Screen untrusted chat and document content.
3. A trade evidence agent identifies the latest agreed terms and cites the message.
4. A confirmation extractor returns economic terms with page-level provenance.
5. Deterministic logic validates SSI and compares agreed terms with the booking.
6. If the evidence agrees, deterministic code creates the amendment fields.
7. The policy gate decides the next state.

**Alternate flows:** Missing evidence, unknown type, low confidence, or agent escalation routes to
approval. A chat-confirm contradiction is marked as a counterparty dispute; the system does not
choose between them and creates no surviving autonomous proposal.

**UI interactions:** The analyst opens the queue item, sees the cited chat and confirm side by side,
opens the proposed amendment, inspects policy reasons, and switches to the audit timeline.

## UC-03 Process a mandatory corporate action

**Primary actor:** Corporate action workflow

**Trigger:** A split or cash-dividend announcement arrives.

**Main flow:**

1. Retain all custodian, ISO 20022, vendor, and issuer sources.
2. Screen each source and extract the event fields with per-field confidence and provenance.
3. Reconcile a golden copy in which every field is agreed, partial, or conflicting.
4. Query the account and tax-lot population as of record date.
5. Calculate entitlements, fractional handling, cash in lieu, and withholding deterministically.
6. Create account-level proposals and evaluate the policy gate.

**Alternate flows:** Any conflicting field, unsupported event, missing position snapshot, or failed
calculation escalates without posting. No source wins by precedence.

**UI interactions:** The corporate actions analyst compares source values, filters impacted
accounts, reviews entitlement calculations, and opens conflict details before deciding.

## UC-04 Track a voluntary corporate action

**Primary actor:** Corporate actions analyst

**Trigger:** A rights issue, optional dividend, tender offer, or other voluntary event arrives.

**Main flow:** Extract and reconcile the event, model eligible accounts and options, record the
deadline, and route the case to the desk regardless of confidence.

**UI interactions:** The queue displays a deadline indicator and accounts requiring instructions.
The analyst may record or link the desk's election, but the agent cannot make the election.

## UC-05 Evaluate bounded autonomy

**Primary actor:** Deterministic policy gate

**Trigger:** A validated finding and deterministic proposal are ready.

**Decision rules:**

| Condition | Outcome |
|---|---|
| Guardrail detects untrusted instruction | Reject; no proposal survives |
| Required evidence missing, evidence conflicts, agent escalates, or confidence is low | Approval required |
| Unknown break type or voluntary/unsupported event | Approval required |
| Value reaches dual-control threshold | Two distinct approvals required |
| Value exceeds desk auto-post limit | Approval required |
| Eligible type, sufficient evidence and confidence, within desk limit | Auto-post instruction |

The audit event includes the policy version, configured thresholds, structured inputs, outcome, and
reason codes so the decision can be re-derived without a model.

## UC-06 Review and decide an escalated case

**Primary actor:** Analyst or approver

**Trigger:** The policy gate places a case in the approval queue.

**Main flow:**

1. Filter or sort the queue by priority, workflow state, conflict, age, and deadline.
2. Open a case and inspect summary, confidence, policy reasons, and case facts.
3. Compare highlighted evidence and its source locator.
4. Inspect the exact account, direction, amount, currency, value date, and reason code.
5. Choose approve, amend, or reject and authenticate the decision identity.
6. For amend, enter the corrected amount and a required note.
7. For reject, enter a required note.
8. Record the immutable decision and display its audit event.

**Alternate flows:** A case already decided cannot be decided again. Missing identity, note, or
amended amount blocks submission. A stale version refreshes the case instead of overwriting a
concurrent decision.

## UC-07 Complete dual control

**Primary actor:** Second approver

**Trigger:** The first approval is recorded for a dual-control case.

**Main flow:** Display the first decision and evidence snapshot, require a different authenticated
identity, record the second decision, and create the governed posting instruction only after the
second approval.

**Alternate flow:** The same identity is rejected. An amendment or rejection closes or reroutes the
case according to approved desk policy and records the rationale.

**UI interactions:** The action bar clearly says "Second approval" and names the first approver;
submission explains why reused identity is invalid.

## UC-08 Post and reconcile an instruction

**Primary actor:** Governed posting service

**Trigger:** The gate authorizes auto-post or the required approvals are complete.

**Main flow:** Consume an immutable posting instruction, submit it under a separate workload
identity, record the external reference and acknowledgement, and mark the case posted.

**Alternate flows:** Timeout or unknown acknowledgement leaves the case in reconciliation, never
blind retry. A duplicate instruction key returns the original result. A ledger rejection routes to
operations with the request and response attached.

**UI interactions:** Users see ready-to-post, reconciliation, posted, or failed status and the
external posting reference. Autonomous and human-approved postings remain separately reportable.

## UC-09 Inspect evidence and audit history

**Primary actor:** Operations, risk, or internal audit

**Trigger:** A user opens case evidence or an audit inquiry.

**Main flow:** Show retained source references and hashes, agent and prompt versions, model route,
schema and policy versions, thresholds, deterministic calculation inputs and outputs, approvals,
posting acknowledgement, and timestamps in chronological order.

**Postcondition:** An authorized reviewer can explain why the system acted or declined to act
without rerunning a model.

## UC-10 Measure quality and release eligibility

**Primary actor:** Engineering and risk

**Trigger:** A model, prompt, retrieval, schema, policy, or calculation change is proposed.

**Main flow:** Replay versioned historical cases, run deterministic and security suites, calculate
auto-post precision and false escalation, compare results with the approved gate, and attach the
evaluation to the release record.

**Postcondition:** The release is blocked on precision failure, unexplained posting, missing audit
evidence, duplicate-action defect, critical security finding, or failed recovery validation.

## UI acceptance baseline

- Queue filters cover open cases, dual control, evidence conflicts, and completed outcomes.
- Selecting a row updates the case facts, policy result, evidence, proposal, and audit views.
- Evidence cards show source type, source name, locator, excerpt, and citation identifier.
- The proposal view distinguishes deterministic outputs from agent findings.
- Approve, amend, and reject are separate actions; required inputs are validated before submission.
- Dual control prevents the first approver from acting as the second approver.
- Conflict cases visibly show both sources and suppress an autonomous proposal.
- Status changes and decisions are announced accessibly and remain visible in the audit timeline.
- Responsive layouts preserve the evidence comparison and decision controls on smaller screens.

