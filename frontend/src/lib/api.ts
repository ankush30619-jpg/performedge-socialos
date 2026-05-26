import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:4000";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// Attach auth token from localStorage on every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("socialos_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Auto-login on 401 ─────────────────────────────────────────────────────────
// If the backend returns 401 (token missing / expired), silently fetch a bypass
// token from /api/auth/bypass-token (only works when BYPASS_AUTH=true on backend),
// store it, and retry the original request once.
let _autoLoginInProgress = false;
let _autoLoginPromise: Promise<string | null> | null = null;

async function fetchBypassToken(): Promise<string | null> {
  try {
    const res = await axios.get(`${API_BASE}/api/auth/bypass-token`);
    const token = res.data?.token as string | undefined;
    if (token) {
      localStorage.setItem("socialos_token", token);
      return token;
    }
  } catch { /* bypass not enabled on backend — ignore */ }
  return null;
}

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const status = err?.response?.status;
    const originalReq = err?.config;

    // Only auto-retry once on 401, and only for non-auth-endpoint requests
    if (
      status === 401 &&
      !originalReq?._retried &&
      typeof window !== "undefined" &&
      !originalReq?.url?.includes("/api/auth/")
    ) {
      originalReq._retried = true;

      // Deduplicate: if multiple requests 401 at once, only fetch token once
      if (!_autoLoginPromise) {
        _autoLoginPromise = fetchBypassToken().finally(() => { _autoLoginPromise = null; });
      }
      const token = await _autoLoginPromise;

      if (token) {
        originalReq.headers = { ...originalReq.headers, Authorization: `Bearer ${token}` };
        return axios(originalReq);
      }
    }

    return Promise.reject(err);
  }
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
