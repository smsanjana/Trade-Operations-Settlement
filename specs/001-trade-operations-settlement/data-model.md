# Data Model: Trade Operations & Settlement

## Modeling rules

- `Case` is the transactional aggregate root, but evidence, policy configuration, decisions,
  posting records, and audit history are immutable/versioned records.
- Current-state queue and reporting views are rebuildable projections, not workflow authority.
- Monetary amounts, rates, ratios, and confidence values use canonical decimal strings at external
  boundaries and fixed-precision decimal arithmetic internally; binary floating point is prohibited.
- All records carry stable identifiers, schema version, creation timestamp, and applicable source,
  workflow, policy, or component version references.
- Late evidence and corrections create successor versions. They never rewrite what a prior policy
  gate or approver reviewed.
- Institution-defined retention, classification, residency, and legal-hold policy values remain
  external configuration; missing policy fails closed.

## Entity catalog

### Case

The stable lifecycle record for one trade exception or corporate-action process.

Key fields:

- `case_id`, `schema_version`, `case_version`
- `source_system`, `source_event_id`, `intake_idempotency_key`, `correlation_id`
- `workflow_type`, `case_type`, `desk_id`, `priority`, `state`
- `counterparty_or_custodian`, `instrument_id`, `currency`, `exposure_amount`
- `deadline_at`, `received_at`, `updated_at`
- `current_evidence_set_id`, `current_proposal_id`, `current_policy_decision_id`
- `failure_class`, `failure_reason_codes`

Invariants:

- `(source_system, intake_idempotency_key)` is unique.
- Every state-changing command compares the supplied version with `case_version`.
- Unsupported types remain as reviewable cases and cannot hold an executable proposal.
- A case cannot enter a posting state without a valid posting instruction.

### TradeExceptionDetails

Key fields: `case_id`, `booked_trade_reference`, `break_type`, affected economic fields,
`ssi_reference`, `counterparty_dispute`, and source references.

Invariant: only fee, commission, settlement-date, and SSI types are release-1 automation candidates.

### CorporateActionDetails

Key fields: `case_id`, `event_reference`, `event_type`, `mandatory_or_voluntary`, instrument,
ex-date, record date, pay date, currency, deadline, and `current_golden_copy_id`.

Invariants:

- Mandatory stock splits and cash dividends are the only release-1 entitlement automation types.
- Voluntary events always require a human desk instruction and never receive an agent-generated
  election.

### EvidenceArtifact

An immutable capture of chat, confirmation, contract note, structured notice, issuer/vendor
document, SSI, booked trade, position snapshot, tax-lot data, or other retrieved context.

Key fields: `evidence_id`, source identity/type, original source timestamp, capture timestamp,
content hash, media/schema type, storage reference, trust classification, data classification,
retention class, region, legal-hold status, and artifact version.

Invariants:

- The retained bytes or authoritative structured snapshot match the content hash.
- Storage references are role-scoped and are not embedded in general logs or events.
- A hash does not replace the evidence needed for reconstruction.

### EvidenceCaseLink and EvidenceSet

`EvidenceCaseLink` connects a case and artifact with purpose, precise locator, used/rejected status,
screening result, screening/redaction version, duplicate/late indicator, and material-field checks.
`EvidenceSet` freezes the ordered evidence-link identifiers and hashes used by one interpretation,
calculation, policy, or approval cycle.

Invariants:

- Agent access is allowed only when every relevant link is screened and not blocked.
- A prompt-injection trigger marks the link blocked and invalidates dependent findings/proposals.
- Over-redaction of a financially material field is a correctness failure.

### WorkflowRun, AgentRun, AgentFinding, and Citation

`WorkflowRun` records the PortAgent workflow name/version, state, correlation identifiers, and
resumption checkpoint. `AgentRun` records agent, prompt, output-schema, model-route, tool-catalog,
and evidence-set versions plus timing/status. `AgentFinding` is an immutable structured output with
field values, confidence, conflict, and escalation flags. `Citation` links a finding field to an
evidence artifact and exact page, message, field path, or equivalent locator.

Invariants:

- Findings must validate against the declared schema before deterministic use.
- Every materially used finding field has at least one valid citation.
- Agent findings never contain executable arithmetic, policy authorization, or ledger commands.

### GoldenCopy, GoldenCopyField, and GoldenCopySourceValue

The versioned corporate-action reconciliation record. Each `GoldenCopyField` records field name,
normalized value only where non-conflicting, and `agreed`, `partial`, or `conflicting` status. Each
contributing `GoldenCopySourceValue` preserves original and normalized value, confidence,
normalization metadata, and citation.

