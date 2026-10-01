# Feature Specification: Trade Operations & Settlement

**Feature Branch**: `001-trade-operations-settlement`

**Created**: 2026-09-22

**Status**: Draft

**Input**: User description: "Create the detailed specification for the Trade Operations &
Settlement application using UseCase.md and the project constitution as primary sources, following
the approved PortAgent architecture."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Resolve Supported Trade Breaks (Priority: P1)

As a settlement analyst, I want supported trade breaks investigated against the booked trade,
standing settlement instructions, trader-broker communications, and confirmations so routine
booking errors are resolved without repeating a manual evidence search.

**Why this priority**: Trade-break resolution is the primary straight-through-processing outcome
and delivers immediate operational value while exercising the system's central evidence and safety
controls.

**Independent Test**: Submit fee, commission, settlement-date, and SSI exceptions with controlled
evidence sets and verify that each case is deduplicated, classified, evidenced, deterministically
calculated where supported, and routed to the correct policy outcome.

**Acceptance Scenarios**:

1. **Given** a fee break with a later chat agreement that matches the confirmation, sufficient
   confidence, and value within the desk limit, **When** PortAgent completes the trade-break
   workflow, **Then** the system creates a cited amendment and the policy gate authorizes the
   eligible autonomous outcome.
2. **Given** an earlier chat term is superseded by an explicit later agreement, **When** the agent
   interprets the conversation, **Then** it identifies the later term and cites the exact message
   establishing the final agreement.
3. **Given** the chat and confirmation disagree, **When** the evidence is reconciled, **Then** the
   case is classified as a counterparty dispute, no autonomous proposal survives, and the case is
   queued with both sources visible.
4. **Given** an exception has an unknown or release-1 unsupported break type, **When** it is
   classified, **Then** it is retained and escalated without a drafted amendment.
5. **Given** the same settlement exception is delivered more than once, **When** it is ingested,
   **Then** all deliveries resolve to one case and cannot create duplicate posting instructions.

---

### User Story 2 - Review and Decide an Escalated Case (Priority: P1)

As an analyst or approver, I want every escalated case to arrive with the trace, policy reasons,
proposed amendment, and cited evidence so I can approve, amend, or reject it without repeating the
investigation.

**Why this priority**: Human review is the mandatory safety path for every case outside approved
autonomy and must be complete before any controlled deployment.

**Independent Test**: Route a case to approval, review all presented evidence and proposal fields,
exercise approve, amend, and reject, and verify decision validation, attribution, state changes,
and audit history.

**Acceptance Scenarios**:

1. **Given** a case requires approval, **When** an authorized user opens it, **Then** the UI shows
   the agent trace, policy reasons, case facts, proposed amendment, and source evidence with precise
   locators.
2. **Given** an approver selects approve, **When** the decision is submitted with an authenticated
   identity, **Then** the approval is recorded against the exact evidence and proposal version the
   approver reviewed.
3. **Given** an approver selects amend, **When** the corrected value and explanatory note are
   supplied, **Then** the corrected proposal and decision record are retained without overwriting
   the original proposal.
4. **Given** an approver selects reject, **When** a note is supplied, **Then** the case is closed
   from posting and the reason is retained for review and evaluation.
5. **Given** a decision form lacks required identity, note, or amended value, **When** submission is
   attempted, **Then** it is refused with a specific correction message and no state change.
6. **Given** another user has decided the case since it was opened, **When** the stale decision is
   submitted, **Then** it is refused and the current case version is displayed.

---

### User Story 3 - Process Mandatory Corporate Actions (Priority: P1)

As a corporate actions analyst, I want announcements reconciled into a field-level golden copy and
entitlements calculated for the record-date population so supported splits and cash dividends can
be processed accurately at account and tax-lot level.

**Why this priority**: Corporate actions affect many accounts simultaneously, making evidence
conflicts and arithmetic correctness high-impact operational risks.

**Independent Test**: Supply multiple controlled announcements plus a record-date position set and
verify extraction, field reconciliation, impacted population, deterministic entitlements, conflict
handling, and policy routing.

**Acceptance Scenarios**:

1. **Given** custodian, standards-based, vendor, and issuer sources agree, **When** a supported
   mandatory event is processed, **Then** the system retains every source, creates a cited golden
   copy, calculates each entitlement deterministically, and evaluates the policy gate.
