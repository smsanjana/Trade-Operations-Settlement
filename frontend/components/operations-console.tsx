"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  fetchCases,
  fetchCaseSnapshot,
  fetchCaseAuditEvents,
  recordDecision,
  submitDeskInstruction,
  snapshotToOperationsCase,
  ApiError,
} from "../lib/api";
import type {
  CaseSummary,
  CaseReviewSnapshot,
  DecisionAction,
  DecisionPayload,
  OperationsCase,
} from "../lib/types";

type Filter = "open" | "dual" | "conflict" | "completed";
type DetailTab = "evidence" | "proposal" | "corporate_action" | "audit";

const money = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 2 });

function statusLabel(status: OperationsCase["status"]): string {
  const map: Record<string, string> = {
    awaiting_approval: "Approval needed",
    awaiting_second_approval: "Second approval",
    ready_to_post: "Ready to post",
    posted: "Posted",
    rejected: "Rejected",
    blocked: "Blocked",
    review_required: "Review needed",
    dual_control_required: "Second approval",
    reconciliation_required: "Reconciliation needed",
    instructed: "Desk instructed",
  };
  return map[status] ?? status;
}

export function OperationsConsole({
  initialSummaries = [],
  initialError = null,
}: {
  initialSummaries?: CaseSummary[];
  initialError?: string | null;
}) {
  const [cases, setCases] = useState<CaseSummary[]>(initialSummaries);
  const [backendError, setBackendError] = useState<string | null>(initialError);
  const [isRetryingConnection, setIsRetryingConnection] = useState(false);

  const [selectedId, setSelectedId] = useState<string>(initialSummaries[0]?.case_id ?? "");
  const [selectedCase, setSelectedCase] = useState<OperationsCase | null>(null);
  const [rawSnapshot, setRawSnapshot] = useState<CaseReviewSnapshot | null>(null);
  const [currentEtag, setCurrentEtag] = useState<string | null>(null);
  const [isLoadingCase, setIsLoadingCase] = useState(false);
  const [caseError, setCaseError] = useState<string | null>(null);

  const [filter, setFilter] = useState<Filter>("open");
  const [tab, setTab] = useState<DetailTab>("evidence");
  const [decision, setDecision] = useState<DecisionPayload | null>(null);
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState<"success" | "error" | "info">("info");

  const [selectedElection, setSelectedElection] = useState("OPT-1");
  const [isSubmittingElection, setIsSubmittingElection] = useState(false);

  // Live Case Hydration
  async function hydrateCase(caseId: string) {
    if (!caseId) {
      setSelectedCase(null);
      setRawSnapshot(null);
      setCurrentEtag(null);
      return;
    }

    setIsLoadingCase(true);
    setCaseError(null);
    try {
      const { snapshot, etag } = await fetchCaseSnapshot(caseId);
      let auditItems: import("../lib/types").AuditEventItem[] = [];
      try {
        auditItems = await fetchCaseAuditEvents(caseId);
      } catch {
        // Audit events are secondary and non-blocking
      }
      const richCase = snapshotToOperationsCase(snapshot, etag, auditItems);
      setSelectedCase(richCase);
      setRawSnapshot(snapshot);
      setCurrentEtag(etag);

      // Default to corporate action tab if applicable
      if (
        richCase.corporateActionDetails &&
        (richCase.caseType.toLowerCase().includes("dividend") || richCase.caseType.toLowerCase().includes("split"))
      ) {
        setTab("corporate_action");
      }
    } catch (err) {
      setCaseError(
        err instanceof Error ? err.message : `Failed to load snapshot for case '${caseId}'.`
      );
    } finally {
      setIsLoadingCase(false);
    }
  }

  // Load selected case on mount or when selectedId changes, checking query params
  useEffect(() => {
    if (typeof window !== "undefined") {
      const urlCaseId = new URLSearchParams(window.location.search).get("selectedCase");
      if (urlCaseId) {
        setSelectedId(urlCaseId);
        hydrateCase(urlCaseId);
        fetchCases()
          .then((live) => setCases(live))
          .catch(() => {});
        return;
      }
    }
    if (selectedId) {
      hydrateCase(selectedId);
    }
  }, [selectedId]);

  // Retry backend connection
  async function handleRetryBackend() {
    setIsRetryingConnection(true);
    setBackendError(null);
    try {
      const liveSummaries = await fetchCases();
      setCases(liveSummaries);
      if (liveSummaries.length > 0) {
        setSelectedId(liveSummaries[0].case_id);
      }
    } catch (err) {
      setBackendError(
        err instanceof Error
          ? err.message
          : "Backend is unreachable. Please verify that the ASGI server is running on http://localhost:8000."
      );
    } finally {
      setIsRetryingConnection(false);
    }
  }

  const filtered = useMemo(
    () =>
      cases.filter((item) => {
        if (filter === "dual") return item.status === "awaiting_second_approval";
        if (filter === "conflict") return item.case_type.toLowerCase().includes("date") || item.status === "review_required";
        if (filter === "completed") return ["posted", "ready_to_post", "rejected"].includes(item.status);
        return ["awaiting_approval", "awaiting_second_approval", "review_required"].includes(item.status);
      }),
    [cases, filter]
  );

  function openDecision(action: DecisionAction) {
    setMessage("");
    setDecision({ action, note: "" });
  }

  async function submitDecisionHandler(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!decision || !selectedCase) return;

    const needsNote = decision.action === "amend" || decision.action === "reject";
    if (needsNote && !decision.note.trim()) {
      setMessage("A non-empty explanatory decision note is required.");
      setMessageType("error");
      return;
    }
    if (decision.action === "amend" && !decision.amendedAmount) {
      setMessage("Enter the corrected amendment amount before submitting.");
      setMessageType("error");
      return;
    }

    setIsSubmittingDecision(true);
    try {
      const { snapshot, newEtag } = await recordDecision(
        selectedCase.caseId,
        decision,
        currentEtag
      );

      // Refresh case details and summaries
      await hydrateCase(snapshot.case_id);
      setCases((prev) =>
        prev.map((c) =>
          c.case_id === snapshot.case_id
            ? { ...c, status: snapshot.status, case_version: snapshot.case_version }
            : c
        )
      );

      setDecision(null);
      setMessage(
        `Decision '${decision.action}' recorded successfully. ETag updated to ${newEtag ?? 'new version'}.`
      );
      setMessageType("success");
    } catch (error) {
      if (error instanceof ApiError && (error.status === 409 || error.status === 412)) {
        setMessage(
          `Optimistic Concurrency Conflict (HTTP ${error.status}): The case was updated by another process. Refreshed to latest state without overwriting.`
        );
        setMessageType("error");
        await hydrateCase(selectedCase.caseId);
      } else {
        setMessage(
          error instanceof Error ? error.message : "The decision could not be recorded."
        );
        setMessageType("error");
      }
    } finally {
      setIsSubmittingDecision(false);
    }
  }

  async function handleDeskInstruction(event: FormEvent) {
    event.preventDefault();
    if (!selectedCase) return;

    setIsSubmittingElection(true);
    setMessage("");
    try {
      const { snapshot, newEtag } = await submitDeskInstruction(
        selectedCase.caseId,
        selectedElection,
        currentEtag
      );
      await hydrateCase(snapshot.case_id);
      setCases((prev) =>
        prev.map((c) => (c.case_id === snapshot.case_id ? { ...c, status: snapshot.status } : c))
      );
      setMessage(`Voluntary desk election '${selectedElection}' recorded. ETag: ${newEtag}`);
      setMessageType("success");
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Failed to record voluntary desk instruction."
      );
      setMessageType("error");
    } finally {
      setIsSubmittingElection(false);
    }
  }

  // Explicit Backend Unavailable State Screen (Requirement 4 & 12)
  if (backendError && cases.length === 0) {
    return (
      <main className="shell">
        <header className="topbar">
          <div className="brand">
            <span className="brand-mark">T</span>
            <div><b>Trade Operations</b><span>Settlement Console</span></div>
          </div>
          <div className="environment"><span /> Disconnected</div>
        </header>
        <section className="backend-error-screen">
          <h2>Backend Service Unavailable</h2>
          <p>
            The frontend could not connect to the Trade Operations ASGI backend at{" "}
            <code>http://localhost:8000/api/v1</code>.
          </p>
          <p>
            <strong>Error details:</strong> {backendError}
          </p>
          <p>
            Per the safety constitution, mock fixtures are not substituted in place of authoritative
            runtime state. Please start the backend service using:
            <br />
            <code>.\scripts\backend.ps1</code>
          </p>
          <button
            className="btn-retry"
            onClick={handleRetryBackend}
            disabled={isRetryingConnection}
          >
            {isRetryingConnection ? "Connecting..." : "Retry Connection"}
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">T</span>
          <div><b>Trade Operations</b><span>Settlement Console</span></div>
        </div>
        <div className="environment"><span /> Synthetic environment</div>
        <div className="operator">
          <span className="avatar">SS</span>
          <div><b>Settlement supervisor</b><small>Server-authenticated session</small></div>
        </div>
      </header>

      <section className="workspace-heading">
        <div>
          <p className="eyebrow">Exception command centre</p>
          <h1>Settlement review queue</h1>
          <p>Resolve the decision, not the investigation. Every figure remains linked to evidence.</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "16px", flexWrap: "wrap" }}>
          <div className="metric-row">
            <div className="metric">
              <span>Open</span>
              <strong>{cases.filter((x) => x.status.includes("approval")).length}</strong>
            </div>
            <div className="metric warning">
              <span>Conflicts</span>
              <strong>{cases.filter((x) => x.case_type.toLowerCase().includes("date") || x.status === "review_required").length}</strong>
            </div>
            <div className="metric">
              <span>Auto-posted</span>
              <strong>{cases.filter((x) => x.status === "posted").length}</strong>
            </div>
          </div>

          <Link
            href="/cases/create"
            className="btn-create-case"
            style={{
              padding: "10px 18px",
              background: "var(--green)",
              color: "white",
              textDecoration: "none",
              borderRadius: "10px",
              fontWeight: 700,
              fontSize: "13px",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              boxShadow: "0 2px 10px rgba(23, 107, 77, 0.25)",
              border: "1px solid var(--green-dark)",
            }}
          >
            <span>+</span> Create Case
          </Link>
        </div>
      </section>

      <nav className="filterbar" aria-label="Queue filters">
        {(["open", "dual", "conflict", "completed"] as Filter[]).map((item) => (
          <button
            className={filter === item ? "active" : ""}
            key={item}
            onClick={() => setFilter(item)}
          >
            {item === "dual" ? "Dual control" : item[0].toUpperCase() + item.slice(1)}
          </button>
        ))}
      </nav>

      <section className="workspace">
        {/* Left-hand Queue Rail */}
        <aside className="queue" aria-label="Settlement cases">
          <div className="queue-title">
            <b>{filtered.length} cases</b>
            <span>Sorted by control priority</span>
          </div>
          {filtered.map((item) => (
            <button
              key={item.case_id}
              className={`case-row ${selectedId === item.case_id ? "selected" : ""}`}
              onClick={() => {
                setSelectedId(item.case_id);
                setMessage("");
              }}
            >
              <div className="row-top">
                <span className={`priority ${item.priority.toLowerCase()}`}>{item.priority}</span>
                <time>{item.updated_at.slice(0, 10)}</time>
              </div>
              <strong>{item.case_id}</strong>
              <span className="case-type">{item.case_type} · {item.instrument}</span>
              <p>{item.counterparty_or_custodian}</p>
              <div className="row-bottom">
                <b>{item.currency} {money.format(Number(item.exposure_amount))}</b>
                <span>{item.status.replace(/_/g, " ")}</span>
              </div>
            </button>
          ))}
          {!filtered.length && <p className="empty">No cases match this control view.</p>}
        </aside>

        {/* Right-hand Detail Panel */}
        {isLoadingCase ? (
          <div className="loading-indicator">Hydrating case details from backend snapshot...</div>
        ) : caseError ? (
          <div className="backend-error-screen" style={{ margin: "20px" }}>
            <h3>Error Loading Case</h3>
            <p>{caseError}</p>
            <button className="btn-retry" onClick={() => hydrateCase(selectedId)}>Retry</button>
          </div>
        ) : selectedCase ? (
          <article className="detail">
            <div className="detail-head">
              <div>
                <div className="case-kicker">
                  <span className={`status ${selectedCase.status}`}>
                    {statusLabel(selectedCase.status)}
                  </span>
                  <span>{selectedCase.caseId} (v{selectedCase.caseVersion ?? 1})</span>
                </div>
                <h2>{selectedCase.caseType}</h2>
                <p>{selectedCase.summary}</p>
              </div>
              <div className="confidence">
                <span>Evidence confidence</span>
                <strong>
                  {selectedCase.confidence !== undefined
                    ? `${Math.round(selectedCase.confidence * 100)}%`
                    : "N/A"}
                </strong>
                <div>
                  <i
                    style={{
                      width:
                        selectedCase.confidence !== undefined
                          ? `${selectedCase.confidence * 100}%`
                          : "0%",
                    }}
                  />
                </div>
              </div>
            </div>

            <div className="facts">
              <div><span>Counterparty</span><b>{selectedCase.counterparty}</b></div>
              <div><span>Instrument</span><b>{selectedCase.instrument}</b></div>
              <div><span>Exposure</span><b>{selectedCase.currency} {money.format(selectedCase.value)}</b></div>
              <div><span>Value Date</span><b>{selectedCase.settlementDate}</b></div>
            </div>

            {/* Dynamic Policy Strip (Requirement 5 & 13) */}
            <div className="policy-strip">
              <div className="shield">◇</div>
              <div>
                <b>
                  {selectedCase.status === "posted"
                    ? "Within approved autonomy"
                    : selectedCase.status === "awaiting_second_approval"
                    ? "Dual-control threshold reached"
                    : selectedCase.policyReasons.some((r) => r.toLowerCase().includes("conflict"))
                    ? "Evidence conflict detected"
                    : "Policy gate held case for human review"}
                </b>
                <p>
                  {selectedCase.policyReasons.length > 0
                    ? selectedCase.policyReasons.join(" · ")
                    : "Evaluation complete; governance thresholds applied."}
                </p>
              </div>
              <span>{selectedCase.policyVersion ?? "Policy Matrix v1.0"}</span>
            </div>

            {/* Detail Navigation Tabs */}
            <div className="tabs" role="tablist">
              <button
                className={tab === "evidence" ? "active" : ""}
                onClick={() => setTab("evidence")}
              >
                Evidence ({selectedCase.evidence.length})
              </button>
              <button
                className={tab === "proposal" ? "active" : ""}
                onClick={() => setTab("proposal")}
              >
                Proposal
              </button>
              {(selectedCase.corporateActionDetails ||
                selectedCase.caseType.toLowerCase().includes("dividend") ||
                selectedCase.caseType.toLowerCase().includes("split") ||
                selectedCase.caseType.toLowerCase().includes("voluntary")) && (
                <button
                  className={tab === "corporate_action" ? "active" : ""}
                  onClick={() => setTab("corporate_action")}
                >
                  Corporate Action
                </button>
              )}
              <button
                className={tab === "audit" ? "active" : ""}
                onClick={() => setTab("audit")}
              >
                Audit Trail ({selectedCase.audit.length})
              </button>
            </div>

            {/* Tab Panels */}
            <div className="tab-panel">
              {tab === "evidence" && <EvidencePanel selected={selectedCase} />}
              {tab === "proposal" && (
                <ProposalPanel selected={selectedCase} />
              )}
              {tab === "corporate_action" && (
                <CorporateActionPanel
                  selected={selectedCase}
                  selectedElection={selectedElection}
                  setSelectedElection={setSelectedElection}
                  handleDeskInstruction={handleDeskInstruction}
                  isSubmittingElection={isSubmittingElection}
                />
              )}
              {tab === "audit" && <AuditPanel selected={selectedCase} />}
            </div>

            {/* Posting Status Card (Requirement 9) */}
            {selectedCase.postingDetails && (
              <div style={{ margin: "0 28px" }}>
                <PostingStatusCard posting={selectedCase.postingDetails} />
              </div>
            )}

            {/* Status Message Display */}
            {message && (
              <p
                className="message"
                role="status"
                style={{ color: messageType === "error" ? "var(--red)" : "var(--green)" }}
              >
                {message}
              </p>
            )}

            {/* Approval Action Bar */}
            {selectedCase.status.includes("approval") && (
              <div className="actionbar">
                <div>
                  <b>Human decision required</b>
                  <span>
                    {selectedCase.status === "awaiting_second_approval"
                      ? "A distinct second approver releases the governed posting instruction."
                      : "First approval records governed decision and prepares release."}
                  </span>
                </div>
                <button className="reject" onClick={() => openDecision("reject")}>
                  Reject
                </button>
                <button className="amend" onClick={() => openDecision("amend")}>
                  Amend
                </button>
                <button className="approve" onClick={() => openDecision("approve")}>
                  {selectedCase.status === "awaiting_second_approval"
                    ? "Second approve"
                    : "Approve"}
                </button>
              </div>
            )}

            {/* Collapsible Technical Details / Raw JSON (Requirement 11) */}
            <details className="tech-details">
              <summary>Technical Details & Raw Snapshot (ETag: {currentEtag ?? "none"})</summary>
              <pre>
                <code>{JSON.stringify(rawSnapshot, null, 2)}</code>
              </pre>
            </details>
          </article>
        ) : (
          <div className="empty" style={{ margin: "auto" }}>
            Select a settlement case from the queue to inspect citations and record decisions.
          </div>
        )}
      </section>

      {/* Decision Modal with Server-Derived Identity (Requirement 2 & 3) */}
      {decision && selectedCase && (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => setDecision(null)}>
          <form
            className="decision-modal"
            onSubmit={submitDecisionHandler}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="modal-head">
              <div>
                <p className="eyebrow">Governed decision</p>
                <h2>
                  {decision.action[0].toUpperCase() + decision.action.slice(1)} {selectedCase.caseId}
                </h2>
              </div>
              <button type="button" onClick={() => setDecision(null)} aria-label="Close">
                ×
              </button>
            </div>

            {/* Read-Only Server-Derived Identity (Requirement 3) */}
            <div className="read-only-identity">
              <span>Authenticated Approver Identity</span>
              <strong>Settlement Supervisor (Server Security Context)</strong>
            </div>

            {decision.action === "amend" && (
              <label>
                Corrected amount ({selectedCase.currency})
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  autoFocus
                  value={decision.amendedAmount ?? ""}
                  onChange={(event) =>
                    setDecision({ ...decision, amendedAmount: Number(event.target.value) })
                  }
                />
              </label>
            )}

            <label>
              Decision note {decision.action === "approve" && <span>(optional)</span>}
              <textarea
                autoFocus={decision.action !== "amend"}
                value={decision.note}
                onChange={(event) => setDecision({ ...decision, note: event.target.value })}
                placeholder="Record the verified evidence citations and rationale for the audit trail."
              />
            </label>

            {message && messageType === "error" && <p className="form-error">{message}</p>}

            <div className="modal-actions">
              <button type="button" onClick={() => setDecision(null)}>
                Cancel
              </button>
              <button type="submit" className="approve" disabled={isSubmittingDecision}>
                {isSubmittingDecision ? "Recording..." : "Record decision"}
              </button>
            </div>
          </form>
        </div>
      )}
    </main>
  );
}

