import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:4000";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// Attach auth token from cookie/session on every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("socialos_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-handle errors (auth bypass active — no redirect on 401)
api.interceptors.response.use(
  (res) => res,
  (err) => Promise.reject(err)
);

// ── Brand API ────────────────────────────────────
export const brandAPI = {
  list: () => api.get("/api/brands"),
  get: (id: string) => api.get(`/api/brands/${id}`),
  create: (data: unknown) => api.post("/api/brands", data),
  update: (id: string, data: unknown) => api.put(`/api/brands/${id}`, data),
  delete: (id: string) => api.delete(`/api/brands/${id}`),
  relearn: (id: string) => api.post(`/api/brands/${id}/relearn`),
  learningLogs: (id: string) => api.get(`/api/brands/${id}/learning-logs`),
};

// ── Agent API ────────────────────────────────────
export const agentAPI = {
  run: (brandId: string, params: Record<string, unknown>) => api.post(`/api/agents/run`, { brandId, ...params }),
  status: (runId: string) => api.get(`/api/agents/runs/${runId}`),
  listRuns: (brandId: string) => api.get(`/api/agents/runs?brandId=${brandId}`),
  stopRun: (runId: string) => api.post(`/api/agents/runs/${runId}/stop`),
};

// ── Analytics API ────────────────────────────────
export const analyticsAPI = {
  latest: (brandId: string) => api.get(`/api/analytics/${brandId}/latest`),
  history: (brandId: string) => api.get(`/api/analytics/${brandId}/history`),
};

// ── Instagram API ────────────────────────────────
export const instagramAPI = {
  getPosts: (brandId: string) => api.get(`/api/instagram/posts/${brandId}`),
  updateStatus: (postId: string, status: string) =>
    api.put(`/api/instagram/posts/${postId}/status`, { status }),
  publish: (data: { postId: string; brandId: string; imageUrl: string; caption: string }) =>
    api.post("/api/instagram/publish", data),
  publishCaption: (data: { postId: string; brandId: string; caption: string; imageUrl?: string }) =>
    api.post("/api/instagram/publish-caption", data),
  insights: (brandId: string) => api.get(`/api/instagram/insights/${brandId}`),
  schedule: (data: { postId: string; brandId: string; imageUrl: string; caption: string; scheduledAt: string }) =>
    api.post("/api/instagram/schedule", data),
  cancelSchedule: (postId: string) => api.delete(`/api/instagram/schedule/${postId}`),
  getScheduled: (brandId: string) => api.get(`/api/instagram/scheduled/${brandId}`),
  metaStatus: (brandId: string) => api.get(`/api/meta/status/${brandId}`),
  getAuthUrl: (brandId: string) => api.get(`/api/meta/auth-url?brandId=${brandId}`),
  disconnect: (brandId: string) => api.post("/api/meta/disconnect", { brandId }),
};

// ── SSE helper ───────────────────────────────────
export function createSSEConnection(
  runId: string,
  onEvent: (event: unknown) => void,
  onError?: (err: Event) => void
): EventSource {
  // Note: EventSource can't send Authorization headers.
  // The backend has BYPASS_AUTH=true in production so no credentials needed.
  // withCredentials: false allows Access-Control-Allow-Origin: * to work correctly.
  const es = new EventSource(`${API_BASE}/api/agents/runs/${runId}/stream`);
  es.onmessage = (e) => {
    try {
      onEvent(JSON.parse(e.data));
    } catch {}
  };
  if (onError) es.onerror = onError;
  return es;
}
