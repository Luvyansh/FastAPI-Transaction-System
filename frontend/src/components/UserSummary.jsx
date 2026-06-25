import { useState } from "react";
import { fetchUserSummary } from "../api";

export default function UserSummary() {
  const [userId, setUserId] = useState("");
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleLookup(event) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSummary(null);

    try {
      const data = await fetchUserSummary(userId);
      setSummary(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold">User Summary</h2>
      <form onSubmit={handleLookup} className="flex gap-2">
        <input
          type="text"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          required
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="User ID"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-900 disabled:opacity-50"
        >
          {loading ? "Loading…" : "Lookup"}
        </button>
      </form>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      {summary && (
        <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
          <div className="rounded-md bg-slate-50 p-3">
            <dt className="text-slate-500">Total Volume</dt>
            <dd className="text-lg font-semibold">${summary.total_volume}</dd>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <dt className="text-slate-500">Transactions</dt>
            <dd className="text-lg font-semibold">{summary.transaction_count}</dd>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <dt className="text-slate-500">Average Amount</dt>
            <dd className="text-lg font-semibold">${summary.average_amount}</dd>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <dt className="text-slate-500">Abuse Flagged</dt>
            <dd className={`text-lg font-semibold ${summary.abuse_flagged ? "text-red-600" : "text-green-600"}`}>
              {summary.abuse_flagged ? "Yes" : "No"}
            </dd>
          </div>
        </dl>
      )}
    </section>
  );
}
