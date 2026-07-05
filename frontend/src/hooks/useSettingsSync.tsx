import { useEffect, useRef } from "react";
import { settingsApi } from "../api/endpoints";
import { useSettings } from "../stores/settingsStore";
import { useAuth } from "./useAuth";

// Server sync for the settings store. The localStorage-persisted store gives an
// instant local value; when signed in, the server is the cross-browser source of
// truth: we hydrate from it on login and push changes back (debounced).
//
// `applyingRemote` guards the subscriber so hydrating from the server doesn't
// immediately echo back as a save.
let applyingRemote = false;

function toBody(s: ReturnType<typeof useSettings.getState>) {
  return {
    theme: s.theme,
    layout_id: s.layoutId,
    goal: s.goal,
    duration_s: s.durationS,
    word_count: s.wordCount,
    target_wpm: s.targetWpm,
    progressive_unlock: s.progressiveUnlock,
    unlock_threshold_pct: s.unlockThresholdPct,
    unlock_window_sessions: s.unlockWindowSessions,
  };
}

export function useSettingsSync() {
  const { user } = useAuth();
  const hydratedFor = useRef<string | null>(null);

  // Hydrate from (or seed) the server whenever the signed-in user changes.
  useEffect(() => {
    if (!user) {
      hydratedFor.current = null;
      return;
    }
    if (hydratedFor.current === user.id) return;
    let cancelled = false;
    (async () => {
      try {
        const s = await settingsApi.get();
        if (cancelled) return;
        if (s.saved) {
          applyingRemote = true;
          useSettings.setState({
            theme: s.theme,
            layoutId: s.layout_id,
            goal: s.goal,
            durationS: s.duration_s,
            wordCount: s.word_count,
            targetWpm: s.target_wpm,
            progressiveUnlock: s.progressive_unlock,
            unlockThresholdPct: s.unlock_threshold_pct,
            unlockWindowSessions: s.unlock_window_sessions,
          });
        } else {
          // First time on the server → seed it from the current local settings.
          await settingsApi.save(toBody(useSettings.getState()));
        }
        hydratedFor.current = user.id;
      } catch {
        /* offline / unreachable: keep local settings */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user?.id]);

  // Persist local changes to the server (debounced), once hydrated.
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const unsub = useSettings.subscribe((state, prev) => {
      if (applyingRemote) {
        applyingRemote = false;
        return;
      }
      if (!hydratedFor.current) return; // not signed-in / not yet synced
      const changed =
        state.theme !== prev.theme ||
        state.layoutId !== prev.layoutId ||
        state.goal !== prev.goal ||
        state.durationS !== prev.durationS ||
        state.wordCount !== prev.wordCount ||
        state.targetWpm !== prev.targetWpm ||
        state.progressiveUnlock !== prev.progressiveUnlock ||
        state.unlockThresholdPct !== prev.unlockThresholdPct ||
        state.unlockWindowSessions !== prev.unlockWindowSessions;
      if (!changed) return;
      clearTimeout(timer);
      timer = setTimeout(() => {
        settingsApi.save(toBody(useSettings.getState())).catch(() => {});
      }, 400);
    });
    return () => {
      unsub();
      clearTimeout(timer);
    };
  }, []);
}
