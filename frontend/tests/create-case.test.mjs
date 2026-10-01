import test from "node:test";
import assert from "node:assert/strict";

const apiBase = "http://127.0.0.1:8000/api/v1";

test("Intake: POST /intake/events creates a settlement exception case", async () => {
  const idempotencyKey = `FRONTEND-SETTL-${Date.now()}`;
  const payload = {
    event_id: `EVT-FE-${Date.now()}`,
    source_system: "MUREX",
    idempotency_key: idempotencyKey,
    event_type: "settlement.exception.received",
    payload: {
      break_type: "Fee mismatch",
      counterparty: "Citigroup Global",
      instrument: "GB0002634946",
      currency: "GBP",
      expected_amount: "18500.00",
      booked_amount: "18000.00",
      desk_id: "EQ_LON",
      evidence_snippets: [
        {
          source_name: "Trader chat",
          media_type: "text/plain",
          excerpt: "Confirmed final fee is 18500.",
        },
      ],
    },
  };

  const res = await fetch(`${apiBase}/intake/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  assert.equal(res.status, 201);
  const data = await res.json();
  assert.ok(data.case_id.startsWith("CAS-"));
  assert.equal(data.case_type, "Fee mismatch");
  assert.equal(data.state, "received");
  assert.equal(data.exposure_amount, "500.00");
  assert.equal(data.deduplicated, false);

  // Verify created case appears in the review queue
  const listRes = await fetch(`${apiBase}/cases`);
  assert.equal(listRes.status, 200);
  const listData = await listRes.json();
  const found = listData.items.find((c) => c.case_id === data.case_id);
  assert.ok(found, `Case ${data.case_id} should appear in GET /cases`);
  assert.equal(found.counterparty_or_custodian, "Citigroup Global");

  // Verify case detail snapshot can be hydrated
  const snapRes = await fetch(`${apiBase}/cases/${data.case_id}`);
  assert.equal(snapRes.status, 200);
  const snapshot = await snapRes.json();
  assert.equal(snapshot.case_id, data.case_id);
  assert.ok(snapshot.proposal);
  assert.equal(snapshot.proposal.amount, "500.00");
  assert.ok(snapshot.evidence_citations.length >= 1);
});

test("Intake: POST /intake/events creates a corporate action case", async () => {
  const idempotencyKey = `FRONTEND-CA-${Date.now()}`;
  const payload = {
    event_id: `EVT-FE-CA-${Date.now()}`,
    source_system: "SWIFT",
    idempotency_key: idempotencyKey,
    event_type: "corporate_action.received",
    payload: {
      event_type: "Stock split",
      mandatory_or_voluntary: "mandatory",
      counterparty_or_custodian: "Euroclear",
      instrument_id: "US0378331005",
      currency: "USD",
      amount: "100000.00",
      desk_id: "CA_DESK",
      evidence_snippets: [
        {
          source_name: "SWIFT MT564",
          media_type: "text/plain",
          excerpt: "Mandatory 2:1 stock split effective 2026-09-30.",
        },
      ],
    },
  };

  const res = await fetch(`${apiBase}/intake/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  assert.equal(res.status, 201);
  const data = await res.json();
  assert.ok(data.case_id.startsWith("CAS-"));
  assert.equal(data.case_type, "Stock split");
  assert.equal(data.exposure_amount, "100000.00");
  assert.equal(data.deduplicated, false);
});

test("Intake: POST /intake/events deduplicates duplicate (source_system, idempotency_key)", async () => {
  const idempotencyKey = `FRONTEND-DUP-${Date.now()}`;
  const payload = {
    event_id: `EVT-DUP-${Date.now()}`,
    source_system: "DTCC",
    idempotency_key: idempotencyKey,
    event_type: "settlement.exception.received",
    payload: {
      break_type: "SSI break",
      counterparty: "Barclays Capital",
      instrument: "GB0002634946",
      currency: "GBP",
      expected_amount: "500.00",
      booked_amount: "500.00",
      desk_id: "EQ_LON",
    },
  };

  // First call -> 201 Created
  const res1 = await fetch(`${apiBase}/intake/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  assert.equal(res1.status, 201);
  const data1 = await res1.json();
  assert.equal(data1.deduplicated, false);

  // Second call -> 200 OK (deduplicated)
  const res2 = await fetch(`${apiBase}/intake/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  assert.equal(res2.status, 200);
  const data2 = await res2.json();
  assert.equal(data2.deduplicated, true);
  assert.equal(data2.case_id, data1.case_id);
  assert.ok(data2.message.includes("idempotency"));
});

test("Intake: POST /intake/events returns RFC 9457 Problem Details on invalid payload", async () => {
  const res = await fetch(`${apiBase}/intake/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_system: "", // Missing required source_system
      idempotency_key: "K",
      event_type: "settlement.exception.received",
      payload: {},
    }),
  });

  assert.equal(res.status, 422);
  const problem = await res.json();
  assert.equal(problem.title, "Unprocessable Content");
  assert.ok(problem.detail.includes("source_system"));
});

test("Runtime: GET /config/runtime provides active AI framework and model without credentials", async () => {
  const res = await fetch(`${apiBase}/config/runtime`);
  assert.equal(res.status, 200);
  const data = await res.json();

  assert.equal(data.framework, "openai");
  assert.equal(data.framework_display, "OpenAI");
  assert.equal(data.model, "gpt-4.1");
  assert.equal(data.orchestration_mode, "sequential");
  assert.ok(Array.isArray(data.supported_orchestration_modes));
  assert.ok(data.supported_orchestration_modes.includes("sequential"));
  assert.ok(data.supported_orchestration_modes.includes("parallel"));
  assert.ok(data.supported_orchestration_modes.includes("hierarchical"));

  // Security Invariant: Zero secrets or API keys exposed to browser
  const rawText = JSON.stringify(data).toLowerCase();
  assert.equal(rawText.includes("api_key"), false);
  assert.equal(rawText.includes("sk-"), false);
});

test("Intake: POST /intake/events captures selected orchestration_mode", async () => {
  const idempotencyKey = `FRONTEND-ORCH-${Date.now()}`;
  const payload = {
    event_id: `EVT-ORCH-${Date.now()}`,
    source_system: "MUREX",
    idempotency_key: idempotencyKey,
    event_type: "settlement.exception.received",
    payload: {
      break_type: "Fee mismatch",
      counterparty: "Morgan Stanley",
      instrument: "US0378331005",
      currency: "USD",
      expected_amount: "5000.00",
      booked_amount: "4800.00",
      desk_id: "EQ_NY",
      orchestration_mode: "parallel",
    },
  };

  const res = await fetch(`${apiBase}/intake/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  assert.equal(res.status, 201);
  const data = await res.json();
  assert.equal(data.orchestration_mode, "parallel");
});