Invariant: a material conflicting field has no silently preferred executable value and blocks
autonomous progression.

### PositionSnapshot and TaxLot

The authoritative record-date population used for entitlement calculations. The snapshot contains
source version/hash, as-of timestamp, completeness status, accounts, and tax-lot references. A tax
lot contains the account, lot identity, settled position, and only the jurisdictional/acquisition
attributes required by approved rules.

Invariant: an unavailable or incomplete authoritative snapshot stops calculation and routes the
case to review.

### DeterministicCalculation

An immutable reproduction record for trade differences, entitlement population, ratios, per-lot
values, fractional handling, cash in lieu, withholding, rounding, confidence aggregation, or
payload construction.

Key fields: `calculation_id`, type/version, input schema/version, canonical inputs, rule-table
versions, intermediate steps, rounding mode/scale, outputs, validation results, reproducibility hash,
and timestamp.

Invariant: every financial value in a proposal is traceable to a successful calculation record.

### Proposal

An immutable non-authoritative instruction candidate.

Key fields: `proposal_id`, `proposal_version`, predecessor proposal, evidence set, calculation,
account, direction, amount, currency, value date, reason code, citations, validity state, and
invalidation reasons.

Invariants:

- All executable fields pass deterministic validation.
- Amend creates a successor proposal and retains the original.
- A proposal derived from blocked content or stale evidence cannot be restored to valid status.

### PolicyConfiguration and PolicyDecision

`PolicyConfiguration` is an immutable, approved, effective-dated scope containing eligible types,
confidence/value/dual-control thresholds, evidence requirements, deadline windows, expiry,
owner approvals, and version. `PolicyDecision` retains the complete structured input snapshot,
configuration version, result, reason codes, and evaluation timestamp.

Allowed results: `rejected`, `approval_required`, `dual_control_required`, and
`autonomous_authorized`.

Invariants:

- Active configurations for the same policy scope cannot overlap.
- Missing, invalid, expired, or unavailable configuration cannot authorize autonomy.
- Free-form reasoning is not an input to the gate.
- Guardrail block, conflict, unknown/unsupported type, missing evidence, low confidence, voluntary
  event, or agent escalation cannot produce autonomous authorization.

### ApprovalCycle and ApprovalDecision

`ApprovalCycle` pins an exact case version, evidence set, proposal, policy decision, required count,
and state. `ApprovalDecision` is an immutable approve/amend/reject action containing authenticated
actor, authorization context, slot number, note, amendment reference, and timestamp.

Invariants:

- Identity is derived from the authenticated context, not a client-supplied field.
- Amend and reject require a note; amend requires valid corrected structured values.
- A material amendment creates a successor proposal, reruns policy, and starts a fresh cycle.
- Dual-control slots require different authorized actors.
- Stale, repeated, or already-decided commands change no state.

### ElectionRecord

An immutable human-originated voluntary-election instruction or a link to an authoritative external
instruction. It records actor, authorization context, option, affected accounts, source reference,
and time.

Invariant: agent and service identities cannot create an election record.

### PostingInstruction and PostingResult

`PostingInstruction` is the immutable payload released after autonomous authorization or satisfied
approval, containing exact proposal/version, authorization basis, instruction idempotency key,
payload hash, and autonomous/human-approved classification. `PostingResult` is an append-only
acknowledgement, rejection, timeout, reconciliation, or external-reference record.

Invariants:

- There is one instruction per authorization fingerprint and one ledger-impacting result per
  posting idempotency key.
- Instruction creation, authorizing transition, audit event, and outbox record are transactional.
- Unknown outcomes enter reconciliation and never cause a blind replacement instruction.

### AuditEvent

An append-only, attributable, timestamped event covering intake, evidence, screening, workflow,
agent, deterministic, policy, human, security, posting, and reconciliation activity.

Key fields: `audit_event_id`, `case_id`, case sequence, event type, actor/service identity,
correlation/causation identifiers, component/version references, payload reference/hash,
`previous_hash`, `event_hash`, and timestamp.

Invariants:

- `(case_id, sequence_number)` is unique and ordered.
- Material state advancement commits with its required audit event.
- Corrections append events; audit history and final decisions are never updated in place.

### EvaluationSet, EvaluationRun, and ReleaseDecision

Versioned historical/adversarial cases, expected results, component/configuration versions, actual
results, autonomous precision, straight-through rate, false escalation, control/security failures,
and release eligibility with blocker reasons.

