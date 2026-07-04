import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KeystrokeIn } from "../api/types";

export type EngineStatus = "idle" | "running" | "complete";

export interface EngineResult {
  wpmRaw: number;
  wpmNet: number;
  accuracy: number; // 0..1
  consistency: number; // 0..1
  durationS: number;
  keystrokes: KeystrokeIn[];
  wpmSamples: number[]; // per-second gross wpm, for the results sparkline
}

export interface TypingView {
  words: string[];
  typed: string[]; // typed text per word
  wordIndex: number;
  charIndex: number;
  errors: Set<string>; // "w:c"
  status: EngineStatus;
  shakeKey: string | null;
  liveWpm: number;
  liveAccuracy: number; // 0..1
  elapsedMs: number;
  result: EngineResult | null;
  restart: () => void;
}

interface InternalState {
  wordIndex: number;
  charIndex: number;
  typed: string[];
  errors: Set<string>;
  status: EngineStatus;
  shakeKey: string | null;
  result: EngineResult | null;
}

const LIVE_WINDOW_MS = 10_000; // rolling window for live WPM (keybr approach)
const LIVE_TICK_MS = 500;

function initial(words: string[]): InternalState {
  return {
    wordIndex: 0,
    charIndex: 0,
    typed: words.map(() => ""),
    errors: new Set(),
    status: "idle",
    shakeKey: null,
    result: null,
  };
}

function computeMetrics(
  keystrokes: KeystrokeIn[],
  errorWordCount: number,
  startMs: number,
  endMs: number,
): EngineResult {
  const durationS = Math.max(0.001, (endMs - startMs) / 1000);
  const minutes = durationS / 60;
  const correctChars = keystrokes.filter((k) => k.correct).length;
  const totalChars = keystrokes.length;

  const wpmRaw = correctChars / 5 / minutes;
  const wpmNet = Math.max(0, wpmRaw - errorWordCount / minutes);
  const accuracy = totalChars > 0 ? correctChars / totalChars : 1;

  // Per-second gross WPM samples → consistency via coefficient of variation.
  const bins = new Map<number, number>();
  for (const k of keystrokes) {
    if (!k.correct) continue;
    const sec = Math.floor(k.ts_offset_ms / 1000);
    bins.set(sec, (bins.get(sec) ?? 0) + 1);
  }
  const wpmSamples: number[] = [];
  const lastSec = Math.max(0, Math.floor((endMs - startMs) / 1000));
  for (let s = 0; s <= lastSec; s++) {
    const chars = bins.get(s) ?? 0;
    wpmSamples.push((chars / 5) * 60);
  }
  let consistency = 1;
  const active = wpmSamples.filter((_, i) => i < lastSec || wpmSamples.length === 1);
  if (active.length > 1) {
    const mean = active.reduce((a, b) => a + b, 0) / active.length;
    if (mean > 0) {
      const variance =
        active.reduce((a, b) => a + (b - mean) ** 2, 0) / active.length;
      const cv = Math.sqrt(variance) / mean;
      consistency = Math.min(1, Math.max(0, 1 - cv));
    }
  }

  return {
    wpmRaw: Math.round(wpmRaw * 100) / 100,
    wpmNet: Math.round(wpmNet * 100) / 100,
    accuracy: Math.round(accuracy * 10000) / 10000,
    consistency: Math.round(consistency * 10000) / 10000,
    durationS: Math.round(durationS),
    keystrokes,
    wpmSamples,
  };
}

/**
 * Typing engine (Section 11). Listens on document keydown so split-keyboard
 * layer switches never steal focus. Timing starts on the first keystroke, not on
 * mount. Keystrokes are batched in memory and surfaced only on completion.
 */
