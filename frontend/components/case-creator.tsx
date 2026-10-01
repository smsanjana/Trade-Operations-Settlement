"use client";

import { useState, useEffect, useId, FormEvent } from "react";
import Link from "next/link";
import { submitIntakeEvent, fetchRuntimeConfig, ApiError } from "../lib/api";
import type { IntakeEventEnvelope, IntakeResult, ProblemDetails, RuntimeConfig } from "../lib/types";

type FlowType = "settlement" | "corporate_action";
type MandatoryOrVoluntary = "mandatory" | "voluntary";
type OrchestrationMode = "sequential" | "parallel" | "hierarchical";

export function CaseCreator() {
  const [flowType, setFlowType] = useState<FlowType>("settlement");

  // Orchestration & Runtime State
  const [orchestrationMode, setOrchestrationMode] = useState<OrchestrationMode>("sequential");
  const [runtimeConfig, setRuntimeConfig] = useState<RuntimeConfig | null>(null);
  const [isLoadingConfig, setIsLoadingConfig] = useState(true);

  useEffect(() => {
    let isMounted = true;
    fetchRuntimeConfig()
      .then((cfg) => {
        if (isMounted) {
          setRuntimeConfig(cfg);
          if (
            cfg.orchestration_mode === "sequential" ||
            cfg.orchestration_mode === "parallel" ||
            cfg.orchestration_mode === "hierarchical"
          ) {
            setOrchestrationMode(cfg.orchestration_mode);
          }
          setIsLoadingConfig(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setIsLoadingConfig(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Common Intake Metadata
  const [sourceSystem, setSourceSystem] = useState("MUREX");
  const [customSource, setCustomSource] = useState("");
  const [idempotencyKey, setIdempotencyKey] = useState(() => `INTAKE-${Date.now()}`);

  // Settlement Break Fields
  const [breakType, setBreakType] = useState("Fee mismatch");
  const [counterparty, setCounterparty] = useState("Northstar Securities");
  const [instrument, setInstrument] = useState("GB00B03MLX29");
  const [currency, setCurrency] = useState("GBP");
  const [expectedAmount, setExpectedAmount] = useState("12450.00");
  const [bookedAmount, setBookedAmount] = useState("12000.00");
  const [deskId, setDeskId] = useState("EQ_LON");
  const [chatExcerpt, setChatExcerpt] = useState("Agreed final commission is GBP 12,450 for value date 25 Aug.");
  const [confirmExcerpt, setConfirmExcerpt] = useState("Commission GBP 12,450.00; settlement date 25 August 2026.");

  // Corporate Action Fields
  const [caEventType, setCaEventType] = useState("Cash dividend");
  const [classification, setClassification] = useState<MandatoryOrVoluntary>("mandatory");
  const [caCustodian, setCaCustodian] = useState("Global Custody Bank");
  const [caInstrument, setCaInstrument] = useState("US0378331005");
  const [caCurrency, setCaCurrency] = useState("USD");
  const [caAmount, setCaAmount] = useState("184250.00");
  const [caDeadline, setCaDeadline] = useState("2026-10-15T17:00");
  const [caDeskId, setCaDeskId] = useState("CA_DESK");
  const [custodianNotice, setCustodianNotice] = useState("DIVR//USD1.25; PAYD//20260904; EXDATE//20260820");
  const [issuerNotice, setIssuerNotice] = useState("Cash dividend USD 1.25 per share, payable 4 September 2026.");

  // Submission States
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<IntakeResult | null>(null);
  const [submitError, setSubmitError] = useState<ProblemDetails | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Form Field IDs for Accessibility
  const sourceId = useId();
  const idempId = useId();
  const breakTypeId = useId();
  const counterpartyId = useId();
  const instrumentId = useId();
  const currencyId = useId();
  const expAmtId = useId();
  const bkdAmtId = useId();
  const deskIdField = useId();
  const caEventTypeId = useId();
  const caCustodianId = useId();
  const caInstrumentId = useId();
  const caCurrencyId = useId();
  const caAmountId = useId();
  const caDeadlineId = useId();

  // Calculated Exposure for Settlement
  const effectiveSource = sourceSystem === "CUSTOM" ? customSource.trim() : sourceSystem;
  const numExp = parseFloat(expectedAmount) || 0;
  const numBkd = parseFloat(bookedAmount) || 0;
  const calculatedExposure = Math.abs(numExp - numBkd).toFixed(2);

  function generateNewIdempotencyKey() {
    setIdempotencyKey(`INTAKE-${Date.now()}`);
  }

  function validate(): boolean {
    const errors: Record<string, string> = {};

    if (!effectiveSource) {
      errors.sourceSystem = "Source system is required.";
    }
    if (!idempotencyKey.trim()) {
      errors.idempotencyKey = "Idempotency key is required.";
    }

    if (flowType === "settlement") {
      if (!counterparty.trim()) {
        errors.counterparty = "Counterparty name is required.";
      }
      if (!instrument.trim()) {
        errors.instrument = "Instrument identifier is required.";
      }
      if (!expectedAmount || isNaN(Number(expectedAmount))) {
        errors.expectedAmount = "Valid expected amount is required.";
      }
      if (!bookedAmount || isNaN(Number(bookedAmount))) {
        errors.bookedAmount = "Valid booked amount is required.";
      }
    } else {
      if (!caCustodian.trim()) {
        errors.caCustodian = "Custodian or counterparty name is required.";
      }
      if (!caInstrument.trim()) {
        errors.caInstrument = "Instrument identifier is required.";
      }
      if (!caAmount || isNaN(Number(caAmount)) || Number(caAmount) <= 0) {
        errors.caAmount = "Valid positive amount is required.";
      }
      if (classification === "voluntary" && !caDeadline) {
        errors.caDeadline = "Election deadline is strictly required for voluntary corporate actions.";
      }
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    setSubmitError(null);
    setResult(null);

    const eventId = `EVT-SIM-${Date.now()}`;

    let envelope: IntakeEventEnvelope;

    if (flowType === "settlement") {
      const snippets = [];
      if (chatExcerpt.trim()) {
        snippets.push({
          source_name: "Trader-broker thread",
          media_type: "text/plain",
          locator: "Chat transcript",
          excerpt: chatExcerpt.trim(),
        });
      }
      if (confirmExcerpt.trim()) {
        snippets.push({
          source_name: "Broker confirmation",
          media_type: "application/pdf",
          locator: "Page 1 - Economic summary",
          excerpt: confirmExcerpt.trim(),
        });
      }

      envelope = {
        event_id: eventId,
        source_system: effectiveSource,
        idempotency_key: idempotencyKey.trim(),
        event_type: "settlement.exception.received",
        payload: {
          break_type: breakType,
          counterparty: counterparty.trim(),
          instrument: instrument.trim(),
          currency,
          expected_amount: expectedAmount.trim(),
          booked_amount: bookedAmount.trim(),
          desk_id: deskId.trim() || "DEFAULT",
          evidence_snippets: snippets,
          orchestration_mode: orchestrationMode,
        },
      };
    } else {
      const snippets = [];
      if (custodianNotice.trim()) {
        snippets.push({
          source_name: "Custodian notice (SWIFT MT564)",
          media_type: "text/plain",
          locator: "Sequence D - Field 92A",
          excerpt: custodianNotice.trim(),
        });
      }
      if (issuerNotice.trim()) {
        snippets.push({
          source_name: "Issuer official announcement",
          media_type: "text/plain",
          locator: "Official announcement notice",
          excerpt: issuerNotice.trim(),
        });
      }

      envelope = {
        event_id: eventId,
        source_system: effectiveSource,
        idempotency_key: idempotencyKey.trim(),
        event_type: "corporate_action.received",
        payload: {
          event_type: caEventType,
          mandatory_or_voluntary: classification,
          counterparty_or_custodian: caCustodian.trim(),
          instrument_id: caInstrument.trim(),
          currency: caCurrency,
          amount: caAmount.trim(),
          deadline_at: classification === "voluntary" ? new Date(caDeadline).toISOString() : null,
          desk_id: caDeskId.trim() || "CA_DESK",
          evidence_snippets: snippets,
          orchestration_mode: orchestrationMode,
        },
      };
    }

    try {
      const intakeRes = await submitIntakeEvent(envelope);
      setResult(intakeRes);
    } catch (err) {
      if (err instanceof ApiError) {
        setSubmitError(err.problem);
      } else {
        setSubmitError({
          type: "about:blank",
          title: "Connection Failed",
          status: 0,
          detail: err instanceof Error ? err.message : "Failed to connect to the backend intake service.",
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleReset() {
    setResult(null);
    setSubmitError(null);
    setValidationErrors({});
    generateNewIdempotencyKey();
  }

  return (
    <main className="shell">
      {/* Top Bar Matching Console */}
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">T</span>
          <div>
            <b>Trade Operations</b>
            <span>Settlement Console</span>
          </div>
        </div>
        <div className="environment">
          <span /> Synthetic intake environment
        </div>
        <div className="operator">
          <span className="avatar">SS</span>
          <div>
            <b>Settlement supervisor</b>
            <small>Server-authenticated session</small>
          </div>
        </div>
      </header>

      {/* Header and Breadcrumb */}
      <section className="workspace-heading">
        <div>
          <nav className="breadcrumb" aria-label="Breadcrumb" style={{ marginBottom: "10px" }}>
            <Link href="/" className="back-link" style={{ color: "var(--green)", textDecoration: "none", fontWeight: 700, fontSize: "13px" }}>
              ← Review Queue
            </Link>
          </nav>
          <p className="eyebrow">Intake Simulation</p>
          <h1>Create Case</h1>
          <p>Submit a new trade exception or corporate action through the application's event-driven intake boundary.</p>
        </div>
      </section>

      {/* Main Container */}
      <section style={{ margin: "0 4vw 48px", maxWidth: "860px" }}>
        {/* Success Confirmation Card */}
        {result && (
          <div
            className="intake-result-card"
            style={{
              padding: "28px",
              background: result.deduplicated ? "var(--amber-soft)" : "var(--green-soft)",
              border: `1px solid ${result.deduplicated ? "var(--amber)" : "var(--green)"}`,
              borderRadius: "14px",
              marginBottom: "28px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "20px" }}>
              <div>
                <span
                  style={{
                    display: "inline-block",
                    padding: "4px 10px",
                    borderRadius: "999px",
                    background: result.deduplicated ? "var(--amber)" : "var(--green)",
                    color: "white",
                    fontSize: "11px",
                    fontWeight: 800,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    marginBottom: "10px",
                  }}
                >
                  {result.deduplicated ? "Duplicate Ingested (Idempotent)" : "Successfully Ingested"}
                </span>
                <h2 style={{ margin: "0 0 8px", fontSize: "28px" }}>
                  Case ID: <code>{result.case_id}</code>
                </h2>
                <p style={{ margin: "0 0 16px", color: "#2d3d33", lineHeight: 1.5 }}>
                  {result.message}
                </p>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", background: "rgba(255,255,255,0.7)", padding: "14px", borderRadius: "10px" }}>
                  <div>
                    <span style={{ fontSize: "10px", textTransform: "uppercase", color: "var(--muted)", display: "block" }}>Type</span>
                    <b>{result.case_type}</b>
                  </div>
                  <div>
                    <span style={{ fontSize: "10px", textTransform: "uppercase", color: "var(--muted)", display: "block" }}>Initial State</span>
                    <b>{result.state}</b>
                  </div>
                  <div>
                    <span style={{ fontSize: "10px", textTransform: "uppercase", color: "var(--muted)", display: "block" }}>Exposure</span>
                    <b>{result.currency} {result.exposure_amount}</b>
                  </div>
                  <div>
                    <span style={{ fontSize: "10px", textTransform: "uppercase", color: "var(--muted)", display: "block" }}>Orchestration</span>
                    <b style={{ textTransform: "capitalize" }}>{result.orchestration_mode || orchestrationMode}</b>
                  </div>
                </div>
              </div>
            </div>

            <div style={{ marginTop: "24px", display: "flex", gap: "12px", flexWrap: "wrap" }}>
              <Link
                href={`/?selectedCase=${result.case_id}`}
                className="btn-primary"
                style={{
                  padding: "11px 20px",
                  background: "var(--green)",
                  color: "white",
                  textDecoration: "none",
                  borderRadius: "8px",
                  fontWeight: 700,
                  fontSize: "13px",
                  display: "inline-block",
                }}
              >
                Open Case in Review Queue →
              </Link>
              <Link
                href="/"
                style={{
                  padding: "11px 18px",
                  background: "white",
                  border: "1px solid var(--line)",
                  color: "var(--ink)",
                  textDecoration: "none",
                  borderRadius: "8px",
                  fontWeight: 700,
                  fontSize: "13px",
                  display: "inline-block",
                }}
              >
                Back to Review Queue
              </Link>
              <button
                type="button"
                onClick={handleReset}
                style={{
                  padding: "11px 18px",
                  background: "transparent",
                  border: "1px solid var(--muted)",
                  color: "var(--ink)",
                  borderRadius: "8px",
                  fontWeight: 600,
                  fontSize: "13px",
                }}
              >
                + Create Another Case
              </button>
            </div>
          </div>
        )}

        {/* Problem Details Error Alert */}
        {submitError && (
          <div
            className="error-card"
            style={{
              padding: "20px 24px",
              background: "#fae8e8",
              border: "1px solid var(--red)",
              borderRadius: "12px",
              marginBottom: "24px",
            }}
          >
            <h3 style={{ margin: "0 0 6px", color: "var(--red)", fontSize: "16px" }}>
              {submitError.title} (HTTP {submitError.status})
            </h3>
            <p style={{ margin: 0, color: "#542a2a", fontSize: "13px", lineHeight: 1.5 }}>
              {submitError.detail}
            </p>
          </div>
        )}

        {/* Creation Form */}
        <div style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: "16px", padding: "32px", boxShadow: "var(--shadow)" }}>
          <form onSubmit={handleSubmit} noValidate>
            {/* Step 1: Flow Type Selector */}
            <div style={{ marginBottom: "28px" }}>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--muted)", marginBottom: "10px" }}>
                Select Flow Type
              </label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <button
                  type="button"
                  onClick={() => { setFlowType("settlement"); setValidationErrors({}); }}
                  style={{
                    padding: "16px",
                    textAlign: "left",
                    borderRadius: "10px",
                    border: flowType === "settlement" ? "2px solid var(--green)" : "1px solid var(--line)",
                    background: flowType === "settlement" ? "var(--green-soft)" : "#fafbf8",
                    cursor: "pointer",
                  }}
                >
                  <strong style={{ display: "block", fontSize: "15px", color: flowType === "settlement" ? "var(--green)" : "var(--ink)" }}>
                    Settlement Exception Recovery
                  </strong>
                  <span style={{ fontSize: "12px", color: "var(--muted)", display: "block", marginTop: "4px" }}>
                    Fee breaks, settlement-date conflicts, SSI mismatches
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => { setFlowType("corporate_action"); setValidationErrors({}); }}
                  style={{
                    padding: "16px",
                    textAlign: "left",
                    borderRadius: "10px",
                    border: flowType === "corporate_action" ? "2px solid var(--green)" : "1px solid var(--line)",
                    background: flowType === "corporate_action" ? "var(--green-soft)" : "#fafbf8",
                    cursor: "pointer",
                  }}
                >
                  <strong style={{ display: "block", fontSize: "15px", color: flowType === "corporate_action" ? "var(--green)" : "var(--ink)" }}>
                    Corporate Action Processing
                  </strong>
                  <span style={{ fontSize: "12px", color: "var(--muted)", display: "block", marginTop: "4px" }}>
                    Cash dividends, stock splits, voluntary election deadlines
                  </span>
                </button>
              </div>
            </div>

            {/* Step: Orchestration & AI Runtime */}
            <div
              style={{
                padding: "20px",
                background: "#f8faf8",
                border: "1px solid var(--line)",
                borderRadius: "12px",
                marginBottom: "28px",
              }}
            >
              <h3 style={{ margin: "0 0 16px", fontSize: "15px", fontWeight: 700, letterSpacing: "0.02em" }}>
                ORCHESTRATION &amp; AI RUNTIME
              </h3>

              {/* 1. Orchestration Mode */}
              <div style={{ marginBottom: "20px" }}>
                <label
                  style={{
                    display: "block",
                    fontSize: "12px",
                    fontWeight: 700,
                    marginBottom: "8px",
                    color: "var(--ink)",
                  }}
                >
                  Orchestration Mode
                </label>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px" }}>
                  {(["sequential", "parallel", "hierarchical"] as const).map((mode) => {
                    const isSelected = orchestrationMode === mode;
                    const modeLabels = {
                      sequential: "Sequential",
                      parallel: "Parallel",
                      hierarchical: "Hierarchical",
                    };
                    return (
                      <button
                        key={mode}
                        type="button"
                        onClick={() => setOrchestrationMode(mode)}
                        style={{
                          padding: "10px 14px",
                          borderRadius: "8px",
                          border: isSelected ? "2px solid var(--green)" : "1px solid var(--line)",
                          background: isSelected ? "var(--green-soft)" : "white",
                          color: isSelected ? "var(--green)" : "var(--ink)",
                          fontWeight: isSelected ? 700 : 500,
                          fontSize: "13px",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                          textAlign: "center",
                        }}
                      >
                        {modeLabels[mode]}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 2 & 3. Active AI Framework & Active Model (Read-Only / System Configured) */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                <div>
                  <label
                    style={{
                      display: "block",
                      fontSize: "12px",
                      fontWeight: 700,
                      marginBottom: "6px",
                      color: "var(--ink)",
                    }}
                  >
                    Active AI Framework
                  </label>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "10px 12px",
                      borderRadius: "8px",
                      border: "1px solid #d8dfd9",
                      background: "#f0f4f1",
                      fontSize: "13px",
                      fontWeight: 600,
                      color: "var(--ink)",
                    }}
                  >
                    <span>{runtimeConfig?.framework_display || runtimeConfig?.framework || (isLoadingConfig ? "Loading..." : "OpenAI")}</span>
                    <span
                      style={{
                        fontSize: "10px",
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                        padding: "2px 8px",
                        borderRadius: "999px",
                        background: "#e1e9e3",
                        color: "var(--muted)",
                      }}
                    >
                      System configured
                    </span>
                  </div>
                </div>

                <div>
                  <label
                    style={{
                      display: "block",
                      fontSize: "12px",
                      fontWeight: 700,
                      marginBottom: "6px",
                      color: "var(--ink)",
                    }}
                  >
                    Active Model
                  </label>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "10px 12px",
                      borderRadius: "8px",
                      border: "1px solid #d8dfd9",
                      background: "#f0f4f1",
                      fontSize: "13px",
                      fontWeight: 600,
                      color: "var(--ink)",
                    }}
                  >
                    <code>{runtimeConfig?.model || (isLoadingConfig ? "Loading..." : "gpt-4.1")}</code>
                    <span
                      style={{
                        fontSize: "10px",
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                        padding: "2px 8px",
                        borderRadius: "999px",
                        background: "#e1e9e3",
                        color: "var(--muted)",
                      }}
                    >
                      System configured
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Step 2: Ingestion Metadata (Source & Idempotency) */}
            <div style={{ padding: "20px", background: "#f8faf8", border: "1px solid var(--line)", borderRadius: "12px", marginBottom: "28px" }}>
              <h3 style={{ margin: "0 0 16px", fontSize: "15px", fontWeight: 700 }}>
                Intake Metadata
              </h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                <div>
                  <label htmlFor={sourceId} style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>
                    Source System *
                  </label>
                  <select
                    id={sourceId}
                    value={sourceSystem}
                    onChange={(e) => setSourceSystem(e.target.value)}
                    style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #cfd8d1", background: "white", fontSize: "13px" }}
                  >
                    <option value="MUREX">MUREX (Matching Platform)</option>
                    <option value="TRAX">TRAX (Regulatory / Confirmation)</option>
                    <option value="DTCC">DTCC (Clearing House)</option>
                    <option value="SWIFT">SWIFT (Financial Messaging)</option>
                    <option value="EUROCLEAR">EUROCLEAR (Custody / Settlement)</option>
                    <option value="CUSTOM">Custom External Source</option>
                  </select>
                  {sourceSystem === "CUSTOM" && (
                    <input
                      type="text"
                      placeholder="Enter source system identifier"
                      value={customSource}
                      onChange={(e) => setCustomSource(e.target.value)}
                      style={{ marginTop: "8px", width: "100%", padding: "9px 12px", borderRadius: "8px", border: "1px solid #cfd8d1", fontSize: "13px" }}
                    />
                  )}
                  {validationErrors.sourceSystem && (
                    <span className="form-error" style={{ color: "var(--red)", fontSize: "12px", display: "block", marginTop: "4px" }}>
                      {validationErrors.sourceSystem}
                    </span>
                  )}
                </div>

                <div>
                  <label htmlFor={idempId} style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>
                    Idempotency Key *
                  </label>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <input
                      id={idempId}
                      type="text"
                      value={idempotencyKey}
                      onChange={(e) => setIdempotencyKey(e.target.value)}
                      style={{ flex: 1, padding: "10px 12px", borderRadius: "8px", border: "1px solid #cfd8d1", fontSize: "13px" }}
                    />
                    <button
                      type="button"
                      onClick={generateNewIdempotencyKey}
                      title="Generate new unique idempotency key"
                      style={{ padding: "0 12px", background: "white", border: "1px solid var(--line)", borderRadius: "8px", fontSize: "12px", fontWeight: 600 }}
                    >
                      Regenerate
                    </button>
                  </div>
                  {validationErrors.idempotencyKey && (
                    <span className="form-error" style={{ color: "var(--red)", fontSize: "12px", display: "block", marginTop: "4px" }}>
                      {validationErrors.idempotencyKey}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Step 3A: Settlement Exception Fields */}
            {flowType === "settlement" && (
              <div className="flow-panel">
                <h3 style={{ margin: "0 0 16px", fontSize: "16px", fontWeight: 700 }}>
                  Settlement Exception Parameters
                </h3>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "16px" }}>
                  <div>
                    <label htmlFor={breakTypeId} style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>
                      Break Type *
                    </label>
                    <select
                      id={breakTypeId}
                      value={breakType}
                      onChange={(e) => setBreakType(e.target.value)}
                      style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #cfd8d1", background: "white", fontSize: "13px" }}
                    >
                      <option value="Fee mismatch">Fee mismatch</option>
                      <option value="Settlement date conflict">Settlement date conflict</option>
                      <option value="Commission break">Commission break</option>
                      <option value="SSI break">SSI break</option>
                      <option value="Unsupported break">Unsupported break (Escalated to Review)</option>
                    </select>
                  </div>

                  <div>
                    <label htmlFor={counterpartyId} style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>
                      Counterparty *
                    </label>
                    <input
                      id={counterpartyId}
                      type="text"
                      value={counterparty}
                      onChange={(e) => setCounterparty(e.target.value)}
                      style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #cfd8d1", fontSize: "13px" }}
                    />
                    {validationErrors.counterparty && (
                      <span className="form-error" style={{ color: "var(--red)", fontSize: "12px", display: "block", marginTop: "4px" }}>
                        {validationErrors.counterparty}
                      </span>
                    )}
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: "16px", marginBottom: "16px" }}>
                  <div>
                    <label htmlFor={instrumentId} style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>
                      Instrument ID (ISIN / CUSIP) *
                    </label>
                    <input
                      id={instrumentId}
                      type="text"
                      value={instrument}
                      onChange={(e) => setInstrument(e.target.value)}
                      style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #cfd8d1", fontSize: "13px" }}
                    />
                    {validationErrors.instrument && (
                      <span className="form-error" style={{ color: "var(--red)", fontSize: "12px", display: "block", marginTop: "4px" }}>
                        {validationErrors.instrument}
                      </span>
                    )}
                  </div>

                  <div>
                    <label htmlFor={currencyId} style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>
                      Currency *
                    </label>
                    <select
                      id={currencyId}
                      value={currency}
                      onChange={(e) => setCurrency(e.target.value)}
                      style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #cfd8d1", background: "white", fontSize: "13px" }}
                    >
                      <option value="GBP">GBP</option>
                      <option value="USD">USD</option>
                      <option value="EUR">EUR</option>
                      <option value="JPY">JPY</option>
                      <option value="CHF">CHF</option>
                    </select>
                  </div>

                  <div>
                    <label htmlFor={deskIdField} style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>
                      Desk ID
                    </label>
                    <input
                      id={deskIdField}
                      type="text"
                      value={deskId}
                      onChange={(e) => setDeskId(e.target.value)}
                      style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #cfd8d1", fontSize: "13px" }}
                    />
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "16px" }}>
                  <div>
                    <label htmlFor={expAmtId} style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>
                      Expected Amount *
                    </label>
                    <input
                      id={expAmtId}
                      type="text"
                      value={expectedAmount}
                      onChange={(e) => setExpectedAmount(e.target.value)}
                      style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #cfd8d1", fontSize: "13px" }}
                    />
                    {validationErrors.expectedAmount && (
                      <span className="form-error" style={{ color: "var(--red)", fontSize: "12px", display: "block", marginTop: "4px" }}>
                        {validationErrors.expectedAmount}
                      </span>
                    )}
                  </div>

                  <div>
                    <label htmlFor={bkdAmtId} style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>
                      Booked Amount *
                    </label>
                    <input
                      id={bkdAmtId}
                      type="text"
                      value={bookedAmount}
                      onChange={(e) => setBookedAmount(e.target.value)}
                      style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #cfd8d1", fontSize: "13px" }}
                    />
                    {validationErrors.bookedAmount && (
                      <span className="form-error" style={{ color: "var(--red)", fontSize: "12px", display: "block", marginTop: "4px" }}>
                        {validationErrors.bookedAmount}
                      </span>
                    )}
                  </div>
                </div>

                {/* Live Exposure Banner */}
                <div style={{ padding: "12px 16px", background: "#f0f6f2", borderRadius: "8px", border: "1px solid #d4e5d9", display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
                  <span style={{ fontSize: "12px", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 700 }}>
                    Calculated Break Exposure:
                  </span>
                  <strong style={{ fontSize: "18px", color: "var(--green)" }}>
                    {currency} {calculatedExposure}
                  </strong>
                </div>

                {/* Collapsible Evidence Section */}
                <details style={{ background: "#fafbf8", border: "1px solid var(--line)", borderRadius: "10px", padding: "14px 18px", marginBottom: "24px" }}>
                  <summary style={{ cursor: "pointer", fontWeight: 700, fontSize: "13px", color: "var(--ink)" }}>
                    Simulated Evidence Citations (Optional)
                  </summary>
                  <div style={{ marginTop: "14px", display: "grid", gap: "12px" }}>
                    <div>
                      <label style={{ display: "block", fontSize: "11px", fontWeight: 700, color: "var(--muted)", marginBottom: "4px" }}>
                        Trader-Broker Chat Excerpt
                      </label>
                      <textarea
                        rows={2}
                        value={chatExcerpt}
                        onChange={(e) => setChatExcerpt(e.target.value)}
                        style={{ width: "100%", padding: "8px 10px", borderRadius: "6px", border: "1px solid #cfd8d1", fontSize: "12px" }}
                      />
                    </div>
                    <div>
                      <label style={{ display: "block", fontSize: "11px", fontWeight: 700, color: "var(--muted)", marginBottom: "4px" }}>
                        Broker Confirmation Excerpt
                      </label>
                      <textarea
                        rows={2}
                        value={confirmExcerpt}
                        onChange={(e) => setConfirmExcerpt(e.target.value)}
                        style={{ width: "100%", padding: "8px 10px", borderRadius: "6px", border: "1px solid #cfd8d1", fontSize: "12px" }}
                      />
                    </div>
                  </div>
                </details>
              </div>
            )}

            {/* Step 3B: Corporate Action Fields */}
            {flowType === "corporate_action" && (
              <div className="flow-panel">
                <h3 style={{ margin: "0 0 16px", fontSize: "16px", fontWeight: 700 }}>
                  Corporate Action Parameters
                </h3>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "16px" }}>
                  <div>
                    <label htmlFor={caEventTypeId} style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>
                      Event Type *
                    </label>
                    <select
                      id={caEventTypeId}
                      value={caEventType}
                      onChange={(e) => setCaEventType(e.target.value)}
                      style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #cfd8d1", background: "white", fontSize: "13px" }}
                    >
                      <option value="Cash dividend">Cash dividend</option>
                      <option value="Stock split">Stock split</option>
                      <option value="Rights issue">Rights issue</option>
                      <option value="Tender offer">Tender offer</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>
                      Classification *
                    </label>
                    <div style={{ display: "flex", gap: "14px", height: "42px", alignItems: "center" }}>
                      <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", cursor: "pointer" }}>
                        <input
                          type="radio"
                          name="classification"
                          value="mandatory"
                          checked={classification === "mandatory"}
                          onChange={() => setClassification("mandatory")}
                        />
                        Mandatory
                      </label>
                      <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", cursor: "pointer" }}>
                        <input
                          type="radio"
                          name="classification"
                          value="voluntary"
                          checked={classification === "voluntary"}
                          onChange={() => setClassification("voluntary")}
                        />
                        Voluntary (Requires Election)
                      </label>
                    </div>
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "16px" }}>
                  <div>
                    <label htmlFor={caCustodianId} style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>
                      Custodian / Source *
                    </label>
                    <input
                      id={caCustodianId}
                      type="text"
                      value={caCustodian}
                      onChange={(e) => setCaCustodian(e.target.value)}
                      style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #cfd8d1", fontSize: "13px" }}
                    />
                    {validationErrors.caCustodian && (
                      <span className="form-error" style={{ color: "var(--red)", fontSize: "12px", display: "block", marginTop: "4px" }}>
                        {validationErrors.caCustodian}
                      </span>
                    )}
                  </div>

                  <div>
                    <label htmlFor={caInstrumentId} style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>
                      Instrument ID (ISIN) *
                    </label>
                    <input
                      id={caInstrumentId}
                      type="text"
                      value={caInstrument}
                      onChange={(e) => setCaInstrument(e.target.value)}
                      style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #cfd8d1", fontSize: "13px" }}
                    />
                    {validationErrors.caInstrument && (
                      <span className="form-error" style={{ color: "var(--red)", fontSize: "12px", display: "block", marginTop: "4px" }}>
                        {validationErrors.caInstrument}
                      </span>
                    )}
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr 1fr", gap: "16px", marginBottom: "16px" }}>
                  <div>
                    <label htmlFor={caCurrencyId} style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>
                      Currency *
                    </label>
                    <select
                      id={caCurrencyId}
                      value={caCurrency}
                      onChange={(e) => setCaCurrency(e.target.value)}
                      style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #cfd8d1", background: "white", fontSize: "13px" }}
                    >
                      <option value="USD">USD</option>
                      <option value="EUR">EUR</option>
                      <option value="GBP">GBP</option>
                      <option value="JPY">JPY</option>
                    </select>
                  </div>

                  <div>
                    <label htmlFor={caAmountId} style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>
                      Gross Entitlement / Exposure Amount *
                    </label>
                    <input
                      id={caAmountId}
                      type="text"
                      value={caAmount}
                      onChange={(e) => setCaAmount(e.target.value)}
                      style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #cfd8d1", fontSize: "13px" }}
                    />
                    {validationErrors.caAmount && (
                      <span className="form-error" style={{ color: "var(--red)", fontSize: "12px", display: "block", marginTop: "4px" }}>
                        {validationErrors.caAmount}
                      </span>
                    )}
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>
                      Desk ID
                    </label>
                    <input
                      type="text"
                      value={caDeskId}
                      onChange={(e) => setCaDeskId(e.target.value)}
                      style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid #cfd8d1", fontSize: "13px" }}
                    />
                  </div>
                </div>

                {/* Conditional Election Deadline (Only for Voluntary) */}
                {classification === "voluntary" && (
                  <div style={{ marginBottom: "20px", padding: "14px", background: "var(--amber-soft)", border: "1px solid var(--amber)", borderRadius: "10px" }}>
                    <label htmlFor={caDeadlineId} style={{ display: "block", fontSize: "12px", fontWeight: 800, color: "var(--amber)", marginBottom: "6px" }}>
                      Election Deadline (Required for Voluntary Actions) *
                    </label>
                    <input
                      id={caDeadlineId}
                      type="datetime-local"
                      value={caDeadline}
                      onChange={(e) => setCaDeadline(e.target.value)}
                      style={{ width: "100%", padding: "9px 12px", borderRadius: "8px", border: "1px solid #d8b880", fontSize: "13px", background: "white" }}
                    />
                    {validationErrors.caDeadline && (
                      <span className="form-error" style={{ color: "var(--red)", fontSize: "12px", display: "block", marginTop: "4px" }}>
                        {validationErrors.caDeadline}
                      </span>
                    )}
                  </div>
                )}

                {/* Collapsible Evidence Section */}
                <details style={{ background: "#fafbf8", border: "1px solid var(--line)", borderRadius: "10px", padding: "14px 18px", marginBottom: "24px" }}>
                  <summary style={{ cursor: "pointer", fontWeight: 700, fontSize: "13px", color: "var(--ink)" }}>
                    Simulated Announcement Notices (Optional)
                  </summary>
                  <div style={{ marginTop: "14px", display: "grid", gap: "12px" }}>
                    <div>
                      <label style={{ display: "block", fontSize: "11px", fontWeight: 700, color: "var(--muted)", marginBottom: "4px" }}>
                        Custodian Notice (SWIFT MT564)
                      </label>
                      <textarea
                        rows={2}
                        value={custodianNotice}
                        onChange={(e) => setCustodianNotice(e.target.value)}
                        style={{ width: "100%", padding: "8px 10px", borderRadius: "6px", border: "1px solid #cfd8d1", fontSize: "12px" }}
                      />
                    </div>
                    <div>
                      <label style={{ display: "block", fontSize: "11px", fontWeight: 700, color: "var(--muted)", marginBottom: "4px" }}>
                        Issuer Official Notice
                      </label>
                      <textarea
                        rows={2}
                        value={issuerNotice}
                        onChange={(e) => setIssuerNotice(e.target.value)}
                        style={{ width: "100%", padding: "8px 10px", borderRadius: "6px", border: "1px solid #cfd8d1", fontSize: "12px" }}
                      />
                    </div>
                  </div>
                </details>
              </div>
            )}

            {/* Action Bar */}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", paddingTop: "18px", borderTop: "1px solid var(--line)" }}>
              <Link
                href="/"
                style={{
                  padding: "10px 18px",
                  borderRadius: "8px",
                  border: "1px solid var(--line)",
                  background: "white",
                  color: "var(--ink)",
                  textDecoration: "none",
                  fontWeight: 600,
                  fontSize: "13px",
                  display: "inline-block",
                }}
              >
                Cancel
              </Link>
              <button
                type="submit"
                disabled={isSubmitting}
                className="btn-submit"
                style={{
                  padding: "10px 24px",
                  borderRadius: "8px",
                  border: "1px solid var(--green)",
                  background: isSubmitting ? "var(--muted)" : "var(--green)",
                  color: "white",
                  fontWeight: 700,
                  fontSize: "13px",
                  cursor: isSubmitting ? "not-allowed" : "pointer",
                }}
              >
                {isSubmitting ? "Submitting Event..." : "Submit Case Intake"}
              </button>
            </div>
          </form>
        </div>
      </section>
    </main>
  );
}
