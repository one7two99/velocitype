import { api } from "./client";
import type {
  ApiKeyCreated,
  ApiKeyInfo,
  KeyHeatmap,
  KeystrokeIn,
  LayoutList,
  NextLessonResponse,
  SessionCompleteResponse,
  SessionHistory,
  SessionMode,
  SessionStartResponse,
  StatsOverview,
  User,
} from "./types";

export const authApi = {
  register: (username: string, email: string, password: string) =>
    api.post<User>("/api/auth/register", { username, email, password }),
  login: (username: string, password: string) =>
    api.post<User>("/api/auth/login", { username, password }),
  logout: () => api.post<{ detail: string }>("/api/auth/logout"),
  refresh: () => api.post<{ detail: string }>("/api/auth/refresh"),
  me: () => api.get<User>("/api/auth/me"),
};

export const sessionsApi = {
  start: (params: {
    layout_id: string;
    mode: SessionMode;
    duration_s?: number | null;
    word_count?: number | null;
    custom_text?: string | null;
  }) => api.post<SessionStartResponse>("/api/sessions/start", params),
  keystrokes: (sessionId: string, keystrokes: KeystrokeIn[]) =>
    api.post<{ saved: number; keys_updated: number }>(
      `/api/sessions/${sessionId}/keystrokes`,
      { keystrokes },
    ),
  complete: (
    sessionId: string,
    metrics: {
      wpm_raw: number;
      wpm_net: number;
      accuracy: number;
      consistency: number;
      duration_s?: number | null;
    },
  ) =>
    api.post<SessionCompleteResponse>(
      `/api/sessions/${sessionId}/complete`,
      metrics,
    ),
  history: (page = 1, pageSize = 10) =>
    api.get<SessionHistory>(
      `/api/sessions?page=${page}&page_size=${pageSize}`,
    ),
};

export const statsApi = {
  overview: (layoutId: string) =>
    api.get<StatsOverview>(`/api/stats/overview?layout_id=${layoutId}`),
  keys: (layoutId: string) =>
    api.get<KeyHeatmap>(`/api/stats/keys?layout_id=${layoutId}`),
};

export const lessonsApi = {
  next: (layoutId: string) =>
    api.get<NextLessonResponse>(`/api/lessons/next?layout_id=${layoutId}`),
  layouts: () => api.get<LayoutList>("/api/lessons/layouts"),
};

export const mcpApi = {
  listKeys: () => api.get<{ keys: ApiKeyInfo[] }>("/api/mcp/keys"),
  createKey: (name: string) =>
    api.post<ApiKeyCreated>("/api/mcp/keys", { name }),
  revokeKey: (id: string) => api.del<void>(`/api/mcp/keys/${id}`),
};
