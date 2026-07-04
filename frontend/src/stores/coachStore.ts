import { create } from "zustand";

// Hands an LLM-generated drill from the Coach page to the Trainer, which starts
// a custom session with it and then clears it.
interface CoachState {
  pendingDrill: string | null;
  setPendingDrill: (text: string | null) => void;
}

export const useCoachStore = create<CoachState>((set) => ({
  pendingDrill: null,
  setPendingDrill: (pendingDrill) => set({ pendingDrill }),
}));