2. **Given** sources disagree on a material field, **When** reconciliation completes, **Then** the
   field is marked conflicting, all source values remain visible, and the event is escalated without
   resolving the conflict by precedence.
3. **Given** a stock split produces fractional units, **When** entitlements are calculated, **Then**
   the configured fractional and cash-in-lieu rules are applied consistently to each tax lot.
4. **Given** withholding varies by jurisdiction, **When** a cash dividend is calculated, **Then**
   the applicable validated rate and gross-to-net calculation are retained in the audit evidence.
5. **Given** the record-date position snapshot is unavailable or incomplete, **When** population
   resolution is attempted, **Then** processing stops safely and the case is queued for review.

---

### User Story 4 - Track Voluntary Corporate Actions (Priority: P2)

As a corporate actions analyst, I want voluntary events extracted, modelled, and monitored against
their election deadlines so every impacted account reaches the desk in time without the system
making an election.

**Why this priority**: Deadline visibility prevents missed client actions while preserving the
non-negotiable boundary that election judgement remains with the desk.

**Independent Test**: Submit a voluntary event with eligible accounts and a deadline, then verify
option extraction, population visibility, deadline status, and mandatory desk escalation at every
confidence level.

**Acceptance Scenarios**:

1. **Given** a voluntary event, **When** extraction and reconciliation complete, **Then** the system
   records the available options, impacted accounts, evidence, and deadline and routes the case to
   the desk regardless of confidence.
2. **Given** an unresolved account approaches the configured deadline window, **When** the queue is
   viewed, **Then** the case is visibly prioritized and identifies the accounts still requiring an
   instruction.
3. **Given** the desk records or links an election, **When** the case is updated, **Then** the human
   instruction and actor are retained; no agent-generated election is accepted.

---

### User Story 5 - Enforce Bounded Autonomy (Priority: P1)

As a risk owner, I want every autonomous decision made by a deterministic policy gate using the
approved configuration so autonomy can be constrained, explained, and independently reproduced.

**Why this priority**: Bounded autonomy and separation of reasoning from authorization are release
prerequisites, not optional enhancements.

**Independent Test**: Evaluate a matrix of case types, confidence values, amounts, evidence states,
guardrail results, and escalation flags and verify the expected reject, approval, dual-control, or
autonomous outcome and reason codes.

**Acceptance Scenarios**:

1. **Given** untrusted content triggers a guardrail, **When** policy is evaluated, **Then** the case
   is rejected from autonomous processing and no derived proposal survives.
2. **Given** required evidence is missing, confidence is below threshold, sources conflict, or any
   agent escalates, **When** policy is evaluated, **Then** the case enters the approval queue.
3. **Given** an eligible supported case has sufficient evidence and confidence and is within the
   desk limit, **When** policy is evaluated, **Then** it may produce an autonomous posting
   instruction with the policy inputs, version, and reasons retained.
4. **Given** the case value reaches the dual-control threshold, **When** policy is evaluated,
   **Then** two distinct approvals are required before a posting instruction can exist.
5. **Given** policy configuration is missing, invalid, expired, or unavailable, **When** a case
   reaches the gate, **Then** autonomous progress stops and the case remains reviewable.

---

### User Story 6 - Complete Dual Control and Governed Posting (Priority: P1)

As a supervisor, I want high-value cases to require a second distinct approval and all authorized
cases to post through a segregated service so agents cannot directly mutate the ledger.

**Why this priority**: This is the final financial-control boundary between a recommendation and a
ledger-impacting action.

**Independent Test**: Approve a dual-control case with two identities, attempt identity reuse and
decision replay, and exercise posting acknowledgement, rejection, timeout, and duplicate delivery.

**Acceptance Scenarios**:

1. **Given** the first approval exists, **When** the same identity attempts the second approval,
   **Then** the decision is refused and no posting instruction is created.
2. **Given** two distinct authorized approvers approve the same evidence and proposal version,
   **When** the second approval is recorded, **Then** exactly one immutable posting instruction is
   released to the separately privileged posting service.
3. **Given** posting succeeds, **When** an acknowledgement is received, **Then** the case records
   the external reference and completes with its autonomous or human-approved classification.
4. **Given** posting times out with an unknown outcome, **When** reconciliation begins, **Then** the
   system does not blindly retry and exposes the case as awaiting reconciliation.
5. **Given** a posting instruction is replayed, **When** the posting boundary receives it, **Then**
   the original result is returned without a second ledger action.

