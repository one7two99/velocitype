import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";
import { coachApi, sessionsApi } from "../api/endpoints";
import type { WeakKeyInfo } from "../api/types";
import { ResultsPanel } from "../components/ResultsPanel";
import { TypingSession } from "../components/TypingEngine/TypingSession";
import { Alert, Spinner } from "../components/ui";
import type { EngineResult } from "../hooks/useTypingEngine";
import { useCoachStore } from "../stores/coachStore";
import { useSettings } from "../stores/settingsStore";
import "./trainer.css";

type Phase = "loading" | "typing" | "results" | "error";

export function TrainerPage() {
  const { layoutId, goal, durationS, wordCount, targetWpm } = useSettings();
  const drillActive = useCoachStore((s) => s.drillActive);
  const setDrillActive = useCoachStore((s) => s.setDrillActive);

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

  // Prefetched next coach drill (drill mode). Generation is slow on CPU, so we
  // fetch the next one in the background while the current session is typed.
  const nextDrillRef = useRef<Promise<string> | null>(null);

  const startSession = useCallback(
    async (opts?: { reuseLesson?: string }) => {
      setPhase("loading");
      setResult(null);
      setSaveError(null);
      try {
        let resp;
        let text: string;
        if (opts?.reuseLesson) {
          text = opts.reuseLesson;
          resp = await sessionsApi.start({
            layout_id: layoutId,
            mode: "custom",
            custom_text: text,
          });
        } else if (drillActive) {
          // Use the prefetched drill if ready, otherwise fetch a fresh one.
          let drill = "";
          const pending = nextDrillRef.current;
          nextDrillRef.current = null;
          if (pending) {
            try {
              drill = await pending;
            } catch {
              drill = "";
            }
          }
          if (!drill) drill = (await coachApi.drill(layoutId)).lesson;
          text = drill;
          resp = await sessionsApi.start({
            layout_id: layoutId,
            mode: "custom",
            custom_text: drill,
          });
          // Kick off generation of the next drill for a smooth "Next Lesson".
          nextDrillRef.current = coachApi.drill(layoutId).then((r) => r.lesson);
        } else {
          resp = await sessionsApi.start({
            layout_id: layoutId,
            mode: "adaptive",
            duration_s: goal === "time" ? durationS : null,
            word_count: goal === "words" ? wordCount : null,
            target_wpm: targetWpm,
          });
          text = resp.lesson;
        }
        setSessionId(resp.session_id);
        setLesson(text);
        setStartWeak(resp.weak_keys);
        setRunId((n) => n + 1);
        setPhase("typing");
      } catch (err) {
        setLoadError(err instanceof ApiError ? err.message : "Failed to start session.");
        setPhase("error");
      }
    },
    [layoutId, goal, durationS, wordCount, targetWpm, drillActive],
  );

  // (Re)start when layout/goal/target change or when drill mode is toggled.
  useEffect(() => {
    startSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layoutId, goal, durationS, wordCount, targetWpm, drillActive]);

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
          target_wpm: targetWpm,
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
    [sessionId, startWeak, targetWpm],
  );

  if (phase === "loading") {
    return (
      <div className="tf-center">
        <div className="tf-loading">
          <Spinner />
          {drillActive && (
            <p className="tf-loading-hint">
              Preparing your coach drill — local generation can take a minute…
            </p>
          )}
        </div>
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

  // Coach drills complete on text (no timer); adaptive timed mode keeps its clock.
  const durationMs = !drillActive && goal === "time" ? durationS * 1000 : undefined;

  return (
    <>
      {drillActive && (
        <div className="tf-drill-banner">
          <span>🎯 Coach drills — targeting your weak keys</span>
          <button
            className="tf-drill-banner-btn"
            onClick={() => setDrillActive(false)}
          >
            Switch to adaptive
          </button>
        </div>
      )}
      <TypingSession
        key={runId}
        lesson={lesson}
        onComplete={handleComplete}
        durationMs={durationMs}
      />
      {phase === "results" && result && (
        <ResultsPanel
          result={result}
          weakKeys={serverWeak}
          saving={saving}
          saveError={saveError}
          onNext={() => startSession()}
          onRetry={() => startSession({ reuseLesson: lesson })}
        />
      )}
    </>
  );
}
