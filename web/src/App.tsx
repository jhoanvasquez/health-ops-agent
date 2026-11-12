import { useCallback, useEffect, useState } from "react";

import { getCase, listPendingReview, listRecentCases, submitReview } from "./api";
import CaseView from "./components/CaseDetail";
import EmptyState from "./components/EmptyState";
import Sidebar from "./components/Sidebar";
import type { CaseDetail, CaseSummary, Outcome } from "./types";

export default function App() {
  const [pending, setPending] = useState<CaseSummary[]>([]);
  const [decided, setDecided] = useState<CaseSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshQueue = useCallback(async (): Promise<CaseSummary[]> => {
    const [pendingCases, recent] = await Promise.all([listPendingReview(), listRecentCases()]);
    setPending(pendingCases);
    setDecided(recent.filter((c) => c.reviewed_at !== null).slice(0, 6));
    return pendingCases;
  }, []);

  useEffect(() => {
    refreshQueue()
      .then((pendingCases) => setSelectedId(pendingCases[0]?.case_id ?? null))
      .catch((e: unknown) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [refreshQueue]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    setDetail(null);
    getCase(selectedId)
      .then(setDetail)
      .catch((e: unknown) => setError(String(e)));
  }, [selectedId]);

  const onReview = useCallback(
    async (decision: Outcome, note: string): Promise<void> => {
      if (!selectedId) return;
      try {
        await submitReview(selectedId, { decision, note });
        const pendingCases = await refreshQueue();
        setSelectedId(pendingCases[0]?.case_id ?? null);
      } catch (e: unknown) {
        setError(String(e));
      }
    },
    [selectedId, refreshQueue],
  );

  return (
    <div className="app">
      <Sidebar pending={pending} decided={decided} selectedId={selectedId} onSelect={setSelectedId} />
      <main className="main">
        {detail ? (
          <CaseView detail={detail} onReview={onReview} />
        ) : (
          <EmptyState error={error} loading={loading || selectedId !== null} />
        )}
      </main>
    </div>
  );
}