---

### User Story 7 - Reconstruct Every Decision (Priority: P2)

As an internal auditor or risk reviewer, I want a complete immutable record of evidence, reasoning,
policy, human decisions, calculations, and posting so I can explain the outcome without rerunning a
model.

**Why this priority**: Audit reconstruction is required to defend autonomous and human-approved
financial actions after models, prompts, and source systems change.

**Independent Test**: Select cases representing autonomous posting, approval, amendment,
rejection, conflict, and guardrail blocking and reconstruct each outcome solely from its retained
record.

**Acceptance Scenarios**:

1. **Given** a completed case, **When** an authorized auditor opens its history, **Then** the record
   identifies input and content hashes, source locators, agent and prompt versions, model route,
   policy version and thresholds, deterministic inputs and outputs, decisions, and final outcome.
2. **Given** evidence has changed at its source since processing, **When** the case is reviewed,
   **Then** the retained evidence and hash identify exactly what the workflow used.
3. **Given** an audit user lacks access to sensitive evidence, **When** the case is opened, **Then**
   restricted content is not disclosed while permitted metadata and outcome information remain
   available.

---

### User Story 8 - Validate Changes Before Release (Priority: P2)

As an engineering and risk reviewer, I want relevant historical cases and control scenarios replayed
for every material change so release eligibility is based on measured autonomous-decision quality.

**Why this priority**: Model, prompt, retrieval, policy, and calculation changes can alter outcomes
without changing the user interface and therefore require explicit regression evidence.

**Independent Test**: Propose one change in each controlled category and verify that the correct
versioned evaluation set runs, results are compared with approved gates, and failed gates block the
release.

**Acceptance Scenarios**:

1. **Given** a material controlled component changes, **When** release validation runs, **Then** the
   relevant historical cases, deterministic tests, workflow tests, and security scenarios execute
   with recorded versions and configuration.
2. **Given** autonomous precision is below the risk-approved gate or any unexplained posting,
   duplicate action, missing audit evidence, critical security finding, or failed recovery test is
   present, **When** release eligibility is evaluated, **Then** the release is blocked.

### Edge Cases

- A source document is malformed, encrypted, empty, duplicated, or arrives after a decision.
- A chat thread contains multiple negotiations, cancellations, corrections, or ambiguous references
  to more than one trade.
- Untrusted content contains indirect instructions aimed at the model or attempts to invoke a
  write-capable tool.
- Screening removes or alters a financially meaningful date, identifier, amount, ratio, or currency.
- A required source is unavailable, stale, outside the configured retrieval window, or cannot be
  linked unambiguously to the case.
- Evidence confidence differs by field and the weakest evidence supports a critical decision field.
- A currency, amount, date, account, direction, reason code, ratio, or withholding rate fails
  deterministic validation.
- A corporate action has partial agreement, conflicting dates, multiple currencies, an amended
  announcement, or a cancelled event.
- Holdings change after record date, tax lots are incomplete, or a fractional result reaches a
  rounding boundary.
- The policy configuration changes while a case is open or differs between evaluation and approval.
- An approver loses authorization, attempts self-approval where prohibited, reuses the first dual-
  control identity, or acts on a stale case version.
- A decision or posting instruction is delivered twice, arrives out of order, or receives an
  acknowledgement after a timeout.
- Evidence, audit, identity, policy, connector, model, or posting services become unavailable during
  a workflow.
- A user views the queue on a smaller screen, uses keyboard-only navigation, or relies on assistive
  technology while comparing evidence and completing a decision.

## Requirements *(mandatory)*

### Functional Requirements

#### Scope and Case Intake

- **FR-001**: The system MUST accept settlement fail and match-exception events with a stable source
  identifier, idempotency key, schema version, and event timestamp.
- **FR-002**: The system MUST validate each event envelope before creating or advancing a case.
- **FR-003**: The system MUST resolve repeated deliveries of the same idempotency key to one case
  and one possible posting outcome.
- **FR-004**: The system MUST classify fee, commission, settlement-date, and SSI breaks as supported
  release-1 trade-break types.
- **FR-005**: The system MUST retain and escalate unknown or unsupported break types without
  drafting an amendment.
- **FR-006**: The system MUST support release-1 mandatory stock splits and cash dividends.
- **FR-007**: The system MUST support extraction, entitlement modelling, population visibility,
  and deadline tracking for voluntary events while prohibiting autonomous elections.
