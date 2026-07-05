import { create } from "zustand";

// Coach-drill mode: while active, the Trainer generates a fresh LLM drill
// (targeting the current weak keys) for every session, until switched back to
// adaptive.
interface CoachState {
  drillActive: boolean;
  setDrillActive: (active: boolean) => void;
}

export const useCoachStore = create<CoachState>((set) => ({
  drillActive: false,
  setDrillActive: (drillActive) => set({ drillActive }),
}));
