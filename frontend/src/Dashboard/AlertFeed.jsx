import { useSocket } from "../hooks/useSocket";
import AlertCard from "./AlertCard";

// ─────────────────────────────────────────────
// AlertFeed is the main live panel.
// It uses the useSocket hook to get real-time alerts,
// then renders a list of AlertCard components — one per alert.
//
// Think of it like this:
//   useSocket  →  gives us the alerts array
//   .map()     →  loops through and makes one AlertCard per alert
// ─────────────────────────────────────────────

export default function AlertFeed() {
  // Destructure what we need from our custom hook.
  // alerts = array of alert objects (grows as new ones come in)
  // connected = boolean (is socket connected?)
  const { alerts, connected } = useSocket();

  // This function is passed DOWN to each AlertCard.
  // When a card is acknowledged, it can tell this parent component.
  // Right now we just log it, but you could filter it out of the list here.
  function handleAcknowledge(id) {
    console.log("Alert acknowledged:", id);
  }

  return (
    <div className="h-full flex flex-col">

      {/* HEADER ROW */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-white font-bold text-lg tracking-tight">
          Live Alerts
        </h2>

        {/* Connection status indicator */}
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-400 animate-pulse" : "bg-red-500"}`}/>
          <span className={`text-xs font-mono ${connected ? "text-emerald-400" : "text-red-400"}`}>
            {connected ? "LIVE" : "DISCONNECTED"}
          </span>
        </div>
      </div>

      {/* ALERT COUNT */}
      <p className="text-slate-400 text-xs mb-4 font-mono">
        {alerts.length} alert{alerts.length !== 1 ? "s" : ""} this session
      </p>

      {/* ALERT LIST */}
      {/* This section scrolls independently so the header stays visible */}
      <div className="flex-1 overflow-y-auto pr-1 space-y-1">

        {/* If no alerts yet, show a placeholder message */}
        {alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-slate-600">
            <span className="text-4xl mb-3">📡</span>
            <p className="text-sm font-mono">Monitoring cameras...</p>
            <p className="text-xs mt-1">Alerts will appear here in real time</p>
          </div>
        ) : (
          // .map() loops through the alerts array.
          // For each alert object, it creates one AlertCard component.
          // "key" is required by React to track each item in the list.
          alerts.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              onAcknowledge={handleAcknowledge}
            />
          ))
        )}
      </div>
    </div>
  );
}