- **FR-008**: The system MUST keep price, quantity, FX-rate, nostro, depot, counterparty-interest,
  predictive-fail, and unsupported merger or rights-issue resolution outside release-1 automation.

#### PortAgent Runtime and Agent Responsibilities

- **FR-009**: PortAgent MUST be the agentic runtime and orchestration layer that selects and
  coordinates the approved workflow, agents, prompts, and tools for each case.
- **FR-010**: PortAgent MUST compose the agent roster by case need rather than invoking a fixed
  roster for every case.
- **FR-011**: A workflow step MUST use an agent only when the step requires interpretation of
  evidence that can reasonably support more than one reading.
- **FR-012**: Evidence agents MUST return structured findings with field-level confidence where
  applicable and citations to the retained source locations supporting each conclusion.
- **FR-013**: The trade evidence agent MUST preserve conversation chronology and recognize an
  explicit later agreement as superseding an earlier term.
- **FR-014**: The trade evidence agent MUST flag chat-confirmation disagreement as a conflict and
  MUST NOT select a preferred source.
- **FR-015**: Confirmation extraction MUST retain page-level or equivalent location provenance for
  each economic term used by the workflow.
- **FR-016**: Corporate action extraction MUST identify event type, ex-date, record date, pay date,
  ratio, cash rate, election deadline, currency, and withholding when present, with source and
  confidence per field.
- **FR-017**: Source reconciliation MUST label each golden-copy field as agreed, partial, or
  conflicting and MUST retain every contributing source value.
- **FR-018**: Agents MUST NOT calculate financial values, determine policy outcomes, authorize
  actions, create executable ledger values, or access a ledger write capability.

#### Deterministic Processing

- **FR-019**: The system MUST perform bounded record retrieval, table lookups, schema validation,
  arithmetic, state transitions, idempotency, and policy evaluation deterministically.
- **FR-020**: The system MUST validate standing settlement instructions and relevant static data
  before drafting a trade amendment.
- **FR-021**: The system MUST deterministically distinguish a supported booking difference from a
  source-evidence conflict based on structured findings.
- **FR-022**: A trade amendment MUST contain account, direction, amount, currency, value date, and
  reason code, and every field MUST pass deterministic validation before policy evaluation.
- **FR-023**: The system MUST derive case confidence from the weakest evidence on which the proposed
  action materially depends.
- **FR-024**: The system MUST resolve the corporate-action population by account and tax lot as of
  the record date using an authoritative position snapshot.
- **FR-025**: The system MUST calculate ratios, per-lot entitlements, fractional units, cash in lieu,
  and jurisdictional withholding deterministically using approved rules.
- **FR-026**: The system MUST retain calculation inputs, rules or versions, intermediate values
  needed for explanation, rounding treatment, and final outputs.
- **FR-027**: Any invalid or unavailable deterministic input or rule MUST stop autonomous progress
  and create a reviewable failure reason without a posting proposal being executed.

#### Policy Gate and Autonomy

- **FR-028**: A deterministic policy gate outside all agents MUST decide whether a case is rejected,
  queued for one approval, queued for dual control, or eligible for autonomous posting.
- **FR-029**: The policy gate MUST consume validated structured fields only and MUST NOT consume
  free-form model reasoning as an executable input.
- **FR-030**: Desk and risk owners MUST control confidence thresholds, value limits, dual-control
  thresholds, eligible case types, and deadline windows as versioned configuration.
- **FR-031**: A guardrail trigger MUST reject autonomous processing and invalidate every proposal
  derived from the blocked content.
- **FR-032**: Missing required evidence, unknown type, low confidence, source conflict, agent
  escalation, voluntary event, or unsupported event MUST result in human review.
- **FR-033**: A case reaching the configured dual-control threshold MUST require two distinct
  authorized approvers.
- **FR-034**: Only an eligible supported case with sufficient evidence and confidence, no conflict or
  escalation, and value within the approved desk limit MAY receive an autonomous outcome.
- **FR-035**: Every policy decision MUST record the policy version, thresholds in force, structured
  inputs, outcome, reason codes, and evaluation timestamp.
- **FR-036**: Missing, invalid, expired, or unavailable policy configuration MUST fail closed and
  MUST NOT use an engineering default to authorize autonomy.

#### Human Approval and Posting

- **FR-037**: Every case not authorized for autonomous posting MUST enter a named review state; no
  case may be dropped from the workflow.
