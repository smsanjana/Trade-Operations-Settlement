import { OperationsConsole } from "../../components/operations-console";
import { loadCases } from "../../lib/api";
import type { CaseSummary } from "../../lib/types";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Settlement Review Queue | Trade Operations",
  description: "Evidence-first settlement exception review and approval",
};

export default async function CasesQueuePage() {
  let initialSummaries: CaseSummary[] = [];
  let initialError: string | null = null;

  try {
    initialSummaries = await loadCases();
  } catch (err) {
    initialError =
      err instanceof Error
        ? err.message
        : "Backend service is unreachable on http://localhost:8000. Ensure the ASGI server is started.";
  }

  return <OperationsConsole initialSummaries={initialSummaries} initialError={initialError} />;
}
