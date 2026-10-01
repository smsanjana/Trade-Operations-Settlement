# Trade Operations & Settlement

> **An enterprise multi-agent system for autonomous trade break resolution, evidence reconciliation, and governed settlement operations.**

[![CI](https://github.com/smsanjana/trade-operations-settlement/actions/workflows/ci.yml/badge.svg)](https://github.com/smsanjana/trade-operations-settlement/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15.5-black.svg)](https://nextjs.org/)
[![React 19](https://img.shields.io/badge/React-19.1-blue.svg)](https://react.dev/)
[![Tests](https://img.shields.io/badge/tests-67%20passed-brightgreen.svg)](backend/tests)
[![Author](https://img.shields.io/badge/Author-Sanjana%20S%20Marigoudar-blueviolet.svg)](#author)

---

## 1. Executive Overview

In modern institutional capital markets, post-trade settlement operations are subject to compressed settlement cycles (**T+1** under SEC Rule 15c6-1 and global equivalents). When discrepancies arise between broker confirmations, trading desk chat logs, and internal accounting systems—known as **trade breaks**—settlement fails occur. Unresolved fails result in mandatory financial penalties (e.g., CSDR in Europe), counterparty credit exposure, and substantial operational overhead.

**Trade Operations & Settlement** is an AI-orchestrated post-trade exception management and corporate action platform. Built on the **PortAgent SDK** runtime, it pairs autonomous multi-agent interpretation of ambiguous, unstructured trade evidence (chat transcripts, PDF confirmations, email records) with **strictly deterministic** financial calculations and policy gates.

The platform achieves:
- **Straight-Through Processing (STP)** for low-risk, high-confidence trade breaks within pre-configured exposure limits.
- **Explainable, Cited Escalation**: High-exposure, ambiguous, or disputable breaks are surfaced to human analysts with exact evidence citations and pre-drafted amendments.
- **Dual-Control Governance**: Enforces separation of duties, maker-checker authorization, RFC 9457 Problem Details error handling, optimistic concurrency control (ETags), and an append-only audit trail.

---

## 2. Problem Statement & Business Context

In institutional trade processing, exceptions happen frequently:
1. **Fee & Commission Mismatches**: Broker invoices or contract notes differ from trader blotter bookings.
2. **Settlement Date Conflicts**: Trading counterparties book differing value dates due to holiday calendars or convention differences.
3. **Standard Settlement Instructions (SSI) Discrepancies**: Incorrect depository routing, BIC/SWIFT code mismatches, or sub-custodian account errors.
4. **Corporate Actions Processing**: Conflicting announcements across custodians and market data vendors require golden-copy extraction and account-level entitlement calculations.

### Why Traditional Systems Fall Short
- **Heuristic Rule Engines**: Rigid and break down when brokers alter confirmation formats or when agreements are clarified in trader chats.
- **Unconstrained AI / LLMs**: Pure LLM approaches risk hallucinating ledger balances, executing unverified financial mutations, or miscalculating basis points.

### The Solution: Governed Separation of Concerns
This project implements a strict architectural firewall:
- **Agents Interpret**: Specialized agents ingest messy, untrusted inputs and produce structured findings with citations and confidence scores.
- **Deterministic Services Calculate & Decide**: Mathematical calculations (basis points, fee differences, tax withholding), ledger interactions, and policy routing are handled exclusively by verified deterministic Python code. Agents receive **zero ledger-write capabilities**.

---

## 3. Objectives & Key Capabilities

- **Autonomous Evidence Synthesis**: Ingests multi-party chat transcripts and PDF confirmations, resolving conversational chronology (e.g., superseding amendments made later in a conversation).
- **Dispute Detection**: Detects counterparty contradictions and automatically flags them as `COUNTERPARTY_DISPUTE` rather than making autonomous guesses.
- **Deterministic Policy Gate**: Evaluates desk limits, exposure thresholds, and confidence scores against versioned policy rules.
- **Dual-Control Authorization**: High-value proposals require independent maker-checker approvals before ledger release.
- **Concurrency Control & Idempotency**: All ingestion events enforce idempotent deduplication; decision endpoints use `If-Match` ETag headers to prevent race conditions.
- **Interactive Analyst Console**: Full-stack Next.js 15 web application enabling trade analysts and supervisors to inspect evidence citations side-by-side and execute governed decisions.

---

## 4. System Architecture

```
                                 +-------------------------------------+
                                 |         External Intake Feed        |
                                 | (Murex, Trax, SWIFT, Broker PDFs)   |
                                 +-------------------------------------+
                                                    |
                                                    | POST /api/v1/intake/events
                                                    v
+----------------------------------------------------------------------------------------------------+
|                                    BACKEND APPLICATION RUNTIME                                     |
|                                                                                                    |
|  +------------------------+      +-------------------------+      +-----------------------------+  |
|  |   Ingestion Boundary   | ---> |  Idempotency & Storage  | ---> | Untrusted Content Screening |  |
|  |   (Envelope Validate)  |      |   (StateStore / SQLite) |      | (Prompt Injection Shield)   |  |
|  +------------------------+      +-------------------------+      +-----------------------------+  |
|                                                                                  |                 |
|                                                                                  v                 |
|  +----------------------------------------------------------------------------------------------+  |
|  |                                  PORTAGENT AGENTIC RUNTIME                                   |  |
|  |                                                                                              |  |
|  |     [Break Classifier]       [Trade Evidence Agent]       [Confirmation Extractor]           |  |
|  |     - Classifies type        - Extracts agreed terms      - Extracts booked terms            |  |
|  |     - tool_retrieve_exception- Chronology & citations     - Page-level provenance            |  |
|  |             \                        |                               /                       |  |
|  |              +-----------------------+------------------------------+                        |  |
|  |                                      v                                                       |  |
|  |                           [Reconciliation Agent]                                             |  |
|  |                           - Reconciles chat vs confirm                                       |  |
|  |                           - Flags disputes / conflicts                                       |  |
|  +----------------------------------------------------------------------------------------------+  |
|                                                  |                                                 |
|                                                  v                                                 |
|  +----------------------------------------------------------------------------------------------+  |
|  |                                   DETERMINISTIC CONTROLS                                     |  |
|  |                                                                                              |  |
|  |  +-----------------------------+  +----------------------------+  +-----------------------+  |  |
|  |  |  Financial Calculations     |  |   Policy Gate Evaluator    |  |  Dual Control Service |  |  |
|  |  |  - Fee difference           |  |   - Auto-post limit checks |  |  - Maker-checker slots|  |  |
|  |  |  - Amendment proposal       |  |   - Confidence thresholds  |  |  - ETag concurrency   |  |  |
|  |  +-----------------------------+  +----------------------------+  +-----------------------+  |  |
|  +----------------------------------------------------------------------------------------------+  |
|                                                  |                                                 |
|                                                  v                                                 |
|  +----------------------------------------------------------------------------------------------+  |
|  |                          REST API (Starlette / Uvicorn ASGI)                                 |  |
|  |  /api/v1/cases  |  /api/v1/cases/{id}  |  /api/v1/cases/{id}/decisions  |  /api/v1/audit-events  |  |
|  +----------------------------------------------------------------------------------------------+  |
+----------------------------------------------------------------------------------------------------+
                                                   |
                                                   | REST / JSON
                                                   v
+----------------------------------------------------------------------------------------------------+
|                                    FRONTEND ANALYST CONSOLE                                        |
|                                                                                                    |
|    Next.js 15 (App Router) | React 19 | TypeScript | Tailwind CSS                                  |
|    - Real-time Case Queue & Filtering (Priority, State, Type)                                      |
|    - Side-by-side Evidence Dossier with Excerpt Highlighting                                       |
|    - Deterministic Proposal Breakdown & Policy Reason Codes                                        |
|    - Governed Decision Submission (Approve, Amend, Reject with Notes)                             |
|    - Full Event-Sourced Audit Timeline                                                             |
+----------------------------------------------------------------------------------------------------+
```

---

## 5. Multi-Agent Architecture

The agentic layer is governed through PortAgent `AgentSpec` contracts. Each agent has a focused responsibility and is strictly restricted to **allowlisted read-only retrieval tools**:

```python
PROHIBITED_AGENT_TOOL_NAMES = {
    "ledger_write", "post_transaction", "submit_ledger_entry",
    "mutate_account_balance", "execute_financial_transfer",
    "override_policy", "authorize_payment"
}
```

### Agent Roster

| Agent | Contract ID | Primary Responsibility | Assigned Tools | Output Artifact |
|---|---|---|---|---|
| **Break Classifier** | `break_classifier` | Inspects incoming exception text and maps it into supported categories (`fee_break`, `commission_break`, `settlement_date_break`, `ssi_break`, or `unknown`). | `tool_retrieve_exception` | `AgentFindingRecord` with break type and exception excerpt citation. |
| **Trade Evidence Agent** | `trade_evidence` | Parses multi-party trader/broker chat threads. Evaluates temporal sequence, ensuring agreements made later in the thread supersede earlier bids. | `tool_retrieve_chat` | `AgentFindingRecord` with agreed terms, confidence score, and message ID citations. |
| **Confirmation Extractor** | `confirm_extractor` | Parses electronic contract notes, broker confirmations, and SWIFT messages to extract economic terms. | `tool_retrieve_confirm` | `AgentFindingRecord` with confirmed terms, page/locator citations. |
| **Reconciliation Agent** | `reconciler` | Performs semantic comparison between chat findings and confirmation findings. Flags matches or identifies counterparty disputes. | None (internal reasoning) | `AgentFindingRecord` (`AGREED` vs `COUNTERPARTY_DISPUTE`), escalates if conflicting. |

---

## 6. Orchestration Modes

The platform supports three distinct PortAgent orchestration modes, configurable via the `ORCHESTRATION_MODE` environment variable or directly in the intake payload:

1. **Sequential Mode (`sequential`)**:
   - Executes agents in linear topological order: `break_classifier` $\to$ `trade_evidence` $\to$ `confirm_extractor` $\to$ `reconciler`.
   - Best for deterministic debugging and predictable execution tracing.

2. **Parallel Mode (`parallel`)**:
   - Dispatches independent information retrieval tasks concurrently across worker threads using `PARALLEL_MAX_WORKERS`.
   - `trade_evidence` and `confirm_extractor` execute simultaneously, cutting latency by up to 50% for high-volume exception queues.

3. **Hierarchical Mode (`hierarchical`)**:
   - A supervisor agent (`SUPERVISOR_AGENT_ID`) coordinates task delegation, dynamically calling sub-agents based on the complexity of the trade break.
   - Ideal for multi-leg trade breaks or cases involving cross-currency hedges.

---

## 7. Settlement Exception Recovery Workflow

The complete end-to-end exception resolution flow runs as follows:

```
[Fail Event Received] 
        │
        ▼
[Idempotency Check] ──(Duplicate)──► Return Existing Case Snapshot (HTTP 200)
        │ (New)
        ▼
[Untrusted Content Screening]
        │ (Screened)
        ▼
[Agent Execution Pipeline]
  1. BreakClassifier categorizes the failure
  2. TradeEvidenceAgent extracts latest agreed terms (with chronology)
  3. ConfirmationExtractor extracts confirmation economic terms
  4. ReconciliationAgent checks for counterparty agreement
        │
        ▼
[Deterministic Arithmetic]
  - Calculates exact delta: (Agreed Fee - Booked Fee)
  - Prepares amendment proposal with value date and ledger account
        │
        ▼
[Policy Gate Evaluation]
  ├── If Confidence >= 0.95 AND Exposure <= $10,000 AND Match == True:
  │     └── Auto-Resolved (Straight-Through Processing)
  │
  ├── If Exposure > $100,000:
  │     └── Routes to Dual Control (Requires 2 independent supervisor approvals)
  │
  └── If Counterparty Dispute OR Confidence < 0.95:
        └── Routes to Analyst Review Queue (Awaiting Human Decision)
```

---

## 8. Corporate Action Processing Workflow

### Implemented Foundation (Release 1)
- **Intake & Routing**: Ingestion endpoint accepts `corporate_action.received` events with standard fields (`event_id`, `event_type`, `record_date`, `ratio_or_rate`, `currency`).
- **Validation & Deduplication**: Corporate action events are validated against JSON schemas and deduplicated using composite `(source_system, idempotency_key)` constraints.
- **Console Visibility**: Ingested corporate actions appear in the analyst console queue with distinct badge indicators and state tracking.

### Planned Enhancements (Roadmap)
- Multi-source golden-copy generation across DTCC, Euroclear, and Bloomberg feeds.
- Automated tax-lot population queries and entitlement calculations (cash-in-lieu and fractional share rounding).
- Automated election capture for voluntary corporate actions.

---

## 9. Governance, Security & Audit Controls

- **Zero-Trust Model Access**: All unstructured broker texts and emails are treated as untrusted and screened prior to agent ingestion.
- **Strict Separation of Duties**: The PortAgent agent runtime cannot execute financial mutations. Any ledger proposal must be validated by the policy gate and authorized by an authenticated user.
- **Optimistic Concurrency Control**: All decision endpoints (`POST /cases/{caseId}/decisions`) mandate the `If-Match` header with the current case ETag. Stale updates return HTTP 412 (Precondition Failed).
- **Dual-Control Enforcement**: When an exposure exceeds the dual-control limit (e.g. $100,000), two distinct approvers must submit matching approval actions before execution. Client-authored approver identities are rejected.
- **RFC 9457 Problem Details**: Errors (missing fields, validation errors, stale ETags) return structured RFC 9457 error documents.
- **Append-Only Audit Log**: Every state transition, agent finding, policy evaluation, and user decision generates an immutable `AuditEventRecord` with timestamps, actors, and payload hashes.

---

## 10. Technology Stack

### Backend
- **Python 3.12**: Core runtime leveraging modern type annotations.
- **PortAgent SDK 0.0.2**: Agent specifications, lifecycle orchestration, and tool wiring.
- **Starlette / FastAPI & Uvicorn**: High-performance asynchronous ASGI web services.
- **Pydantic & JSONSchema**: Schema validation and runtime contract enforcement.
- **PyYAML & Psycopg**: Configuration parsing and relational persistence support.

### Frontend
- **Next.js 15.5 (App Router)**: Modern React framework with server-side rendering and fast client navigation.
- **React 19.1**: Latest React core with improved hook performance.
- **TypeScript 5.7**: Strict type-checking across API clients, fixtures, and components.
- **Tailwind CSS**: Responsive, institutional-grade dark/light theme styling.

### Quality & Testing
- **Pytest 8.4**: Unit, contract, integration, security, and workflow test execution.
- **Ruff & Mypy**: Static analysis, formatting, and strict type verification.
- **Node.js Test Runner & Vitest**: Fast frontend integration and unit testing.
- **Playwright**: End-to-end browser test automation capabilities.

---

## 11. Repository Structure

```
trade-operations-settlement/
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated GitHub Actions CI workflow
├── backend/
│   ├── pyproject.toml           # Python build config, dependencies, tools
│   ├── uv.lock                  # Pinned dependency lockfile
│   ├── Dockerfile               # Production container definition
│   ├── src/
│   │   └── trade_operations_settlement/
│   │       ├── api/
│   │       │   ├── main.py      # Starlette application, routes, middleware
│   │       │   ├── intake.py    # Exception ingestion & deduplication
│   │       │   ├── cases.py     # Case listing and state query endpoints
│   │       │   └── security.py  # ETag validation, auth, dual-control logic
│   │       ├── application/
│   │       │   ├── agents/      # PortAgent AgentSpecs (classifier, evidence, reconciler)
│   │       │   ├── tools/       # Deterministic tools (audit, calculations, policy gate)
│   │       │   └── workflows/   # Workflow engine runtime and orchestration service
│   │       └── config/          # Observability, policy settings, logging
│   └── tests/
│       ├── contract/            # OpenAPI contract and spec validation tests
│       ├── integration/         # API endpoints, state store, provider switching tests
│       ├── security/            # Identity boundaries, guardrail, and ETag tests
│       ├── unit/                # Pure-logic calculation, policy gate, and MCP tests
│       └── workflow/            # PortAgent agent and workflow execution tests
├── frontend/
│   ├── app/                     # Next.js App Router (cases view, create case)
│   ├── components/              # Interactive UI components (console, case creator)
│   ├── lib/                     # Typed API client, mock fixtures, interfaces
│   ├── tests/                   # Node test runner integration tests
│   ├── package.json             # Frontend dependencies and scripts
│   ├── tsconfig.json            # TypeScript compiler configuration
│   └── Dockerfile               # Multi-stage frontend container build
├── specs/                       # Spec Kit documentation artifacts
│   └── 001-trade-operations-settlement/
│       ├── spec.md              # Feature specification
│       ├── plan.md              # Technical implementation plan
│       ├── tasks.md             # Detailed engineering task list
│       ├── data-model.md        # Entities, relationships, and lifecycle
│       ├── research.md          # Architectural decisions and tradeoffs
│       └── contracts/           # OpenAPI and AsyncAPI schemas
├── UseCase.md                   # Full product requirements and actor matrix
├── compose.yaml                 # Docker Compose multi-service deployment
├── .env.example                 # Sanitized configuration template
└── .env.synthetic.example       # Non-production synthetic profile template
```

---

## 12. Installation & Environment Setup

### Prerequisites
- **Python 3.12+**
- **Node.js 20+** and **npm**
- **Git**

### 1. Clone the Repository
```bash
git clone https://github.com/smsanjana/trade-operations-settlement.git
cd trade-operations-settlement
```

### 2. Configure Environment Variables
Copy the sanitized environment template:
```bash
cp .env.example .env
```

Key configuration variables:
```env
# AI Framework / Provider Selection
AI_PROVIDER=openai
FRAMEWORK=openai

# Model Configuration
OPENAI_MODEL=gpt-4.1

# Orchestration Mode: sequential | parallel | hierarchical
ORCHESTRATION_MODE=sequential
PARALLEL_MAX_WORKERS=4

# Operating Mode: synthetic | production
TRADE_OPS_ENV=synthetic
```

---

## 13. Backend Startup Instructions

```powershell
cd backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1   # On Linux/macOS: source .venv/bin/activate

# Install dependencies in editable mode with development tools
pip install -e ".[dev]"

# Start ASGI API server
uvicorn trade_operations_settlement.api.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend API documentation is available at `http://127.0.0.1:8000/api/v1/cases`.

---

## 14. Frontend Startup Instructions

In a separate terminal window:
```powershell
cd frontend

# Install dependencies from lockfile
npm ci

# Start Next.js development server
npm run dev
```
Open your browser at **`http://localhost:3000`** to access the Analyst & Approver Console.

---

## 15. Verified API Endpoints & Usage

### 1. Ingest an Exception
```bash
curl -X POST http://127.0.0.1:8000/api/v1/intake/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "EVT-2026-9901",
    "event_type": "settlement_fail.received",
    "source_system": "MUREX",
    "idempotency_key": "IDEM-MUREX-9901",
    "orchestration_mode": "sequential",
    "payload": {
      "exception_type": "fee_break",
      "instrument_id": "US0378331005",
      "counterparty": "Apex Clearing",
      "currency": "USD",
      "expected_amount": "5000.00",
      "booked_amount": "5450.00",
      "trade_date": "2026-08-25"
    }
  }'
```

### 2. Query Case Details with ETag
```bash
curl -i http://127.0.0.1:8000/api/v1/cases/TRD-28419
```
*Returns `ETag: W/"1"` in HTTP response header.*

### 3. Record a Governed Approval Decision
```bash
curl -X POST http://127.0.0.1:8000/api/v1/cases/TRD-28419/decisions \
  -H "Content-Type: application/json" \
  -H 'If-Match: W/"1"' \
  -H "X-Actor-Id: supervisor.john" \
  -d '{
    "action": "approve",
    "note": "Verified broker confirmation matches chat record."
  }'
```

### 4. Query Runtime Configuration
```bash
curl http://127.0.0.1:8000/api/v1/config/runtime
```
*Returns active AI framework and orchestration mode without exposing credentials.*

---

## 16. Verification & Test Results

The repository includes a comprehensive, multi-layer automated test suite:

### 1. Backend Automated Tests (Pytest)
```powershell
cd backend
pytest
```
**Results:** **`67 passed, 2 warnings in 22.12s`**
- `tests/contract/`: OpenAPI schema conformance, intake validation, RFC 9457 error contracts.
- `tests/integration/`: State store operations, API endpoints, runtime framework switching (`openai`, `langgraph`, `adk`, `crewai`, `semantic_kernel`).
- `tests/security/`: Guardrails, identity boundaries, ETag concurrency, prevention of unauthorized approver override.
- `tests/unit/`: Mathematical calculations, policy gates, MCP boundary integration.
- `tests/workflow/`: Multi-agent execution, break classification, and reconciliation workflows.

### 2. Frontend Type-checking and Production Build
```powershell
cd frontend
npm run typecheck    # tsc --noEmit
npm run build        # next build
```
**Results:**
- `tsc --noEmit`: Completed with **0 errors**.
- `next build`: Optimized production bundle generated in **2.8s**.

### 3. Frontend / Backend Integration Tests
```powershell
cd frontend
npm test             # node --test tests/*.test.mjs
```
**Results:** **`11 passed, 0 failed in 523ms`** against live backend API.

---

## 17. Security & Privacy Safeguards

- **Zero Secrets Tracked**: `.env` is permanently excluded via `.gitignore`. Live API keys and database credentials are never committed.
- **Synthetic Test Mode**: The system includes a fully isolated synthetic mode (`TRADE_OPS_ENV=synthetic`) using seeded data fixtures for testing without external exchange or broker connectivity.
- **Prompt Injection Defense**: Text from counterparties is isolated and processed only through constrained agent prompts requiring structured output schemas.
- **Immutable Auditability**: All administrative actions and agent outputs are cryptographically hashed and logged to an append-only store.

---

## 18. Limitations & Future Roadmap

- **External Ledger Connectivity**: Release 1 generates compliant amendment proposals; direct SWIFT MT548/ISO 20022 message dispatch to live custody networks is planned for Release 2.
- **Voluntary Corporate Actions**: Complex election capture (e.g. rights issues, tender offers with oversubscription) is documented in `specs/` and scheduled for subsequent iterations.
- **Distributed Lock Management**: The current prototype uses in-memory and SQLite-backed optimistic locking; production multi-pod deployments will transition to distributed Redis locks.

---

## Author

**Sanjana S Marigoudar**  
*Software Engineer & AI Systems Developer*  
- **Email**: [sanjanasmarigoudar@gmail.com](mailto:sanjanasmarigoudar@gmail.com)  
- **GitHub**: [@smsanjana](https://github.com/smsanjana)
