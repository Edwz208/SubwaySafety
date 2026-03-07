import { useEffect, useState } from "react";
import { io } from "socket.io-client";

// This is the URL of your Node.js Socket.io server (websocket-server/index.js).
// It runs on port 3001 separately from FastAPI.
const SOCKET_URL = "http://localhost:3001";

// ─────────────────────────────────────────────
// WHAT IS A CUSTOM HOOK?
// In React, a "hook" is a function that starts with "use".
// It lets components share logic without copy-pasting code.
// This hook handles the entire Socket.io connection in one place.
// Any component that calls useSocket() gets live alert data automatically.
// ─────────────────────────────────────────────

export function useSocket() {
  // useState creates a variable that React watches.
  // When it changes, React re-renders the component automatically.
  // Here we store the array of live alerts that come in via socket.
  const [alerts, setAlerts] = useState([]);

  // connected tracks whether the socket is currently connected.
  const [connected, setConnected] = useState(false);

  // useEffect runs code AFTER the component appears on screen.
  // The empty array [] at the end means "only run this once on mount".
  useEffect(() => {
    // Create a socket connection to the server.
    const socket = io(SOCKET_URL);

    // "connect" fires when the connection is established.
    socket.on("connect", () => {
      setConnected(true);
      console.log("Socket connected:", socket.id);
    });

    // "disconnect" fires when the connection drops.
    socket.on("disconnect", () => {
      setConnected(false);
      console.log("Socket disconnected");
    });

    // ─────────────────────────────────────────────
    // THIS IS THE KEY EVENT.
    // Your backend (alert_service.py) emits "new_alert" whenever
    // a camera detects something. Here we listen for that event.
    //
    // newAlert looks like:
    // {
    //   id: 42,
    //   camera_id: "CAM-03",
    //   location: "Platform 2",
    //   severity: "HIGH",
    //   summary: "Person lying on ground for 45 seconds...",
    //   snapshot_url: "http://...",
    //   timestamp: "2025-03-06T14:32:00Z"
    // }
    // ─────────────────────────────────────────────
    socket.on("new_alert", (newAlert) => {
      // prev is the current array of alerts.
      // We add the new alert to the FRONT of the array (newest first).
      setAlerts((prev) => [newAlert, ...prev]);
    });

    // CLEANUP: When the component using this hook is removed from screen,
    // React runs this return function. It disconnects the socket cleanly.
    return () => {
      socket.disconnect();
    };
  }, []); // [] = run only once

  // Return these values so any component can use them.
  return { alerts, connected };
}
