import { useQueryClient } from "@tanstack/react-query";
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
  const focusKeys = useCoachStore((s) => s.focusKeys);
  const focusBigrams = useCoachStore((s) => s.focusBigrams);
  const stopDrills = useCoachStore((s) => s.stopDrills);
  const qc = useQueryClient();

  const [phase, setPhase] = useState<Phase>("loading");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [lesson, setLesson] = useState("");
  const [runId, setRunId] = useState(0);
  const [startWeak, setStartWeak] = useState<WeakKeyInfo[]>([]);
  const [result, setResult] = useState<EngineResult | null>(null);
  const [serverWeak, setServerWeak] = useState<WeakKeyInfo[]>([]);
  const [unlockedChar, setUnlockedChar] = useState<string | null>(null);
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
            // Retrying a coach drill stays tagged as a coach drill.
            mode: drillActive ? "coach_drill" : "custom",
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
          if (!drill) drill = (await coachApi.drill(layoutId, focusKeys, focusBigrams)).lesson;
          text = drill;
          resp = await sessionsApi.start({
            layout_id: layoutId,
            mode: "coach_drill",
            custom_text: drill,
          });
          // Note: the next drill is prefetched in handleComplete (after this
          // session's metrics are saved) so it reflects the latest performance.
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
    [layoutId, goal, durationS, wordCount, targetWpm, drillActive, focusKeys, focusBigrams],
  );

  // (Re)start when layout/goal/target change or when drill mode / focus changes.
  useEffect(() => {
    // Focus changed → discard any drill prefetched for the old focus.
    nextDrillRef.current = null;
    startSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layoutId, goal, durationS, wordCount, targetWpm, drillActive, focusKeys, focusBigrams]);

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
        setUnlockedChar(resp.unlocked_char ?? null);
        // Session is saved → refresh dashboard/analysis data (stats + history).
        qc.invalidateQueries({ queryKey: ["stats"] });
        qc.invalidateQueries({ queryKey: ["sessions"] });
        if (resp.unlocked_char) qc.invalidateQueries({ queryKey: ["lessons", "unlock"] });
        // Now that THIS session's metrics are persisted, prefetch the next coach
        // drill so it reflects the just-finished performance (not a stale snapshot).
        if (drillActive) {
          nextDrillRef.current = coachApi
            .drill(layoutId, focusKeys, focusBigrams)
            .then((d) => d.lesson);
        }
      } catch (err) {
        setSaveError(
          err instanceof ApiError ? err.message : "Failed to save session.",
        );
      } finally {
        setSaving(false);
      }
    },
    [sessionId, startWeak, targetWpm, qc, drillActive, layoutId, focusKeys, focusBigrams],
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
          <span>
            🎯 Coach drills —{" "}
            {focusBigrams.length
              ? `targeting pairs: ${focusBigrams.join(" ")}`
              : focusKeys.length
                ? `targeting: ${focusKeys.map((k) => (k === " " ? "␣" : k)).join(" ")}`
                : "targeting your weak keys"}
          </span>
          <button className="tf-drill-banner-btn" onClick={() => stopDrills()}>
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
          unlockedChar={unlockedChar}
          onNext={() => startSession()}
          onRetry={() => startSession({ reuseLesson: lesson })}
        />
      )}
    </>
  );
}
