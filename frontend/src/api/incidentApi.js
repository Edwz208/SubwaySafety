import axios from "axios";

// ─────────────────────────────────────────────
// Base URL of your FastAPI backend.
// Dev:  http://localhost:8000
// Prod: your Vultr server IP or Tailscale IP
// ─────────────────────────────────────────────
const BASE_URL = "http://localhost:8000";

const api = axios.create({
  baseURL: BASE_URL,
});

// ─────────────────────────────────────────────
// FUNCTION 1: getIncidents
// Fetches past events from the backend.
// Route: GET /api/events
// Used by: IncidentLog.jsx
// ─────────────────────────────────────────────
export async function getIncidents() {
  const response = await api.get("/api/events");
  return response.data;
}

// ─────────────────────────────────────────────
// FUNCTION 2: getIncidentById
// Fetches one specific event by its ID.
// Route: GET /api/events/{id}
// Used by: IncidentLog detail view
// ─────────────────────────────────────────────
export async function getIncidentById(id) {
  const response = await api.get(`/api/events/${id}`);
  return response.data;
}

// ─────────────────────────────────────────────
// FUNCTION 3: acknowledgeAlert
// Marks an alert as handled by staff.
// Route: PATCH /api/events/{id}/acknowledge
// Used by: AlertCard.jsx acknowledge button
// ─────────────────────────────────────────────
export async function acknowledgeAlert(incidentId) {
  const response = await api.patch(`/api/events/${incidentId}/acknowledge`);
  return response.data;
}

// ─────────────────────────────────────────────
// FUNCTION 4: getHeatmapData
// Fetches incident counts per location for the heatmap.
// Route: GET /api/events/heatmap/summary
// Used by: HeatmapWidget.jsx
// ─────────────────────────────────────────────
export async function getHeatmapData() {
  const response = await api.get("/api/events/heatmap/summary");
  return response.data;
}
