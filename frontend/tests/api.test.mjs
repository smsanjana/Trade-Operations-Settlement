import test from "node:test";
import assert from "node:assert/strict";

const apiBase = "http://127.0.0.1:8000/api/v1";

test("API: GET /cases retrieves real backend case list", async () => {
  const res = await fetch(`${apiBase}/cases`);
  assert.equal(res.status, 200);
  const data = await res.json();
  assert.ok(Array.isArray(data.items));
  assert.ok(data.items.length >= 4);

  const feeCase = data.items.find((c) => c.case_id === "TRD-28419");
  assert.ok(feeCase);
  assert.equal(feeCase.case_type, "Fee mismatch");
  assert.equal(feeCase.counterparty_or_custodian, "Northstar Securities");
});

test("API: GET /cases/{caseId} retrieves snapshot with ETag and citations", async () => {
  const res = await fetch(`${apiBase}/cases/TRD-28419`);
  assert.equal(res.status, 200);
  const etag = res.headers.get("etag");
  assert.ok(etag);
  assert.match(etag, /"TRD-28419-v\d+"/);

  const snapshot = await res.json();
  assert.equal(snapshot.case_id, "TRD-28419");
  assert.ok(snapshot.proposal);
  assert.equal(snapshot.proposal.amount, "450.00");
  assert.ok(Array.isArray(snapshot.evidence_citations));
  assert.equal(snapshot.evidence_citations.length, 2);
});

test("API: GET /cases/{caseId}/audit-events retrieves real audit trail", async () => {
  const res = await fetch(`${apiBase}/cases/TRD-28419/audit-events`);
  assert.equal(res.status, 200);
  const data = await res.json();
  assert.ok(Array.isArray(data.items));
  assert.ok(data.items.length >= 1);
  assert.equal(data.items[0].event_type, "intake.received");
});

test("API: POST /cases/{caseId}/decisions enforces If-Match and rejects stale ETag", async () => {
  // Stale ETag
  const staleRes = await fetch(`${apiBase}/cases/TRD-28419/decisions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "If-Match": '"TRD-28419-v999"',
    },
    body: JSON.stringify({ action: "approve", note: "Should fail with 409" }),
  });
  assert.equal(staleRes.status, 409);
  const problem = await staleRes.json();
  assert.equal(problem.title, "Conflict");
});

test("API: POST /cases/{caseId}/decisions rejects client-authored approver identity", async () => {
  const res = await fetch(`${apiBase}/cases/TRD-28419/decisions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "If-Match": '"TRD-28419-v1"',
    },
    body: JSON.stringify({
      action: "approve",
      approver_id: "attacker",
      note: "Should fail with 422",
    }),
  });
  assert.equal(res.status, 422);
});
