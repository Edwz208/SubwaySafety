import { useEffect, useState } from "react";

// ─────────────────────────────────────────────
// IMPORTANT CHANGE FROM ORIGINAL:
// Your backend uses FastAPI's native WebSocket at ws://localhost:8000/alert
// NOT a separate Socket.io server on port 3001.
//
// Native WebSocket = built into every browser, no library needed.
// You can remove socket.io-client from package.json entirely.
//
// ws:// = WebSocket protocol (same idea as http://)
// The path /alert matches @router.websocket("/alert") in routers/alert.py
// ─────────────────────────────────────────────
const WS_URL = "ws://localhost:8000/alert";

export function useSocket() {
  const [alerts, setAlerts] = useState([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    // Create native browser WebSocket connection
    const ws = new WebSocket(WS_URL);

    // Fires when connection is successfully opened
    ws.onopen = () => {
      setConnected(true);
      console.log("[useSocket] Connected to FastAPI WebSocket");
    };

    // Fires when connection is closed (backend restart, network drop etc.)
    ws.onclose = () => {
      setConnected(false);
      console.log("[useSocket] WebSocket disconnected");
    };

    // ── THIS IS THE KEY HANDLER ──
    // Fires every time FastAPI calls manager.broadcast() in alert.py
    // event.data is the JSON string your backend sends via send_alert()
    // We parse it and prepend it to the alerts array (newest first)
    ws.onmessage = (event) => {
      try {
        const newAlert = JSON.parse(event.data);
        setAlerts((prev) => [newAlert, ...prev]);
      } catch (e) {
        console.error("[useSocket] Failed to parse alert:", e);
      }
    };

    // Fires if the connection errors out
    ws.onerror = (error) => {
      console.error("[useSocket] WebSocket error:", error);
      setConnected(false);
    };

    // Cleanup: close the WebSocket when the component unmounts
    // This prevents memory leaks and dangling connections
    return () => {
      ws.close();
    };
  }, []); // [] = run once on mount only

  return { alerts, connected };
}
