import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api/client";
import { sessionsApi } from "../api/endpoints";
import type { WeakKeyInfo } from "../api/types";
import { ResultsPanel } from "../components/ResultsPanel";
import { TypingSession } from "../components/TypingEngine/TypingSession";
import { Alert, Spinner } from "../components/ui";
import type { EngineResult } from "../hooks/useTypingEngine";
import { useSettings } from "../stores/settingsStore";

type Phase = "loading" | "typing" | "results" | "error";

export function TrainerPage() {
  const { layoutId, goal, durationS, wordCount } = useSettings();

  const [phase, setPhase] = useState<Phase>("loading");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [lesson, setLesson] = useState("");
  const [runId, setRunId] = useState(0);
  const [startWeak, setStartWeak] = useState<WeakKeyInfo[]>([]);
  const [result, setResult] = useState<EngineResult | null>(null);
  const [serverWeak, setServerWeak] = useState<WeakKeyInfo[]>([]);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const startSession = useCallback(
    async (reuseLesson?: string) => {
      setPhase("loading");
      setResult(null);
      setSaveError(null);
      try {
        const resp = await sessionsApi.start({
          layout_id: layoutId,
          mode: "adaptive",
          duration_s: goal === "time" ? durationS : null,
          word_count: goal === "words" ? wordCount : null,
        });
        setSessionId(resp.session_id);
        setLesson(reuseLesson ?? resp.lesson);
        setStartWeak(resp.weak_keys);
        setRunId((n) => n + 1);
        setPhase("typing");
      } catch (err) {
        setLoadError(err instanceof ApiError ? err.message : "Failed to start session.");
        setPhase("error");
      }
    },
    [layoutId, goal, durationS, wordCount],
  );

  // Start the first session on mount and whenever layout/goal changes.
  useEffect(() => {
    startSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layoutId, goal, durationS, wordCount]);

  const handleComplete = useCallback(
    async (r: EngineResult) => {
      setResult(r);
      setServerWeak(startWeak);
      setPhase("results");
      if (!sessionId) return;
      setSaving(true);
      setSaveError(null);
      try {
        if (r.keystrokes.length > 0) {
          await sessionsApi.keystrokes(sessionId, r.keystrokes);
        }
        const resp = await sessionsApi.complete(sessionId, {
          wpm_raw: r.wpmRaw,
          wpm_net: r.wpmNet,
          accuracy: r.accuracy,
          consistency: r.consistency,
          duration_s: r.durationS,
        });
        setServerWeak(resp.weak_keys);
      } catch (err) {
        setSaveError(
          err instanceof ApiError ? err.message : "Failed to save session.",
        );
      } finally {
        setSaving(false);
      }
    },
    [sessionId, startWeak],
  );

  if (phase === "loading") {
    return (
      <div className="tf-center">
        <Spinner />
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div style={{ maxWidth: 480, margin: "3rem auto" }}>
        <Alert>{loadError}</Alert>
        <button className="tf-btn tf-btn--primary" onClick={() => startSession()}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <>
      <TypingSession
        key={runId}
        lesson={lesson}
        onComplete={handleComplete}
        durationMs={goal === "time" ? durationS * 1000 : undefined}
      />
      {phase === "results" && result && (
        <ResultsPanel
          result={result}
          weakKeys={serverWeak}
          saving={saving}
          saveError={saveError}
          onNext={() => startSession()}
          onRetry={() => startSession(lesson)}
        />
      )}
    </>
  );
}
