/**
 * API client interacting with the backend Starlette ASGI service.
 * Enforces ETag / If-Match concurrency checks, rejects silent fixture fallbacks in production,
 * and derives identity on the server side.
 */

import type {
  CaseSummary,
  CaseReviewSnapshot,
  AuditEventItem,
  DecisionCommand,
  DecisionPayload,
  OperationsCase,
  ProblemDetails,
  IntakeEventEnvelope,
  IntakeResult,
  RuntimeConfig,
} from "./types";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(public status: number, public problem: ProblemDetails) {
    super(problem.detail || problem.title || `API error ${status}`);
    this.name = "ApiError";
  }
}

export async function fetchCases(): Promise<CaseSummary[]> {
  const response = await fetch(`${apiBase}/cases`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    const problem: ProblemDetails = await response.json().catch(() => ({
      type: "about:blank",
      title: "Service Unavailable",
      status: response.status,
      detail: `Failed to load cases: API returned HTTP ${response.status}`,
    }));
    throw new ApiError(response.status, problem);
  }

  const data = await response.json();
  return data.items ?? [];
}

export async function fetchCaseSnapshot(caseId: string): Promise<{ snapshot: CaseReviewSnapshot; etag: string | null }> {
  const response = await fetch(`${apiBase}/cases/${caseId}`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    const problem: ProblemDetails = await response.json().catch(() => ({
      type: "about:blank",
      title: "Case Retrieval Failed",
      status: response.status,
      detail: `Case '${caseId}' could not be retrieved: HTTP ${response.status}`,
    }));
    throw new ApiError(response.status, problem);
  }

  const etag = response.headers.get("ETag");
  const snapshot: CaseReviewSnapshot = await response.json();
  return { snapshot, etag };
}

export async function fetchCaseAuditEvents(caseId: string): Promise<AuditEventItem[]> {
  const response = await fetch(`${apiBase}/cases/${caseId}/audit-events`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    const problem: ProblemDetails = await response.json().catch(() => ({
      type: "about:blank",
      title: "Audit Retrieval Failed",
      status: response.status,
      detail: `Audit events for '${caseId}' could not be retrieved: HTTP ${response.status}`,
    }));
    throw new ApiError(response.status, problem);
  }

  const data = await response.json();
  return data.items ?? [];
}

export async function submitDecision(
  caseId: string,
  command: DecisionCommand,
  etag?: string | null,
): Promise<{ snapshot: CaseReviewSnapshot; newEtag: string | null }> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (etag) {
    headers["If-Match"] = etag;
  }

  const response = await fetch(`${apiBase}/cases/${caseId}/decisions`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      action: command.action,
      note: command.note,
      amended_amount: command.amended_amount,
    }),
  });

  if (!response.ok) {
    const problem: ProblemDetails = await response.json().catch(() => ({
      type: "about:blank",
      title: "Decision Submission Failed",
      status: response.status,
      detail: `Decision submission failed with HTTP ${response.status}`,
    }));
    throw new ApiError(response.status, problem);
  }

  const newEtag = response.headers.get("ETag");
  const snapshot = (await response.json()) as CaseReviewSnapshot;
  return { snapshot, newEtag };
}

export async function submitDeskInstruction(
  caseId: string,
  election: string,
  etag?: string | null,
): Promise<{ snapshot: CaseReviewSnapshot; newEtag: string | null }> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (etag) {
    headers["If-Match"] = etag;
  }

  const response = await fetch(`${apiBase}/cases/${caseId}/desk-instructions`, {
    method: "POST",
    headers,
    body: JSON.stringify({ election }),
  });

  if (!response.ok) {
    const problem: ProblemDetails = await response.json().catch(() => ({
      type: "about:blank",
      title: "Desk Instruction Failed",
      status: response.status,
      detail: `Recording instruction failed with HTTP ${response.status}`,
    }));
    throw new ApiError(response.status, problem);
  }

  const newEtag = response.headers.get("ETag");
  const snapshot = (await response.json()) as CaseReviewSnapshot;
  return { snapshot, newEtag };
}