// Subcomponents

function EvidencePanel({ selected }: { selected: OperationsCase }) {
  if (!selected.evidence.length) {
    return <p className="empty">No citations recorded yet for this case.</p>;
  }
  return (
    <div className="evidence-grid">
      {selected.evidence.map((item) => (
        <section className="evidence-card" key={item.evidenceId}>
          <div>
            <span>{item.kind}</span>
            <b>{item.sourceName}</b>
            <small>{item.locator}</small>
          </div>
          <blockquote>{item.excerpt}</blockquote>
          <footer>
            <span>Source citation</span>
            <code>{item.evidenceId}</code>
          </footer>
        </section>
      ))}
    </div>
  );
}

function ProposalPanel({ selected }: { selected: OperationsCase }) {
  if (!selected.proposedAmount) {
    return (
      <p className="empty">
        No posting proposal survives while evidence is in conflict or unapproved.
      </p>
    );
  }
  return (
    <div className="proposal">
      <div className="proposal-amount">
        <span>Proposed ledger amendment</span>
        <strong>
          {selected.direction} {selected.currency} {money.format(selected.proposedAmount)}
        </strong>
      </div>
      <dl>
        <div><dt>Account</dt><dd>{selected.accountId ?? "N/A"}</dd></div>
        <div><dt>Value date</dt><dd>{selected.settlementDate}</dd></div>
        <div><dt>Reason code</dt><dd>{selected.reasonCode ?? "N/A"}</dd></div>
        <div><dt>Calculation engine</dt><dd>Deterministic arithmetic (zero LLM)</dd></div>
      </dl>
    </div>
  );
}

