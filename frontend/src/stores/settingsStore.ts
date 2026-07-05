import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ThemePref = "dark" | "light" | "system";
export type SessionGoal = "time" | "words";

interface SettingsState {
  theme: ThemePref;
  layoutId: string;
  goal: SessionGoal;
  durationS: number; // 15 | 30 | 60 | 120
  wordCount: number; // 10 | 25 | 50 | 100
  targetWpm: number; // keybr-style target speed keys are measured against
  progressiveUnlock: boolean;
  unlockThresholdPct: number; // % of target WPM a key must reach to progress
  unlockWindowSessions: number; // consecutive qualifying sessions to master a key
  setTheme: (t: ThemePref) => void;
  setLayoutId: (id: string) => void;
  setGoal: (g: SessionGoal) => void;
  setDurationS: (d: number) => void;
  setWordCount: (w: number) => void;
  setTargetWpm: (t: number) => void;
  setProgressiveUnlock: (v: boolean) => void;
  setUnlockThresholdPct: (v: number) => void;
  setUnlockWindowSessions: (v: number) => void;
}

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      theme: "system",
      layoutId: "ferris_sweep_colemak_dh",
      goal: "time",
      durationS: 60,
      wordCount: 25,
      targetWpm: 40,
      progressiveUnlock: true,
      unlockThresholdPct: 90,
      unlockWindowSessions: 3,
      setTheme: (theme) => set({ theme }),
      setLayoutId: (layoutId) => set({ layoutId }),
      setGoal: (goal) => set({ goal }),
      setDurationS: (durationS) => set({ durationS }),
      setWordCount: (wordCount) => set({ wordCount }),
      setTargetWpm: (targetWpm) => set({ targetWpm }),
      setProgressiveUnlock: (progressiveUnlock) => set({ progressiveUnlock }),
      setUnlockThresholdPct: (unlockThresholdPct) => set({ unlockThresholdPct }),
      setUnlockWindowSessions: (unlockWindowSessions) => set({ unlockWindowSessions }),
    }),
    { name: "velocitype-settings" },
  ),
);

/** Apply the theme preference to <html data-theme>. */
export function applyTheme(theme: ThemePref) {
  const root = document.documentElement;
  if (theme === "system") {
    root.removeAttribute("data-theme");
  } else {
    root.setAttribute("data-theme", theme);
  }
}