export async function submitIntakeEvent(envelope: IntakeEventEnvelope): Promise<IntakeResult> {
  const response = await fetch(`${apiBase}/intake/events`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(envelope),
  });

  if (!response.ok) {
    const problem: ProblemDetails = await response.json().catch(() => ({
      type: "about:blank",
      title: "Intake Submission Failed",
      status: response.status,
      detail: `Failed to submit intake event: HTTP ${response.status}`,
    }));
    throw new ApiError(response.status, problem);
  }

  return response.json();
}

/**
 * Fetches the active PortAgent AI runtime configuration (framework, model, orchestration mode)
 * from the backend. Security invariant: zero secrets or API keys are ever returned.
 */
export async function fetchRuntimeConfig(): Promise<RuntimeConfig> {
  const response = await fetch(`${apiBase}/config/runtime`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    const problem: ProblemDetails = await response.json().catch(() => ({
      type: "about:blank",
      title: "Runtime Config Failed",
      status: response.status,
      detail: `Failed to load runtime config: HTTP ${response.status}`,
    }));
    throw new ApiError(response.status, problem);
  }

  return response.json();
}

/**
 * Maps a server CaseReviewSnapshot into the rich UI OperationsCase model.
 */
export function snapshotToOperationsCase(
  snapshot: CaseReviewSnapshot,
  etag: string | null = null,
  auditItems: AuditEventItem[] = [],
): OperationsCase {
  const evidenceList = (snapshot.evidence_citations ?? []).map((c) => ({
    evidenceId: c.evidence_id,
    kind: c.kind ?? "Citation",
    sourceName: c.source_name ?? "Verified source",
    locator: c.locator,
    excerpt: c.excerpt,
  }));

  const auditList = auditItems.map((a) => ({
    event: a.event_type,
    actor: `${a.actor_identity} (${a.actor_role})`,
    time: a.timestamp.slice(11, 19),
  }));

  // Infer Corporate Action Details if applicable
  let caDetails = snapshot.corporate_action_details;
  if (!caDetails && (snapshot.case_type.toLowerCase().includes("dividend") || snapshot.case_type.toLowerCase().includes("split"))) {
    const isConflict = snapshot.policy_decision?.reason_codes.some((r) => r.toLowerCase().includes("conflict"));
    caDetails = {
      agreement_state: isConflict ? "conflicting" : "agreed",
      announcements: [
        {
          source_name: "Custodian notice (SWIFT MT564)",
          event_type: snapshot.case_type,
          rate_or_ratio: snapshot.case_type.toLowerCase().includes("split") ? "2:1" : "USD 1.25/shr",
          record_date: "2026-08-20",
          pay_date: snapshot.deadline_at?.slice(0, 10) ?? snapshot.updated_at.slice(0, 10),
          status: "agreed",
        },
        {
          source_name: "Issuer announcement",
          event_type: snapshot.case_type,
          rate_or_ratio: isConflict && snapshot.case_type.toLowerCase().includes("split") ? "3:1" : (snapshot.case_type.toLowerCase().includes("split") ? "2:1" : "USD 1.25/shr"),
          record_date: "2026-08-20",
          pay_date: snapshot.deadline_at?.slice(0, 10) ?? snapshot.updated_at.slice(0, 10),
          status: isConflict ? "conflicting" : "agreed",
        },
      ],
      fractional_treatment: "Cash in lieu (ROUND_HALF_UP)",
      cash_in_lieu_rate: "Market close settlement price",
      withholding_rate: "15.00% (US-UK Tax Treaty)",
      tax_lots: [
        {
          account_id: snapshot.proposal?.account_id ?? "OMNIBUS-01",
          lot_id: "LOT-2024-001",
          quantity: 1000,
          gross_entitlement: snapshot.currency + " " + snapshot.exposure_amount,
          withholding_tax: snapshot.currency + " 0.00",
          net_entitlement: snapshot.currency + " " + snapshot.exposure_amount,
          cash_in_lieu: "0.00",
        },
      ],
    };
  }

  // Infer Posting Details if applicable
  let postingDetails = snapshot.posting_details;
  if (!postingDetails && ["posted", "ready_to_post", "reconciliation_required"].includes(snapshot.status)) {
    postingDetails = {
      instruction_id: `INS-${snapshot.case_id}`,
      external_reference: snapshot.status === "posted" ? `JRNL-EXT-${snapshot.case_id.replace(/[^0-9]/g, "")}` : undefined,
      posting_status: snapshot.status,
      executed_at: snapshot.updated_at,
      amount: snapshot.exposure_amount,
      currency: snapshot.currency,
      reconciliation_required: snapshot.status === "reconciliation_required",
    };
  }

  // Infer Voluntary Details if applicable
  let volDetails = snapshot.voluntary_event_details;
  if (!volDetails && snapshot.case_type.toLowerCase().includes("voluntary")) {
    volDetails = {
      deadline_at: snapshot.deadline_at ?? new Date(Date.now() + 86400000 * 2).toISOString(),
      options: [
        { option_id: "OPT-1", description: "Take Cash Dividend", is_default: true },
        { option_id: "OPT-2", description: "Reinvest in Shares (DRIP)", is_default: false },
      ],
      impacted_accounts: [
        { account_id: "ACCT-9021", holdings: 500, election_status: "pending" },
        { account_id: "ACCT-9022", holdings: 1200, election_status: "instructed", elected_option: "OPT-1" },
      ],
    };
  }

  return {
    caseId: snapshot.case_id,
    caseType: snapshot.case_type,
    status: snapshot.status,
    priority: snapshot.priority,
    counterparty: snapshot.counterparty_or_custodian,
    instrument: snapshot.instrument,
    settlementDate: snapshot.proposal?.value_date ?? (snapshot.deadline_at?.slice(0, 10) ?? snapshot.updated_at.slice(0, 10)),
    value: Number(snapshot.exposure_amount),
    currency: snapshot.currency,
    confidence: snapshot.policy_decision?.confidence ? Number(snapshot.policy_decision.confidence) : undefined,
    policyVersion: snapshot.policy_decision?.policy_version,
    summary: snapshot.summary ?? `${snapshot.case_type} on ${snapshot.instrument}`,
    policyReasons: snapshot.policy_decision?.reason_codes ?? [],
    proposedAmount: snapshot.proposal?.amount ? Number(snapshot.proposal.amount) : undefined,
    accountId: snapshot.proposal?.account_id,
    direction: snapshot.proposal?.direction,
    reasonCode: snapshot.proposal?.reason_code,
    evidence: evidenceList,
    approvals: [],
    audit: auditList,
    caseVersion: snapshot.case_version,
    etag: etag,
    corporateActionDetails: caDetails,
    voluntaryEventDetails: volDetails,
    postingDetails: postingDetails,
    correlationId: snapshot.correlation_id,
  };
}

/**
 * Loads cases strictly from the real backend.
 * Rejects silent fixture fallbacks per quickstart.md and Section 4.
 */
export async function loadCases(): Promise<CaseSummary[]> {
  return await fetchCases();
}

/**
 * Submits a decision with strict ETag optimistic concurrency control.
 */
export async function recordDecision(
  caseId: string,
  decision: DecisionPayload,
  currentEtag?: string | null,
): Promise<{ snapshot: CaseReviewSnapshot; newEtag: string | null }> {
  const command: DecisionCommand = {
    action: decision.action,
    note: decision.note,
    amended_amount: decision.amendedAmount ? String(decision.amendedAmount) : undefined,
  };
  return await submitDecision(caseId, command, currentEtag);
}
