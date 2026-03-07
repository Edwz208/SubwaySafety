import axios from "axios";

// This is the base URL of your FastAPI backend.
// When running locally, FastAPI defaults to port 8000.
// Change this to your Vultr server IP when deployed.
const BASE_URL = "http://localhost:8000";

// axios.create() makes a reusable "client" with the base URL pre-set.
// So instead of typing the full URL every time, you just type the path.
const api = axios.create({
  baseURL: BASE_URL,
});

// ─────────────────────────────────────────────
// FUNCTION 1: getIncidents
// Fetches the list of past incidents from your backend.
// The backend route is: GET /incidents
// Returns an array of incident objects.
// ─────────────────────────────────────────────
export async function getIncidents() {
  const response = await api.get("/incidents");
  return response.data; // axios puts the actual data inside .data
}

// ─────────────────────────────────────────────
// FUNCTION 2: getIncidentById
// Fetches one specific incident by its ID.
// The backend route is: GET /incidents/{id}
// ─────────────────────────────────────────────
export async function getIncidentById(id) {
  const response = await api.get(`/incidents/${id}`);
  return response.data;
}

// ─────────────────────────────────────────────
// FUNCTION 3: acknowledgeAlert
// Marks an alert as "seen/handled" by staff.
// The backend route is: POST /alerts/trigger
// Sends the incident ID so the backend knows which one to mark.
// ─────────────────────────────────────────────
export async function acknowledgeAlert(incidentId) {
  const response = await api.post(`/alerts/${incidentId}/acknowledge`);
  return response.data;
}

// ─────────────────────────────────────────────
// FUNCTION 4: getHeatmapData
// Fetches aggregated location risk data for the heatmap widget.
// The backend route is: GET /incidents/heatmap
// ─────────────────────────────────────────────
export async function getHeatmapData() {
  const response = await api.get("/incidents/heatmap");
  return response.data;
}
