import { useState } from "react";
import TransactionForm from "./components/TransactionForm";
import UserSummary from "./components/UserSummary";
import RankingTable from "./components/RankingTable";

export default function App() {
  const [refreshKey, setRefreshKey] = useState(0);

  function handleTransactionSuccess() {
    setRefreshKey((key) => key + 1);
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-5xl px-4 py-6">
          <h1 className="text-2xl font-bold tracking-tight">Transaction Dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">
            Submit transactions, view user stats, and track the leaderboard.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-4 py-8">
        <div className="grid gap-6 md:grid-cols-2">
          <TransactionForm onSuccess={handleTransactionSuccess} />
          <UserSummary />
        </div>
        <RankingTable refreshKey={refreshKey} />
      </main>
    </div>
  );
}