- **FR-038**: A reviewer MUST be able to approve, amend, or reject a case through distinct actions.
- **FR-039**: Every decision MUST identify the authenticated actor and the exact case, evidence,
  proposal, and policy versions reviewed.
- **FR-040**: Amend MUST require a corrected value and explanatory note while retaining the original
  proposal and its provenance.
- **FR-041**: Reject MUST require an explanatory note and MUST prevent the rejected proposal from
  reaching posting.
- **FR-042**: Dual control MUST require two distinct authorized identities and MUST display the first
  decision to the second approver.
- **FR-043**: The system MUST reject a repeated decision, stale case update, or attempt by the first
  approver to complete the second approval.
- **FR-044**: Final approval MUST create an immutable posting instruction; it MUST NOT cause an agent
  to write to the ledger.
- **FR-045**: Posting MUST occur through a separately authorized service using the minimum required
  write permission and an instruction-level idempotency key.
- **FR-046**: The system MUST record the posting request, acknowledgement, external reference, and
  autonomous or human-approved classification.
- **FR-047**: A timeout or unknown posting result MUST enter reconciliation without blind retry, and
  a duplicate posting instruction MUST return the original result without another ledger action.

#### Evidence, Audit, and Security

- **FR-048**: The system MUST treat chat, confirmations, contract notes, issuer documents, SWIFT,
  standards-based messages, vendor content, and retrieved context as untrusted.
- **FR-049**: Untrusted content MUST pass platform and application screening before reaching an
  agent.
- **FR-050**: Screening and redaction MUST preserve financially meaningful identifiers, dates,
  amounts, currencies, ratios, and source boundaries; over-redaction MUST be reported and tested as
  a correctness failure.
- **FR-051**: The system MUST retain all evidence used or rejected by a case with source identity,
  precise locator, capture time, content hash, and trust or screening status.
- **FR-052**: Every proposal, escalation, policy outcome, approval, amendment, rejection, posting,
  and reconciliation event MUST append an attributable timestamped audit event.
- **FR-053**: The audit record MUST contain the agent, prompt, workflow, schema, model route, policy,
  deterministic-rule, and evaluation-set versions relevant to the outcome.
- **FR-054**: An authorized reviewer MUST be able to reconstruct why the system acted or declined to
  act without rerunning an agent or model.
- **FR-055**: Audit history and final decisions MUST be immutable; corrections MUST be appended as
  new attributable events.
- **FR-056**: Access to cases, sensitive evidence, decisions, configuration, and audit records MUST
  be restricted by authenticated role and least privilege.
- **FR-057**: Agents and agent-accessible tools MUST be limited to explicitly approved read-only or
  deterministic operations and MUST have no ledger write path.
- **FR-058**: Secrets and unrestricted sensitive evidence MUST NOT appear in prompts, client-visible
  error details, or general operational logs.
- **FR-059**: Evidence and audit retention, encryption, regional handling, and deletion MUST follow
  the approved institutional data policy without weakening decision reconstruction.
- **FR-060**: Failure of evidence, identity, policy, audit persistence, connectors, models, approval
  state, or posting acknowledgement MUST stop autonomous progress and preserve a retryable or
  reviewable state.

#### Analyst and Approver UI

- **FR-061**: The UI MUST provide a queue showing case identifier, type, source, age, priority,
  counterparty or custodian, value, confidence, deadline where applicable, and workflow state.
- **FR-062**: Users MUST be able to filter or sort the queue by open state, dual control, evidence
  conflict, completion state, priority, age, event deadline, and supported case type.
- **FR-063**: Selecting a queue item MUST display the case summary, key facts, evidence confidence,
  policy outcome, and reason codes without losing the user's queue context.
- **FR-064**: The UI MUST show chat and confirmation evidence side by side for trade disputes and
  MUST highlight the cited message or document location.
- **FR-065**: Corporate action views MUST show the golden-copy value, source value, agreement state,
  and provenance for each material field.
- **FR-066**: The proposal view MUST show account, direction, amount, currency, value date, reason
  code, and identify values as deterministic outputs rather than agent findings.
- **FR-067**: Conflict cases MUST visibly present all conflicting values and MUST NOT present an
  autonomous proposal as actionable.
- **FR-068**: Approve, amend, and reject MUST be separate controls with required-input validation and
  clear confirmation of the recorded outcome.
