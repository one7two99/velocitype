import { api } from "./client";
import type {
  AiConfig,
  AiConfigUpdate,
  ApiKeyCreated,
  ApiKeyInfo,
  CoachAnalysis,
  CoachDrill,
  CoachMetrics,
  CoachPrompts,
  CoachStatus,
  ModelList,
  PromptCustom,
  PullStatus,
  KeyHeatmap,
  KeystrokeIn,
  LayoutList,
  NgramTable,
  NextLessonResponse,
  SessionCompleteResponse,
  SessionHistory,
  SessionMode,
  SessionStartResponse,
  SessionStatSeries,
  StatsOverview,
  UnlockState,
  User,
  UserSettings,
} from "./types";

export const authApi = {
  register: (username: string, email: string, password: string) =>
    api.post<User>("/api/auth/register", { username, email, password }),
  login: (username: string, password: string) =>
    api.post<User>("/api/auth/login", { username, password }),
  logout: () => api.post<{ detail: string }>("/api/auth/logout"),
  refresh: () => api.post<{ detail: string }>("/api/auth/refresh"),
  me: () => api.get<User>("/api/auth/me"),
  changePassword: (current_password: string, new_password: string) =>
    api.patch<{ detail: string }>("/api/auth/password", {
      current_password,
      new_password,
    }),
  changeEmail: (password: string, email: string) =>
    api.patch<User>("/api/auth/email", { password, email }),
  deleteAccount: (password: string) =>
    api.del<void>("/api/auth/me", { password }),
  resetData: (password: string) =>
    api.post<{ detail: string }>("/api/auth/me/reset", { password }),
};

export const sessionsApi = {
  start: (params: {
    layout_id: string;
    mode: SessionMode;
    duration_s?: number | null;
    word_count?: number | null;
    custom_text?: string | null;
    target_wpm?: number | null;
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
      target_wpm?: number | null;
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
  ngrams: (layoutId: string) =>
    api.get<NgramTable>(`/api/stats/ngrams?layout_id=${layoutId}`),
  sessions: (layoutId: string) =>
    api.get<SessionStatSeries>(`/api/stats/sessions?layout_id=${layoutId}`),
};

export const settingsApi = {
  get: () => api.get<UserSettings>("/api/settings"),
  save: (body: Omit<UserSettings, "saved">) =>
    api.put<UserSettings>("/api/settings", body),
};

export const lessonsApi = {
  next: (layoutId: string, targetWpm?: number) =>
    api.get<NextLessonResponse>(
      `/api/lessons/next?layout_id=${layoutId}` +
        (targetWpm ? `&target_wpm=${targetWpm}` : ""),
    ),
  layouts: () => api.get<LayoutList>("/api/lessons/layouts"),
  unlock: (layoutId: string) =>
    api.get<UnlockState>(`/api/lessons/unlock?layout_id=${layoutId}`),
  resetProgression: (layoutId: string) =>
    api.post<UnlockState>(`/api/lessons/unlock/reset?layout_id=${layoutId}`),
};

export const mcpApi = {
  listKeys: () => api.get<{ keys: ApiKeyInfo[] }>("/api/mcp/keys"),
  createKey: (name: string) =>
    api.post<ApiKeyCreated>("/api/mcp/keys", { name }),
  revokeKey: (id: string) => api.del<void>(`/api/mcp/keys/${id}`),
};

export const coachApi = {
  status: () => api.get<CoachStatus>("/api/coach/status"),
  metrics: (layoutId: string) =>
    api.get<CoachMetrics>(`/api/coach/metrics?layout_id=${layoutId}`),
  analyze: (layoutId: string) =>
    api.post<CoachAnalysis>(`/api/coach/analyze?layout_id=${layoutId}`),
  drill: (layoutId: string, focusKeys?: string[], focusBigrams?: string[]) => {
    const body: { focus_keys?: string[]; focus_bigrams?: string[] } = {};
    if (focusBigrams && focusBigrams.length) body.focus_bigrams = focusBigrams;
    else if (focusKeys && focusKeys.length) body.focus_keys = focusKeys;
    return api.post<CoachDrill>(
      `/api/coach/drill?layout_id=${layoutId}`,
      Object.keys(body).length ? body : undefined,
    );
  },
  getPrompts: () => api.get<CoachPrompts>("/api/coach/prompts"),
  savePrompts: (custom: PromptCustom) =>
    api.put<CoachPrompts>("/api/coach/prompts", custom),
  getConfig: () => api.get<AiConfig>("/api/coach/config"),
  saveConfig: (body: AiConfigUpdate) =>
    api.put<AiConfig>("/api/coach/config", body),
  listModels: (provider: string) =>
    api.get<ModelList>(`/api/coach/models?provider=${provider}`),
  pullModel: (name: string) =>
    api.post<PullStatus>("/api/coach/models/pull", { name }),
  pullStatus: (name: string) =>
    api.get<PullStatus>(`/api/coach/models/pull?name=${encodeURIComponent(name)}`),
};
