import { useEffect, useState } from "react";
import { getIncidents } from "../api/incidentApi";

// ─────────────────────────────────────────────
// IncidentLog fetches ALL past incidents from FastAPI
// and displays them in a table.
//
// Key concepts used here:
// - useEffect: fetch data when component loads
// - useState: store the fetched data + loading/error states
// - Conditional rendering: show loader OR table based on state
// ─────────────────────────────────────────────

const SEVERITY_COLORS = {
  HIGH:   "text-red-400 bg-red-500/10",
  MEDIUM: "text-amber-400 bg-amber-500/10",
  LOW:    "text-blue-400 bg-blue-500/10",
};

export default function IncidentLog() {
  const [incidents, setIncidents] = useState([]); // the data array
  const [loading, setLoading]     = useState(true); // are we fetching?
  const [error, setError]         = useState(null); // did something go wrong?
  const [page, setPage]           = useState(1); // current page number
  const PER_PAGE = 8; // how many rows per page

  // useEffect with [] runs once when the component first appears.
  // This is where you fetch initial data.
  useEffect(() => {
    async function fetchData() {
      try {
        const data = await getIncidents(); // calls incidentApi.js
        setIncidents(data);
      } catch (err) {
        setError("Could not load incidents. Is the backend running?");
        console.error(err);
      } finally {
        setLoading(false); // always stop the loader
      }
    }
    fetchData();
  }, []); // [] means "only run once on mount"

  // PAGINATION LOGIC
  // Calculate which slice of the array to show on the current page.
  const totalPages = Math.ceil(incidents.length / PER_PAGE);
  const start = (page - 1) * PER_PAGE;
  const pageData = incidents.slice(start, start + PER_PAGE);

  // ── LOADING STATE ──
  if (loading) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-400">
        <div className="animate-spin w-6 h-6 border-2 border-slate-600 border-t-blue-400 rounded-full mr-3"/>
        Loading incidents...
      </div>
    );
  }

  // ── ERROR STATE ──
  if (error) {
    return (
      <div className="flex items-center justify-center h-48 text-red-400 text-sm font-mono">
        ⚠ {error}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">

      {/* HEADER */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-white font-bold text-lg tracking-tight">Incident Log</h2>
        <span className="text-xs text-slate-400 font-mono">{incidents.length} total</span>
      </div>

      {/* TABLE */}
      <div className="flex-1 overflow-x-auto">
        <table className="w-full text-sm">

          {/* TABLE HEADER ROW */}
          <thead>
            <tr className="border-b border-slate-700">
              {["ID", "Camera", "Location", "Severity", "Summary", "Time"].map(col => (
                <th key={col} className="text-left text-xs text-slate-500 uppercase tracking-wider font-semibold pb-3 pr-4">
                  {col}
                </th>
              ))}
            </tr>
          </thead>

          {/* TABLE BODY — one row per incident */}
          <tbody>
            {pageData.map((inc) => (
              <tr
                key={inc.id}
                className="border-b border-slate-800 hover:bg-slate-800/40 transition-colors"
              >
                <td className="py-3 pr-4 text-slate-500 font-mono text-xs">#{inc.id}</td>
                <td className="py-3 pr-4 text-slate-300 font-mono text-xs">{inc.camera_id}</td>
                <td className="py-3 pr-4 text-slate-300 text-xs">{inc.location}</td>
                <td className="py-3 pr-4">
                  {/* Severity badge using our color map above */}
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${SEVERITY_COLORS[inc.severity] || SEVERITY_COLORS.LOW}`}>
                    {inc.severity}
                  </span>
                </td>
                {/* Truncate long summaries with max-w + truncate */}
                <td className="py-3 pr-4 text-slate-400 text-xs max-w-xs truncate">{inc.summary}</td>
                <td className="py-3 text-slate-500 font-mono text-xs whitespace-nowrap">
                  {new Date(inc.timestamp).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* EMPTY STATE */}
        {incidents.length === 0 && (
          <div className="text-center text-slate-600 py-12 font-mono text-sm">
            No incidents recorded yet
          </div>
        )}
      </div>

      {/* PAGINATION CONTROLS */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-800">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 text-xs rounded-lg bg-slate-800 text-slate-300
              hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed
              border border-slate-700 transition-all"
          >
            ← Prev
          </button>
          <span className="text-xs text-slate-500 font-mono">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 text-xs rounded-lg bg-slate-800 text-slate-300
              hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed
              border border-slate-700 transition-all"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
