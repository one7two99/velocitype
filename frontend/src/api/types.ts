// Types mirroring the backend Pydantic schemas.

export type SessionMode = "adaptive" | "fixed_text" | "custom" | "coach_drill";

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

export interface NgramRow {
  ngram: string;
  cls: string | null; // BigramClass value (SFB / ROLL_IN / …)
  attempts: number;
  errors: number;
  error_rate: number;
  avg_latency_ms: number | null;
  wpm: number | null;
  consistency: number | null;
  hitch_rate: number | null;
  latency_n: number;
}

export interface NgramTable {
  layout_id: string;
  ngrams: NgramRow[];
}

export interface WeakBigram {
  bigram: string;
  class: string | null;
  err_pct: number;
  wpm?: number;
  consistency?: number;
  hitch_pct?: number;
}

export interface TrigramRollup {
  redirect_pct: number;
  sfb_chain_pct: number;
  worst_redirect: string | null;
  worst_sfb_chain: string | null;
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
  provider: string;
  reachable: boolean;
  model: string;
  model_ready: boolean;
}

export type AiProvider = "ollama" | "mistral";

export interface AiConfig {
  provider: AiProvider;
  ollama_model: string;
  mistral_model: string;
  mistral_key_set: boolean;
  ollama_default: string;
  mistral_default: string;
}

export interface AiConfigUpdate {
  provider?: AiProvider;
  ollama_model?: string;
  mistral_model?: string;
  // null = leave unchanged, "" = clear, non-empty = set
  mistral_api_key?: string | null;
}

export interface ModelList {
  provider: string;
  models: string[];
  installed: string[];
  reachable: boolean;
}

export interface PullStatus {
  name: string;
  status: string;
  completed: boolean;
  percent: number | null;
  error: string | null;
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
  source: string; // provider name ("ollama" | "mistral") or "fallback"
}

export interface PromptSet {
  analysis_system: string;
  analysis_user: string;
  drill_system: string;
  drill_user: string;
}
export interface PromptCustom {
  analysis_system: string | null;
  analysis_user: string | null;
  drill_system: string | null;
  drill_user: string | null;
}
export interface CoachPrompts {
  defaults: PromptSet;
  custom: PromptCustom;
}
export type PromptKey = keyof PromptSet;

export interface CoachMetrics {
  user: string;
  generated_at: string;
  layout: string;
  lifetime: {
    sessions: number;
    total_time_minutes: number;
    best_wpm: number | null;
    avg_wpm_30d: number | null;
    avg_accuracy_30d: number | null;
  };
  weak_keys: { char: string; error_rate: number; avg_latency_ms: number | null }[];
  trend_7d: { wpm: number[]; accuracy: number[] };
  coach_prompt: string;
  weak_bigrams?: WeakBigram[];
  trigram_rollup?: TrigramRollup | null;
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
