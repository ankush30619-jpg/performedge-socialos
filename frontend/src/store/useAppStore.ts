import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Brand, AgentRun, SSEEvent, AppStore } from "@/types";

export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
      activeBrandId: null,
      brands: [],
      activeRun: null,
      sseEvents: [],

      setActiveBrand: (id: string | null) => set({ activeBrandId: id }),
      setBrands: (brands) => set({ brands }),
      setActiveRun: (run) => set({ activeRun: run }),
      addSSEEvent: (event) =>
        set((state) => ({ sseEvents: [...state.sseEvents.slice(-200), event] })),
      clearSSEEvents: () => set({ sseEvents: [] }),
    }),
    {
      name: "socialos-store",
      partialize: (state) => ({
        activeBrandId: state.activeBrandId,
      }),
    }
  )
);

// Selector hooks
export const useActiveBrand = () => {
  const { activeBrandId, brands } = useAppStore();
  return brands.find((b) => b.id === activeBrandId) ?? null;
};
