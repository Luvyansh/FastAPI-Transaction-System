import { useCallback, useEffect, useState } from "react";
import { fetchRanking } from "../api";

export default function RankingTable({ refreshKey }) {
  const [rankings, setRankings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadRankings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRanking();
      setRankings(data.rankings);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRankings();
  }, [loadRankings, refreshKey]);

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Leaderboard</h2>
        <button
          onClick={loadRankings}
          disabled={loading}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      {loading && <p className="text-sm text-slate-500">Loading rankings…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && rankings.length === 0 && (
        <p className="text-sm text-slate-500">No users ranked yet.</p>
      )}

      {rankings.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="py-2 pr-4 font-medium">Rank</th>
                <th className="py-2 pr-4 font-medium">User</th>
                <th className="py-2 pr-4 font-medium">Score</th>
                <th className="py-2 pr-4 font-medium">Volume</th>
                <th className="py-2 pr-4 font-medium">Tx Count</th>
                <th className="py-2 font-medium">Flagged</th>
              </tr>
            </thead>
            <tbody>
              {rankings.map((entry) => (
                <tr key={entry.user_id} className="border-b border-slate-100">
                  <td className="py-2 pr-4 font-medium">#{entry.rank}</td>
                  <td className="py-2 pr-4">{entry.user_id}</td>
                  <td className="py-2 pr-4 font-semibold">{entry.score}</td>
                  <td className="py-2 pr-4">${entry.total_volume}</td>
                  <td className="py-2 pr-4">{entry.transaction_count}</td>
                  <td className="py-2">
                    {entry.abuse_flagged ? (
                      <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700">
                        Flagged
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
