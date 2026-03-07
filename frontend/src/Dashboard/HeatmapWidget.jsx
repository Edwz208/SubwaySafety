import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { getHeatmapData } from "../api/incidentApi";

// ─────────────────────────────────────────────
// HeatmapWidget fetches aggregated incident counts
// per location (platform/zone) from the backend,
// then renders a bar chart using Recharts.
//
// Recharts works like this:
//   <ResponsiveContainer> — makes the chart fill its parent div
//     <BarChart data={array}> — the chart, takes your data array
//       <Bar dataKey="count"> — which field in each object to use as bar height
// ─────────────────────────────────────────────

// Color scale: bars get a different color based on how high their count is.
function getBarColor(value, max) {
  const ratio = value / max;
  if (ratio > 0.7) return "#ef4444"; // red   = high risk
  if (ratio > 0.4) return "#f59e0b"; // amber = medium risk
  return "#3b82f6";                  // blue  = low risk
}

// MOCK DATA: used if the backend isn't running yet.
// Replace with real API data once your backend is up.
const MOCK_DATA = [
  { location: "Platform 1", count: 3 },
  { location: "Platform 2", count: 11 },
  { location: "Platform 3", count: 7 },
  { location: "Entrance",   count: 2 },
  { location: "Exit Gate",  count: 5 },
  { location: "Stairs A",   count: 8 },
];

export default function HeatmapWidget() {
  const [data, setData]       = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const result = await getHeatmapData();
        setData(result);
      } catch {
        // If backend isn't ready, fall back to mock data so the UI still works
        console.warn("Heatmap API unavailable — using mock data");
        setData(MOCK_DATA);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  // Find the maximum count value so we can calculate relative colors
  const maxCount = Math.max(...data.map(d => d.count), 1);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-400 text-sm">
        <div className="animate-spin w-5 h-5 border-2 border-slate-600 border-t-blue-400 rounded-full mr-2"/>
        Loading heatmap...
      </div>
    );
  }

  return (
    <div>
      {/* HEADER */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-white font-bold text-lg tracking-tight">Risk Heatmap</h2>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500"/>Low</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500"/>Med</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500"/>High</span>
        </div>
      </div>

      {/* RECHARTS BAR CHART */}
      {/* ResponsiveContainer makes the chart stretch to fill its parent */}
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>

          {/* XAxis: the location names along the bottom */}
          <XAxis
            dataKey="location"
            tick={{ fill: "#64748b", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />

          {/* YAxis: the incident count numbers on the left */}
          <YAxis
            tick={{ fill: "#64748b", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />

          {/* Tooltip: the popup that appears when you hover a bar */}
          <Tooltip
            contentStyle={{
              background: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "8px",
              color: "#e2e8f0",
              fontSize: "12px",
            }}
            cursor={{ fill: "rgba(255,255,255,0.05)" }}
            formatter={(value) => [`${value} incidents`, "Count"]}
          />

          {/* Bar: the actual bars. dataKey="count" means use the "count" field from each data object */}
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {/* Cell lets us set individual bar colors based on value */}
            {data.map((entry, index) => (
              <Cell key={index} fill={getBarColor(entry.count, maxCount)} />
            ))}
          </Bar>

        </BarChart>
      </ResponsiveContainer>

      {/* MOST DANGEROUS ZONE CALLOUT */}
      {data.length > 0 && (() => {
        const hotspot = data.reduce((a, b) => a.count > b.count ? a : b);
        return (
          <div className="mt-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <p className="text-xs text-red-400 font-semibold">
              ⚠ Highest risk zone: <span className="text-red-300">{hotspot.location}</span>
              <span className="text-slate-500 ml-2">({hotspot.count} incidents)</span>
            </p>
          </div>
        );
      })()}
    </div>
  );
}
