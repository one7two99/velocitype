// Types mirroring the backend Pydantic schemas.

export type SessionMode = "adaptive" | "fixed_text" | "custom";

export interface User {
  id: string;
  username: string;
  email: string;
  created_at: string;
  last_login: string | null;
  is_active: boolean;
}

export interface WeakKeyInfo {
  char: string;
  error_rate: number;
  avg_latency_ms: number | null;
}

export interface SessionStartResponse {
  session_id: string;
  layout_id: string;
  mode: SessionMode;
  lesson: string;
  weak_keys: WeakKeyInfo[];
}

export interface KeystrokeIn {
  ts_offset_ms: number;
  expected_char: string;
  actual_char: string;
  correct: boolean;
  hold_ms: number | null;
}

export interface SessionMetrics {
  wpm_raw: number | null;
  wpm_net: number | null;
  accuracy: number | null;
  consistency: number | null;
}

export interface SessionCompleteResponse {
  session_id: string;
  metrics: SessionMetrics;
  weak_keys: WeakKeyInfo[];
}

export interface SessionSummary {
  id: string;
  layout_id: string;
  mode: string;
  duration_s: number | null;
  word_count: number | null;
  started_at: string;
  completed_at: string | null;
  wpm_raw: number | null;
  wpm_net: number | null;
  accuracy: number | null;
  consistency: number | null;
}

export interface SessionHistory {
  items: SessionSummary[];
  page: number;
  page_size: number;
  total: number;
}

export interface TrendPoint {
  date: string;
  wpm: number | null;
  accuracy: number | null;
}

export interface TopError {
  char: string;
  error_rate: number;
  errors: number;
  attempts: number;
}

export interface StatsOverview {
  layout_id: string;
  total_sessions: number;
  total_time_minutes: number;
  best_wpm: number | null;
  avg_wpm_30d: number | null;
  avg_accuracy_30d: number | null;
  best_accuracy: number | null;
  best_consistency: number | null;
  wpm_trend: TrendPoint[];
  accuracy_trend: TrendPoint[];
  top_errors: TopError[];
}

export interface KeyHeatCell {
  character: string;
  hand: string | null;
  finger: string | null;
  attempts: number;
  errors: number;
  error_rate: number;
  avg_latency_ms: number | null;
  consistency: number | null;
}

export interface KeyHeatmap {
  layout_id: string;
  keys: KeyHeatCell[];
}

export interface NextLessonResponse {
  layout_id: string;
  lesson: string;
  weak_keys: WeakKeyInfo[];
  word_count: number;
}

export interface LayoutInfo {
  id: string;
  name: string;
  hand_map: Record<string, string>;
  finger_map: Record<string, string>;
  thumb_keys: string[];
}

export interface LayoutList {
  layouts: LayoutInfo[];
}

export interface ApiKeyInfo {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface ApiKeyCreated {
  id: string;
  name: string;
  prefix: string;
  api_key: string;
}

export interface CoachStatus {
  reachable: boolean;
  model: string;
  model_ready: boolean;
}

export interface CoachAnalysis {
  layout_id: string;
  model: string;
  generated_at: string;
  analysis: string;
}

export interface CoachDrill {
  layout_id: string;
  model: string;
  generated_at: string;
  lesson: string;
  word_count: number;
  weak_keys: WeakKeyInfo[];
  source: "ollama" | "fallback";
}

// RFC 7807 problem+json
export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance?: string;
  errors?: { loc: (string | number)[]; msg: string; type: string }[];
}
