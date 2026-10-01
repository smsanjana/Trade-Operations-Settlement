/**
 * Contract-aligned types matching OpenAPI 3.1 specifications.
 * Client-authored approver identities are prohibited; identity is server-derived.
 */

export type CaseStatus =
  | "received"
  | "validated"
  | "evidence_pending"
  | "screened"
  | "interpreted"
  | "deterministic_processing"
  | "policy_evaluated"
  | "review_required"
  | "dual_control_required"
  | "awaiting_second_approval"
  | "ready_to_post"
  | "posting_submitted"
  | "posted"
  | "posting_failed"
  | "reconciliation_required"
  | "rejected"
  | "blocked"
  | "awaiting_approval";

export type Priority = "Critical" | "High" | "Normal";

export interface CaseSummary {
  case_id: string;
  case_type: string;
  status: CaseStatus;
  priority: Priority;
  counterparty_or_custodian: string;
  instrument: string;
  currency: string;
  exposure_amount: string;
  deadline_at: string | null;
  updated_at: string;
}

export interface EvidenceCitation {
  citation_id: string;
  evidence_id: string;
  locator: string;
  excerpt: string;
  source_name?: string;
  kind?: string;
}

export interface PolicyDecisionSnapshot {
  outcome: string;
  reason_codes: string[];
  confidence?: string;
  policy_version?: string;
}

export interface ProposalSnapshot {
  account_id: string;
  direction: string;
  amount: string;
  currency: string;
  value_date: string;
  reason_code: string;
}

export interface CorporateActionNotice {
  source_name: string;
  event_type: string;
  rate_or_ratio: string;
  record_date: string;
  pay_date: string;
  status: "agreed" | "conflicting" | "pending";
}

export interface TaxLotPosition {
  account_id: string;
  lot_id: string;
  quantity: number;
  gross_entitlement: string;
  withholding_tax?: string;
  net_entitlement: string;
  fractional_units?: string;
  cash_in_lieu?: string;
}

export interface CorporateActionDetails {
  announcements: CorporateActionNotice[];
  agreement_state: "agreed" | "conflicting" | "pending";
  fractional_treatment?: string;
  cash_in_lieu_rate?: string;
  withholding_rate?: string;
  tax_lots?: TaxLotPosition[];
}

export interface VoluntaryOption {
  option_id: string;
  description: string;
  is_default: boolean;
}

export interface ImpactedAccount {
  account_id: string;
  holdings: number;
  election_status: "instructed" | "pending";
  elected_option?: string;
}

export interface VoluntaryEventDetails {
  deadline_at: string;
  options: VoluntaryOption[];
  impacted_accounts: ImpactedAccount[];
}

export interface PostingExecutionDetails {
  instruction_id?: string;
  external_reference?: string;
  posting_status: string;
  executed_at?: string;
  amount?: string;
  currency?: string;
  reconciliation_required?: boolean;
  failure_reason?: string;
}

export interface CaseReviewSnapshot extends CaseSummary {
  case_version: number;
  summary?: string;
  policy_decision?: PolicyDecisionSnapshot;
  proposal?: ProposalSnapshot;
  evidence_citations?: EvidenceCitation[];
  corporate_action_details?: CorporateActionDetails;
  voluntary_event_details?: VoluntaryEventDetails;
  posting_details?: PostingExecutionDetails;
  correlation_id?: string;
}

export interface AuditEventItem {
  event_id: string;
  case_id: string;
  sequence_number: number;
  event_type: string;
  actor_identity: string;
  actor_role: string;
  timestamp: string;
  correlation_id?: string;
  payload_hash?: string;
}

export type DecisionAction = "approve" | "amend" | "reject";

export interface DecisionCommand {
  action: DecisionAction;
  note: string;
  amended_amount?: string;
}

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance?: string;
}

// UI Transition & view model types
export interface Evidence {
  evidenceId: string;
  kind: string;
  sourceName: string;
  locator: string;
  excerpt: string;
}

export interface Approval {
  approverId: string;
  action: DecisionAction;
  note: string;
}

export interface OperationsCase {
  caseId: string;
  caseType: string;
  status: CaseStatus;
  priority: Priority;
  counterparty: string;
  instrument: string;
  settlementDate: string;
  value: number;
  currency: string;
  confidence?: number;
  policyVersion?: string;
  summary: string;
  policyReasons: string[];
  proposedAmount?: number;
  accountId?: string;
  direction?: string;
  reasonCode?: string;
  evidence: Evidence[];
  approvals: Approval[];
  audit: { event: string; actor: string; time: string }[];
  caseVersion?: number;
  etag?: string | null;
  corporateActionDetails?: CorporateActionDetails;
  voluntaryEventDetails?: VoluntaryEventDetails;
  postingDetails?: PostingExecutionDetails;
  correlationId?: string;
}

export interface DecisionPayload {
  action: DecisionAction;
  note: string;
  amendedAmount?: number;
}

export interface IntakeEventEnvelope {
  event_id: string;
  source_system: string;
  idempotency_key: string;
  event_type: "settlement.exception.received" | "corporate_action.received";
  payload: Record<string, unknown>;
  received_at?: string;
}

export interface IntakeResult {
  case_id: string;
  case_version: number;
  case_type: string;
  state: CaseStatus;
  priority: Priority;
  exposure_amount: string;
  currency: string;
  source_system: string;
  idempotency_key: string;
  orchestration_mode?: string;
  deduplicated: boolean;
  message: string;
}

export interface RuntimeConfig {
  framework: string;
  framework_display: string;
  provider: string;
  model: string;
  orchestration_mode: string;
  supported_orchestration_modes: string[];
  environment: string;
  mcp_enabled: boolean;
}