- **FR-069**: A dual-control case MUST identify that a second approval is required, show the first
  approver and decision, and explain identity-reuse refusal.
- **FR-070**: Voluntary-event views MUST show the election deadline, available options, impacted
  accounts, and accounts still awaiting a desk instruction.
- **FR-071**: Users MUST be able to view a chronological audit timeline containing agents,
  deterministic steps, policy outcomes, human actions, and posting state.
- **FR-072**: Posting views MUST distinguish ready-to-post, reconciling, posted, failed, rejected,
  autonomous, and human-approved outcomes and show the external reference when available.
- **FR-073**: The UI MUST provide actionable, non-sensitive error messages and MUST preserve entered
  decision data when a recoverable submission error occurs.
- **FR-074**: Queue, evidence comparison, proposal, audit, and decision interactions MUST remain
  usable with keyboard navigation, assistive technology, and supported smaller-screen layouts.

#### Quality and Release Control

- **FR-075**: Historical resolved cases MUST be replayed after changes to agents, prompts, model
  routing, retrieval, extraction, policy, schemas, or financial calculations.
- **FR-076**: Evaluation datasets, expected outcomes, configuration, and results MUST be versioned
  and linked to the release record.
- **FR-077**: Release validation MUST measure autonomous-decision precision separately from
  straight-through rate and false escalation.
- **FR-078**: Throughput improvements MUST NOT compensate for autonomous precision below the
  risk-approved release gate.
- **FR-079**: Security validation MUST include indirect prompt injection, unauthorized tool use,
  data leakage, malformed content, and over-redaction scenarios.
- **FR-080**: Release validation MUST include policy-boundary, idempotency, replay, workflow-state,
  approval, dual-control, connector-contract, posting-contract, and end-to-end scenarios.
- **FR-081**: The system MUST report autonomous, human-approved, amended, rejected, conflicted,
  guardrail-blocked, reconciliation, and failed outcomes separately.
- **FR-082**: A release MUST be blocked by an unexplained posting, duplicate-action defect, missing
  audit evidence, unresolved critical security finding, failed recovery validation, unreconciled
  posting behavior, or precision below the approved gate.

### Requirement Acceptance Matrix

| Area | Acceptance evidence |
|---|---|
| Intake and scope | Supported and unsupported event fixtures demonstrate validation, classification, deduplication, and safe escalation for FR-001 through FR-008. |
| PortAgent and agents | Workflow traces demonstrate case-specific composition, structured cited findings, chronology, conflicts, and prohibited agent actions for FR-009 through FR-018. |
| Deterministic processing | Golden calculation cases and boundary tests reproduce validated amendments and entitlements for FR-019 through FR-027. |
| Policy gate | A complete decision matrix reproduces reject, approval, dual-control, and autonomous outcomes with versioned reasons for FR-028 through FR-036. |
| Human approval and posting | Role, stale-state, dual-control, replay, acknowledgement, and reconciliation scenarios pass for FR-037 through FR-047. |
| Evidence, audit, and security | An authorized reviewer reconstructs representative outcomes, while injection, over-redaction, least-privilege, and failure tests pass for FR-048 through FR-060. |
| User interface | Task-based usability and accessibility tests cover queue, evidence, proposals, decisions, deadlines, audit, and posting states for FR-061 through FR-074. |
| Release control | Versioned replay reports and security/control suites enforce the release blockers in FR-075 through FR-082. |

### Key Entities *(include if feature involves data)*

- **Case**: The lifecycle record for one trade exception or corporate action, identified by a stable
  case identifier and idempotency key and linked to type, state, priority, value, participants,
  evidence, findings, proposals, decisions, and posting outcome.
- **Evidence Artifact**: A retained chat message, document, structured notice, booked record, SSI
  record, position snapshot, or vendor item with source identity, locator, capture time, content
  hash, screening status, and case relationships.
- **Agent Finding**: A versioned, structured interpretation produced by a named PortAgent-managed
  agent, containing field values, confidence, citations, conflict and escalation indicators.
- **Golden Copy**: The reconciled corporate-action view that preserves each source value and records
  whether each field is agreed, partial, or conflicting.
- **Position and Tax Lot**: The authoritative record-date holdings used to identify affected
  accounts and calculate entitlements.
- **Deterministic Calculation**: A reproducible record of validated inputs, rule versions,
  intermediate values, rounding, and outputs for an amendment or entitlement.