Invariant: a controlled-component change cannot be released without a linked eligible evaluation
run and all mandatory control suites.

## Relationships

```text
Case 1--* EvidenceCaseLink *--1 EvidenceArtifact
Case 1--* EvidenceSet 1--* EvidenceCaseLink
Case 1--* WorkflowRun 1--* AgentRun 1--* AgentFinding 1--* Citation
CorporateActionDetails 1--* GoldenCopy 1--* GoldenCopyField 1--* GoldenCopySourceValue
CorporateActionDetails 1--* PositionSnapshot 1--* TaxLot
Case 1--* DeterministicCalculation 1--* Proposal
Proposal *--1 EvidenceSet
Case 1--* PolicyDecision *--1 PolicyConfiguration
PolicyDecision *--1 Proposal
Case 1--* ApprovalCycle 1--* ApprovalDecision
ApprovalCycle *--1 Proposal
Case 1--* PostingInstruction 1--* PostingResult
Case 1--* AuditEvent
EvaluationSet 1--* EvaluationRun 1--1 ReleaseDecision
```

## Case state machine

```text
received
  -> validated
  -> evidence_pending
  -> screened
  -> interpreted
  -> deterministic_processing
  -> policy_evaluated
       -> review_required
       -> dual_control_required
       -> ready_to_post
       -> blocked

review_required
  -> ready_to_post | rejected | reevaluation_required

dual_control_required
  -> awaiting_second_approval
  -> ready_to_post | rejected | reevaluation_required

ready_to_post
  -> posting_submitted
  -> posted | posting_failed | reconciliation_required

reconciliation_required
  -> posted | posting_failed
```

Evidence, identity, model, connector, rule, policy, approval-state, or audit failure must enter a
named retryable, reviewable, blocked, or reconciliation state. A case cannot silently disappear.
Posted is terminal for the original instruction; later evidence creates an appended follow-up flow.

## Approval state machine

```text
pending
  -> satisfied                 # single-control approval
  -> first_approved
       -> satisfied            # distinct second approval
  -> rejected
  -> superseded                # evidence/proposal/policy changed
```

Reject prevents the cycle's proposal from posting. Amend produces a successor proposal and policy
decision; any prior approvals become superseded so all required approvers review identical values.

## Posting state machine

```text
created -> dispatched
             -> acknowledged
             -> rejected
             -> outcome_unknown -> reconciling
                                      -> reconciled_posted
                                      -> reconciled_rejected
```

`outcome_unknown` has no automatic retry transition.

## Concurrency and idempotency constraints

- Unique intake: `(source_system, intake_idempotency_key)`.
- Compare-and-swap on `Case.case_version` for every transition.
- Unique audit order: `(case_id, sequence_number)`.
- Unique approval slot: `(approval_cycle_id, slot_number)`.
- Two dual-control slots cannot contain the same actor identity.
- One active cycle per case/evidence/proposal/policy version tuple.
- One posting instruction per authorization fingerprint.
- Globally unique posting idempotency key; replay returns the recorded result.
- Policy configuration effective intervals for the same scope cannot overlap.
- Final decision, instruction, audit, and outbox creation share one transaction.

## Security classification baseline

| Data | Baseline handling |
|---|---|
| Public issuer source | Public at source, but its retained workflow copy inherits case access controls. |
| Case metadata and non-sensitive metrics | Internal or Confidential according to desk scope. |
| Trade economics, chat, confirms, SSI, accounts, holdings, and tax lots | Restricted financial/client data. |
| Findings, citations, excerpts, golden copies, and calculations | Inherit the highest source classification. |
| Approval identity, policy decisions, posting records, and audit | Restricted regulated-control data. |
| Policy thresholds and eligibility | Confidential and limited to approved desk/risk administrators. |
| Credentials and secrets | Secret-store only; never stored in case, evidence, prompt, or audit payloads. |

Authorization combines role, desk/business scope, region, classification, and purpose. Search
indexes, caches, UI excerpts, and exports inherit their source classification and retention rules.
An auditor without content permission receives permitted metadata and outcome information, not the
restricted evidence body.

## Retention and deletion

- Store policy-supplied retention class, region, retention start, destruction-eligibility time, and
  legal-hold state; do not invent durations.
- Legal hold overrides normal destruction.
- Coordinate evidence and dependent decision retention so surviving records do not falsely claim
  reconstructability.
- Policy-authorized deletion may leave only the required tombstone and audit proof; it must not
  retain content that policy requires destroyed.
