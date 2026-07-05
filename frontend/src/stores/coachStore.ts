import { create } from "zustand";

// Coach-drill mode: while active, the Trainer generates a fresh LLM drill for
// every session, until switched back to adaptive. Focus is either specific keys
// (from the per-key Analysis) OR specific bigrams (from the bigram breakdown);
// with neither, the adaptive engine picks the current weakest keys automatically.
interface CoachState {
  drillActive: boolean;
  focusKeys: string[];
  focusBigrams: string[];
  setDrillActive: (active: boolean) => void;
  setFocusKeys: (keys: string[]) => void;
  startDrills: (focusKeys: string[]) => void;
  startBigramDrills: (focusBigrams: string[]) => void;
  stopDrills: () => void;
}

export const useCoachStore = create<CoachState>((set) => ({
  drillActive: false,
  focusKeys: [],
  focusBigrams: [],
  setDrillActive: (drillActive) => set({ drillActive }),
  setFocusKeys: (focusKeys) => set({ focusKeys }),
  startDrills: (focusKeys) => set({ drillActive: true, focusKeys, focusBigrams: [] }),
  startBigramDrills: (focusBigrams) =>
    set({ drillActive: true, focusBigrams, focusKeys: [] }),
  stopDrills: () => set({ drillActive: false, focusKeys: [], focusBigrams: [] }),
}));