- **Proposed Amendment**: The non-authoritative instruction candidate containing account,
  direction, amount, currency, value date, reason code, citations, and calculation reference.
- **Policy Configuration**: The desk/risk-owned, effective-dated limits and eligibility rules used
  by the policy gate.
- **Policy Decision**: The structured gate input, outcome, reasons, configuration version, and time
  that determine rejection, review, dual control, or autonomous eligibility.
- **Approval Decision**: An immutable approve, amend, or reject action tied to an authenticated
  actor and the exact case, evidence, proposal, and policy versions reviewed.
- **Posting Instruction**: The immutable idempotent instruction released only after policy
  authorization or required approvals and consumed by the separately privileged posting service.
- **Posting Result**: The acknowledgement, external reference, status, timestamps, and reconciliation
  information returned by the book-of-record boundary.
- **Audit Event**: An append-only, attributable, timestamped record of each material workflow,
  agent, deterministic, policy, human, security, and posting event.
- **Evaluation Set and Result**: Versioned historical and adversarial cases, expected outcomes,
  configuration, measured results, and release-gate decision.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of replayed duplicate intake events and posting instructions result in no more
  than one case and one ledger-impacting action.
- **SC-002**: 100% of tested evidence conflicts, unknown break types, voluntary events, missing
  required evidence, agent escalations, and below-threshold cases enter the correct human-review
  path without autonomous posting.
- **SC-003**: 100% of tested financial values reaching a proposal or posting instruction are
  reproducible from retained deterministic inputs and approved rules, with no model-generated
  arithmetic used as an executable value.
- **SC-004**: 100% of guardrail-triggered test cases are blocked before agent interpretation can
  produce an actionable proposal, with zero unauthorized tool or ledger-write actions.
- **SC-005**: Authorized auditors can reconstruct the outcome of 100% of sampled autonomous,
  approved, amended, rejected, conflicted, and blocked cases without rerunning a model.
- **SC-006**: 100% of dual-control tests require two distinct authorized identities, and no case is
  released by identity reuse, stale approval, or decision replay.
- **SC-007**: In usability validation, at least 90% of settlement and corporate-action reviewers
  complete a fully evidenced approve, amend, or reject task correctly on the first attempt.
- **SC-008**: For cases with complete evidence, at least 90% of reviewers reach a decision within
  five minutes without searching outside the case evidence pack.
- **SC-009**: In supported operating conditions, at least 95% of queue, case-detail, and decision
  actions present a result or clear progress state within two seconds of user action.
- **SC-010**: 100% of voluntary events inside the configured deadline window are visibly prioritized
  with all accounts lacking an instruction identified.
- **SC-011**: Every release that changes a controlled component reports autonomous precision,
  straight-through rate, and false escalation on the versioned evaluation set and meets the
  risk-approved precision gate before release.
- **SC-012**: No release proceeds with an unexplained posting, duplicate-action defect, missing
  required audit evidence, unresolved critical security finding, failed recovery validation, or
  unreconciled posting behavior.

## Assumptions

- Release 1 scope and exclusions are those stated in `UseCase.md`; any expansion requires a new or
  amended specification and risk review.
- PortAgent is the approved agentic runtime and orchestration layer. It coordinates agents, prompts,
  tools, and workflows but does not own deterministic authorization or ledger write access.
- Existing enterprise identity and role-management capabilities authenticate analysts, approvers,
  risk users, auditors, and service identities; this feature consumes their asserted identities and
  authorizations.
- Desk and risk owners provide and approve confidence thresholds, auto-post limits, dual-control
  thresholds, eligible event types, and deadline windows before validation or pilot operation.
- The book of record, matching platform, settlement platform, SSI source, holdings source, and tax-
  lot source remain authoritative and expose the records needed for the specified workflows.
- Data retention, encryption, regional controls, legal hold, and deletion periods are supplied by
  the institution's approved data policy and are not independently redefined by this feature.
- Source timestamps, currencies, calendars, and time zones are normalized according to approved
  market and desk conventions while original source representations remain retained.
- The primary operational experience is a responsive web interface for authenticated internal
  users; native mobile applications are outside release 1.
- Local synthetic data or in-memory substitutes may be used for isolated development and testing,
  but they are not authoritative runtime state and do not demonstrate production readiness.
- Production autonomy is enabled only after grounded non-production validation, historical replay,
  shadow operation, risk approval, operational monitoring, rollback readiness, and incident
  procedures are complete.