export function useTypingEngine(
  lesson: string,
  onComplete?: (r: EngineResult) => void,
): TypingView {
  const words = useMemo(
    () => lesson.trim().split(/\s+/).filter(Boolean),
    [lesson],
  );

  const [state, setState] = useState<InternalState>(() => initial(words));
  const [liveWpm, setLiveWpm] = useState(0);
  const [liveAccuracy, setLiveAccuracy] = useState(1);
  const [elapsedMs, setElapsedMs] = useState(0);

  const startRef = useRef<number | null>(null);
  const keystrokesRef = useRef<KeystrokeIn[]>([]);
  const errorWordsRef = useRef<Set<number>>(new Set());
  const tabArmedRef = useRef(false);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  const restart = useCallback(() => {
    startRef.current = null;
    keystrokesRef.current = [];
    errorWordsRef.current = new Set();
    tabArmedRef.current = false;
    setLiveWpm(0);
    setLiveAccuracy(1);
    setElapsedMs(0);
    setState(initial(words));
  }, [words]);

  // Reset whenever the lesson text changes.
  useEffect(() => {
    restart();
  }, [restart]);

  const finish = useCallback(() => {
    const start = startRef.current ?? Date.now();
    const result = computeMetrics(
      keystrokesRef.current,
      errorWordsRef.current.size,
      start,
      Date.now(),
    );
    setState((s) => ({ ...s, status: "complete", result }));
    onCompleteRef.current?.(result);
  }, []);

  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      // Let real browser/OS shortcuts through.
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const key = e.key;

      // Tab (+Enter) restarts without the mouse (Section 6.1).
      if (key === "Tab") {
        e.preventDefault();
        tabArmedRef.current = true;
        return;
      }
      if (key === "Enter") {
        e.preventDefault();
        if (tabArmedRef.current) restart();
        return;
      }
      tabArmedRef.current = false;

      setState((s) => {
        if (s.status === "complete") return s;

        // Backspace: correct within the current word only.
        if (key === "Backspace") {
          e.preventDefault();
          if (s.charIndex === 0) return s;
          const ci = s.charIndex - 1;
          const typed = [...s.typed];
          typed[s.wordIndex] = typed[s.wordIndex].slice(0, ci);
          const errors = new Set(s.errors);
          errors.delete(`${s.wordIndex}:${ci}`);
          return { ...s, charIndex: ci, typed, errors };
        }

        // Space commits the current word and advances (monkeytype behavior).
        if (key === " ") {
          e.preventDefault();
          if (s.charIndex === 0 && s.typed[s.wordIndex] === "") return s;
          if (s.wordIndex >= words.length - 1) return s;
          return { ...s, wordIndex: s.wordIndex + 1, charIndex: 0 };
        }

        // Only printable single characters from here on.
        if (key.length !== 1) return s;
        e.preventDefault();

        if (startRef.current === null) startRef.current = Date.now();
        const ts = Date.now() - (startRef.current ?? Date.now());

        const word = words[s.wordIndex] ?? "";
        const expected = word[s.charIndex] ?? ""; // "" => extra char (error)
        const correct = key === expected;

        keystrokesRef.current.push({
          ts_offset_ms: ts,
          expected_char: expected || key,
          actual_char: key,
          correct,
          hold_ms: null,
        });

        const errors = new Set(s.errors);
        let shakeKey = s.shakeKey;
        if (!correct) {
          errors.add(`${s.wordIndex}:${s.charIndex}`);
          errorWordsRef.current.add(s.wordIndex);
          shakeKey = `${s.wordIndex}:${s.charIndex}`;
        }

        const typed = [...s.typed];
        typed[s.wordIndex] = typed[s.wordIndex] + key;
        const nextChar = s.charIndex + 1;

        const isLastWord = s.wordIndex === words.length - 1;
        const finishedWord = nextChar >= word.length;
        const complete = isLastWord && finishedWord && word.length > 0;

        const next: InternalState = {
          ...s,
          typed,
          charIndex: nextChar,
          errors,
          shakeKey,
          status: complete ? "complete" : "running",
        };

        if (complete) {
          // Defer metric computation out of the state updater.
          queueMicrotask(finish);
        }
        return next;
      });
    },
    [words, restart, finish],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [handleKey]);

  // Clear the shake marker shortly after it fires so it can re-trigger.
  useEffect(() => {
    if (!state.shakeKey) return;
    const t = setTimeout(
      () => setState((s) => ({ ...s, shakeKey: null })),
      120,
    );
    return () => clearTimeout(t);
  }, [state.shakeKey]);

  // Live WPM (rolling 10s window) + accuracy, ticked every 500ms.
  useEffect(() => {
    if (state.status !== "running") return;
    const id = setInterval(() => {
      const start = startRef.current;
      if (start === null) return;
      const now = Date.now() - start;
      setElapsedMs(now);
      const ks = keystrokesRef.current;
      const windowStart = now - LIVE_WINDOW_MS;
      const recent = ks.filter((k) => k.ts_offset_ms >= windowStart);
      const recentCorrect = recent.filter((k) => k.correct).length;
      const windowMin =
        Math.min(now, LIVE_WINDOW_MS) / 1000 / 60 || 1 / 60;
      setLiveWpm(Math.round(recentCorrect / 5 / windowMin));
      const correct = ks.filter((k) => k.correct).length;
      setLiveAccuracy(ks.length ? correct / ks.length : 1);
    }, LIVE_TICK_MS);
    return () => clearInterval(id);
  }, [state.status]);

  return {
    words,
    typed: state.typed,
    wordIndex: state.wordIndex,
    charIndex: state.charIndex,
    errors: state.errors,
    status: state.status,
    shakeKey: state.shakeKey,
    liveWpm,
    liveAccuracy,
    elapsedMs,
    result: state.result,
    restart,
  };
}
