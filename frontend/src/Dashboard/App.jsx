import { useState } from "react";
import AlertFeed from "./components/AlertFeed";
import CameraMap from "./components/CameraMap";
import IncidentLog from "./components/IncidentLog";
import HeatmapWidget from "./components/HeatmapWidget";

// ─────────────────────────────────────────────
// App.jsx is the ROOT component — the top of the component tree.
// Everything renders inside here.
//
// LAYOUT STRUCTURE:
//   ┌─────────────────────────────────────────┐
//   │  HEADER (top bar)                        │
//   ├──────────────┬──────────────────────────┤
//   │  LEFT PANEL  │  RIGHT PANEL             │
//   │  AlertFeed   │  [tab: Map | Log | Heat] │
//   └──────────────┴──────────────────────────┘
//
// We use Tailwind CSS utility classes for all styling.
// "flex" = flexbox layout, "grid" = CSS grid, "p-4" = padding, etc.
// ─────────────────────────────────────────────

// The right panel has 3 tabs. This array drives both the tab buttons
// and which component to render.
const TABS = [
  { id: "map",      label: "📍 Camera Map",    Component: CameraMap },
  { id: "log",      label: "📋 Incident Log",  Component: IncidentLog },
  { id: "heatmap",  label: "🔥 Risk Heatmap",  Component: HeatmapWidget },
];

export default function App() {
  // activeTab controls which right-panel tab is currently visible.
  const [activeTab, setActiveTab] = useState("map");

  // Find the component for the active tab so we can render it.
  const ActiveComponent = TABS.find(t => t.id === activeTab)?.Component;

  return (
    // min-h-screen = at least 100% of viewport height
    // bg-slate-950 = very dark background
    // font-sans = system sans-serif font
    <div className="min-h-screen bg-slate-950 text-white font-sans flex flex-col">

      {/* ── HEADER ── */}
      <header className="border-b border-slate-800 px-6 py-4 flex items-center justify-between
        bg-slate-950/80 backdrop-blur-sm sticky top-0 z-10">

        <div className="flex items-center gap-3">
          {/* Logo / brand */}
          <div className="w-8 h-8 rounded-lg bg-blue-500 flex items-center justify-center text-sm font-bold">
            🚇
          </div>
          <div>
            <h1 className="text-white font-bold text-base tracking-tight">SubGuard</h1>
            <p className="text-slate-500 text-xs">Transit Safety Dashboard</p>
          </div>
        </div>

        {/* Right side of header: current time */}
        <div className="text-slate-400 text-xs font-mono">
          {new Date().toLocaleDateString("en-CA", {
            weekday: "short", year: "numeric", month: "short", day: "numeric"
          })}
        </div>
      </header>

      {/* ── MAIN CONTENT ── */}
      {/* flex-1 = takes remaining height, overflow-hidden = prevents double scrollbars */}
      <main className="flex-1 flex overflow-hidden p-4 gap-4">

        {/* ── LEFT PANEL: Live Alert Feed ── */}
        {/* w-80 = fixed 320px width, flex-shrink-0 = never shrink */}
        <aside className="w-80 flex-shrink-0 bg-slate-900 rounded-2xl border border-slate-800 p-4 overflow-hidden flex flex-col">
          <AlertFeed />
        </aside>

        {/* ── RIGHT PANEL: Tabs ── */}
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
          {/* flex-1 = fill remaining space, overflow-y-auto = scroll if needed */}
          <div className="flex-1 overflow-y-auto p-6">
            {/* Render whichever component matches the active tab */}
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
