import { useState, useEffect, useRef } from "react";
import toast, { Toaster } from "react-hot-toast";
import { useSocket } from "./hooks/useSocket";
import AlertFeed from "./components/AlertFeed";
import CameraMap from "./components/CameraMap";
import IncidentLog from "./components/IncidentLog";
import HeatmapWidget from "./components/HeatmapWidget";

// ─────────────────────────────────────────────
// App.jsx — root component
//
// WHAT CHANGED FROM ORIGINAL:
// 1. Added react-hot-toast imports
// 2. Added useSocket() call here at the root level
// 3. Added useEffect that watches the alerts array —
//    whenever a new alert comes in, fires a toast popup
//    regardless of which tab the user is currently viewing
//
// WHY AT ROOT LEVEL?
// The toast needs to fire no matter which tab is open.
// If it lived inside AlertFeed.jsx, it would only work
// when the user is looking at the alerts tab.
// ─────────────────────────────────────────────

const TABS = [
  { id: "map",     label: "📍 Camera Map",   Component: CameraMap },
  { id: "log",     label: "📋 Incident Log", Component: IncidentLog },
  { id: "heatmap", label: "🔥 Risk Heatmap", Component: HeatmapWidget },
];

// Severity → emoji for toast message
const SEVERITY_EMOJI = {
  critical: "🔴",
  high:     "🟠",
  medium:   "🟡",
  low:      "🔵",
  HIGH:     "🔴",
  MEDIUM:   "🟡",
  LOW:      "🔵",
};

export default function App() {
  const [activeTab, setActiveTab] = useState("map");

  // ── TOAST SYSTEM ──
  // useSocket() is called here at root so we can watch for new alerts
  // and fire toasts globally, regardless of which tab is open.
  // AlertFeed.jsx also calls useSocket() independently for the alert list —
  // two calls to the same hook = two separate WebSocket connections,
  // which is fine for a hackathon demo.
  const { alerts } = useSocket();

  // useRef stores a value between renders without causing re-renders.
  // We use it to track how many alerts existed on the last render,
  // so we only toast when the count actually increases.
  const prevCountRef = useRef(0);

  useEffect(() => {
    // Only fire toast if alerts array grew (new alert came in)
    if (alerts.length > prevCountRef.current) {
      const latest = alerts[0]; // newest alert is always index 0

      toast(
        `${SEVERITY_EMOJI[latest.severity] || "⚠️"} ${latest.location || "Unknown location"} — ${latest.camera_id || "Unknown camera"}`,
        {
          duration: 6000,           // stays on screen 6 seconds
          position: "top-right",
          style: {
            background:   "#1e293b",
            color:        "#f1f5f9",
            border:       "1px solid #ef4444",
            borderRadius: "12px",
            fontSize:     "13px",
            fontFamily:   "monospace",
            padding:      "14px 18px",
          },
        }
      );
    }

    // Update the ref to current count for next render
    prevCountRef.current = alerts.length;
  }, [alerts]); // runs every time alerts array changes

  const ActiveComponent = TABS.find(t => t.id === activeTab)?.Component;

  return (
    <div className="min-h-screen bg-slate-950 text-white font-sans flex flex-col">

      {/* Toaster renders the actual toast popup container */}
      {/* Must be inside the return so it's always mounted */}
      <Toaster position="top-right" />

      {/* ── HEADER ── */}
      <header className="border-b border-slate-800 px-6 py-4 flex items-center justify-between
        bg-slate-950/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-500 flex items-center justify-center text-sm font-bold">
            🚇
          </div>
          <div>
            <h1 className="text-white font-bold text-base tracking-tight">SubGuard</h1>
            <p className="text-slate-500 text-xs">Transit Safety Dashboard</p>
          </div>
        </div>
        <div className="text-slate-400 text-xs font-mono">
          {new Date().toLocaleDateString("en-CA", {
            weekday: "short", year: "numeric", month: "short", day: "numeric"
          })}
        </div>
      </header>

      {/* ── MAIN CONTENT ── */}
      <main className="flex-1 flex overflow-hidden p-4 gap-4">

        {/* LEFT PANEL — Live Alert Feed */}
        <aside className="w-80 flex-shrink-0 bg-slate-900 rounded-2xl border border-slate-800 p-4 overflow-hidden flex flex-col">
          <AlertFeed />
        </aside>

        {/* RIGHT PANEL — Tabbed views */}
        <section className="flex-1 bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden flex flex-col">

          {/* TAB BAR */}
          <div className="flex border-b border-slate-800 px-4 pt-4 gap-1">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  px-4 py-2 text-xs font-semibold rounded-t-lg transition-all duration-200
                  ${activeTab === tab.id
                    ? "bg-slate-800 text-white border border-b-0 border-slate-700"
                    : "text-slate-500 hover:text-slate-300"}
                `}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* TAB CONTENT */}
          <div className="flex-1 overflow-y-auto p-6">
            {ActiveComponent && <ActiveComponent />}
          </div>

        </section>
      </main>

      {/* ── FOOTER ── */}
      <footer className="border-t border-slate-800 px-6 py-2 flex items-center justify-between">
        <p className="text-slate-600 text-xs font-mono">SubGuard v1.0 — Hack Canada 2025</p>
        <p className="text-slate-600 text-xs font-mono">Powered by Gemini · Vultr · Tailscale · Solana</p>
      </footer>

    </div>
  );
}