function CorporateActionPanel({
  selected,
  selectedElection,
  setSelectedElection,
  handleDeskInstruction,
  isSubmittingElection,
}: {
  selected: OperationsCase;
  selectedElection: string;
  setSelectedElection: (val: string) => void;
  handleDeskInstruction: (e: FormEvent) => void;
  isSubmittingElection: boolean;
}) {
  const ca = selected.corporateActionDetails;
  const vol = selected.voluntaryEventDetails;

  return (
    <div className="ca-section">
      {/* Voluntary Event Urgency & Desk Election (Requirement 10) */}
      {vol && (
        <div className="voluntary-box">
          <h4>Voluntary Corporate Action Election</h4>
          <span className="deadline-badge">
            Election Deadline: {new Date(vol.deadline_at).toLocaleDateString()}
          </span>
          <p style={{ margin: "0 0 10px", fontSize: "13px", color: "#61440d" }}>
            Autonomous agents are prohibited from submitting elections. Review impacted accounts and
            record the client instruction below:
          </p>

          <form className="election-form" onSubmit={handleDeskInstruction}>
            <label style={{ fontSize: "12px", fontWeight: "bold" }}>Election:</label>
            <select
              className="election-select"
              value={selectedElection}
              onChange={(e) => setSelectedElection(e.target.value)}
            >
              {vol.options.map((opt) => (
                <option key={opt.option_id} value={opt.option_id}>
                  {opt.description} {opt.is_default ? "(Default)" : ""}
                </option>
              ))}
            </select>
            <button type="submit" className="approve" disabled={isSubmittingElection}>
              {isSubmittingElection ? "Submitting..." : "Record Desk Instruction"}
            </button>
          </form>
        </div>
      )}

      {/* Mandatory Announcement Comparison (Requirement 8) */}
      {ca && ca.announcements.length > 0 && (
        <div>
          <h4 style={{ margin: "0 0 10px" }}>Source Announcement Comparison</h4>
          <div className="ca-table-wrap">
            <table className="ca-table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Event Type</th>
                  <th>Rate / Ratio</th>
                  <th>Record Date</th>
                  <th>Pay Date</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {ca.announcements.map((ann, idx) => (
                  <tr key={idx}>
                    <td><b>{ann.source_name}</b></td>
                    <td>{ann.event_type}</td>
                    <td><code>{ann.rate_or_ratio}</code></td>
                    <td>{ann.record_date}</td>
                    <td>{ann.pay_date}</td>
                    <td>
                      <span
                        className={`badge ${
                          ann.status === "agreed"
                            ? "badge-agreed"
                            : ann.status === "conflicting"
                            ? "badge-conflict"
                            : "badge-pending"
                        }`}
                      >
                        {ann.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tax-Lot Entitlement Breakdown (Requirement 8) */}
      {ca && ca.tax_lots && ca.tax_lots.length > 0 && (
        <div>
          <h4 style={{ margin: "0 0 10px" }}>Position & Tax-Lot Entitlement Breakdown</h4>
          <div className="ca-table-wrap">
            <table className="ca-table">
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Tax Lot</th>
                  <th>Quantity</th>
                  <th>Gross Entitlement</th>
                  <th>Withholding</th>
                  <th>Net Entitlement</th>
                  <th>Cash In Lieu</th>
                </tr>
              </thead>
              <tbody>
                {ca.tax_lots.map((lot, idx) => (
                  <tr key={idx}>
                    <td>{lot.account_id}</td>
                    <td><code>{lot.lot_id}</code></td>
                    <td>{lot.quantity}</td>
                    <td>{lot.gross_entitlement}</td>
                    <td>{lot.withholding_tax ?? "0.00"}</td>
                    <td><b>{lot.net_entitlement}</b></td>
                    <td>{lot.cash_in_lieu ?? "0.00"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p style={{ fontSize: "11px", color: "var(--muted)", marginTop: "8px" }}>
            Rules applied: Fractional shares resolved via{" "}
            <strong>{ca.fractional_treatment ?? "ROUND_HALF_UP"}</strong>. Tax withholding:{" "}
            <strong>{ca.withholding_rate ?? "Standard"}</strong>.
          </p>
        </div>
      )}
    </div>
  );
}

function PostingStatusCard({ posting }: { posting: NonNullable<OperationsCase["postingDetails"]> }) {
  return (
    <div className="posting-card">
      <h4>Governed Posting & Ledger Outcome</h4>
      <dl>
        <div>
          <dt>Instruction ID</dt>
          <dd><code>{posting.instruction_id ?? "N/A"}</code></dd>
        </div>
        <div>
          <dt>External Journal Ref</dt>
          <dd><b>{posting.external_reference ?? "Pending release"}</b></dd>
        </div>
        <div>
          <dt>Posting Status</dt>
          <dd>
            <span
              className={`badge ${
                posting.posting_status === "posted" ? "badge-agreed" : "badge-pending"
              }`}
            >
              {posting.posting_status}
            </span>
          </dd>
        </div>
        <div>
          <dt>Executed At</dt>
          <dd>{posting.executed_at?.slice(0, 19).replace("T", " ") ?? "N/A"}</dd>
        </div>
      </dl>
      {posting.reconciliation_required && (
        <p style={{ margin: "10px 0 0", color: "var(--amber)", fontSize: "12px", fontWeight: "bold" }}>
          Reconciliation Required: Ledger confirmation timed out. Duplicate execution is blocked
          pending manual statement inquiry.
        </p>
      )}
    </div>
  );
}

function AuditPanel({ selected }: { selected: OperationsCase }) {
  if (!selected.audit.length) {
    return <p className="empty">No audit events recorded for this case version.</p>;
  }
  return (
    <ol className="timeline">
      {selected.audit.map((item, index) => (
        <li key={`${item.event}-${index}`}>
          <span />
          <div>
            <b>{item.event}</b>
            <p>{item.actor}</p>
          </div>
          <time>{item.time}</time>
        </li>
      ))}
    </ol>
  );
}
