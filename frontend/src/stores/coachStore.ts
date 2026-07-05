import { create } from "zustand";

// Coach-drill mode: while active, the Trainer generates a fresh LLM drill for
// every session, until switched back to adaptive. When focusKeys is non-empty the
// drills target exactly those keys (picked in the Analysis table); otherwise the
// adaptive engine picks the current weakest keys automatically.
interface CoachState {
  drillActive: boolean;
  focusKeys: string[];
  setDrillActive: (active: boolean) => void;
  setFocusKeys: (keys: string[]) => void;
  startDrills: (focusKeys: string[]) => void;
  stopDrills: () => void;
}

export const useCoachStore = create<CoachState>((set) => ({
  drillActive: false,
  focusKeys: [],
  setDrillActive: (drillActive) => set({ drillActive }),
  setFocusKeys: (focusKeys) => set({ focusKeys }),
  startDrills: (focusKeys) => set({ drillActive: true, focusKeys }),
  stopDrills: () => set({ drillActive: false, focusKeys: [] }),
}));
