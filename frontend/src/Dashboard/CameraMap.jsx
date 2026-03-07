import { useSocket } from "../hooks/useSocket";

// ─────────────────────────────────────────────
// CameraMap renders a visual SVG map of the subway station.
// It shows where each camera is positioned and highlights
// any cameras that have active/recent alerts.
//
// We use the useSocket hook here too — so when a new alert
// comes in, the relevant camera dot lights up automatically.
//
// SVG (Scalable Vector Graphics) is built into HTML.
// Think of it like drawing with code:
//   <rect>  = rectangle
//   <circle> = circle/dot
//   <text>  = label
// ─────────────────────────────────────────────

// Static camera positions on the map (x, y are percentages of the SVG size).
// In a real app, these would come from your backend.
const CAMERAS = [
  { id: "CAM-01", label: "Platform 1 - East", x: 120, y: 80  },
  { id: "CAM-02", label: "Platform 1 - West", x: 340, y: 80  },
  { id: "CAM-03", label: "Platform 2 - East", x: 120, y: 160 },
  { id: "CAM-04", label: "Platform 2 - West", x: 340, y: 160 },
  { id: "CAM-05", label: "Entrance Gate",     x: 230, y: 30  },
  { id: "CAM-06", label: "Exit Stairs A",     x: 60,  y: 220 },
  { id: "CAM-07", label: "Exit Stairs B",     x: 400, y: 220 },
];

export default function CameraMap() {
  // Get live alerts from the socket so we know which cameras are active
  const { alerts } = useSocket();

  // Build a Set of camera IDs that have recent unacknowledged alerts.
  // A Set is like an array but with no duplicates and fast lookup.
  const activeCameraIds = new Set(
    alerts
      .filter(a => !a.acknowledged)
      .map(a => a.camera_id)
  );

  return (
    <div>
      {/* HEADER */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-white font-bold text-lg tracking-tight">Station Map</h2>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"/>Normal
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse"/>Alert
          </span>
        </div>
      </div>

      {/* SVG MAP */}
      {/* viewBox defines the coordinate space. Width x Height = 460 x 260 */}
      <svg
        viewBox="0 0 460 260"
        className="w-full rounded-xl border border-slate-700 bg-slate-900"
      >
        {/* BACKGROUND GRID LINES for visual depth */}
        {[0,1,2,3,4].map(i => (
          <line key={`h${i}`} x1="0" y1={i*65} x2="460" y2={i*65}
            stroke="#1e293b" strokeWidth="1"/>
        ))}
        {[0,1,2,3,4,5].map(i => (
          <line key={`v${i}`} x1={i*92} y1="0" x2={i*92} y2="260"
            stroke="#1e293b" strokeWidth="1"/>
        ))}

        {/* PLATFORM 1 */}
        <rect x="60" y="60" width="340" height="40" rx="4"
          fill="#1e3a5f" stroke="#2563eb" strokeWidth="1"/>
        <text x="230" y="85" textAnchor="middle" fill="#93c5fd" fontSize="11" fontFamily="monospace">
          PLATFORM 1
        </text>

        {/* PLATFORM 2 */}
        <rect x="60" y="140" width="340" height="40" rx="4"
          fill="#1e3a5f" stroke="#2563eb" strokeWidth="1"/>
        <text x="230" y="165" textAnchor="middle" fill="#93c5fd" fontSize="11" fontFamily="monospace">
          PLATFORM 2
        </text>

        {/* ENTRANCE */}
        <rect x="190" y="10" width="80" height="28" rx="4"
          fill="#134e4a" stroke="#0d9488" strokeWidth="1"/>
        <text x="230" y="28" textAnchor="middle" fill="#5eead4" fontSize="10" fontFamily="monospace">
          ENTRANCE
        </text>

        {/* EXIT STAIRS */}
        <rect x="30" y="210" width="70" height="28" rx="4"
          fill="#1c1917" stroke="#78716c" strokeWidth="1"/>
        <text x="65" y="228" textAnchor="middle" fill="#a8a29e" fontSize="9" fontFamily="monospace">
          STAIRS A
        </text>
        <rect x="360" y="210" width="70" height="28" rx="4"
          fill="#1c1917" stroke="#78716c" strokeWidth="1"/>
        <text x="395" y="228" textAnchor="middle" fill="#a8a29e" fontSize="9" fontFamily="monospace">
          STAIRS B
        </text>

        {/* CAMERA DOTS */}
        {CAMERAS.map((cam) => {
          const isActive = activeCameraIds.has(cam.id);
          return (
            // <g> is a group — lets us move a set of elements together
            <g key={cam.id}>
              {/* Outer glow ring — only visible when alert is active */}
              {isActive && (
                <circle
                  cx={cam.x} cy={cam.y} r="12"
                  fill="rgba(239,68,68,0.2)"
                  stroke="#ef4444"
                  strokeWidth="1"
                >
                  {/* Animate the glow ring to pulse */}
                  <animate attributeName="r" values="10;16;10" dur="1.5s" repeatCount="indefinite"/>
                  <animate attributeName="opacity" values="0.8;0.2;0.8" dur="1.5s" repeatCount="indefinite"/>
                </circle>
              )}

              {/* Main camera dot */}
              <circle
                cx={cam.x} cy={cam.y} r="6"
                fill={isActive ? "#ef4444" : "#10b981"}
                stroke={isActive ? "#fca5a5" : "#34d399"}
                strokeWidth="1.5"
              />

              {/* Camera ID label */}
              <text
                x={cam.x} y={cam.y + 18}
                textAnchor="middle"
                fill={isActive ? "#fca5a5" : "#64748b"}
                fontSize="8"
                fontFamily="monospace"
              >
                {cam.id}
              </text>
            </g>
          );
        })}
      </svg>

      {/* ACTIVE ALERTS BELOW MAP */}
      {activeCameraIds.size > 0 && (
        <div className="mt-3 space-y-1">
          {[...activeCameraIds].map(id => (
            <div key={id} className="flex items-center gap-2 text-xs text-red-400 font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"/>
              {id} — active alert
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
