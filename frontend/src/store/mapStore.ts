import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface MapState {
  selectedLGAs: string[];
  viewport: {
    latitude: number;
    longitude: number;
    zoom: number;
  };

  addLGA: (lga: string) => void;
  removeLGA: (lga: string) => void;
  clearLGAs: () => void;
  setViewport: (viewport: Partial<MapState['viewport']>) => void;
}

export const useMapStore = create<MapState>()(
  persist(
    (set) => ({
      selectedLGAs: [],
      viewport: {
        latitude: -34.9285,
        longitude: 138.6007,
        zoom: 10,
      },

      addLGA: (lga) => set((state) => ({
        selectedLGAs: [...state.selectedLGAs, lga],
      })),
      removeLGA: (lga) => set((state) => ({
        selectedLGAs: state.selectedLGAs.filter((l) => l !== lga),
      })),
      clearLGAs: () => set({ selectedLGAs: [] }),
      setViewport: (viewport) => set((state) => ({
        viewport: { ...state.viewport, ...viewport },
      })),
    }),
    {
      name: 'map-storage', // localStorage key
      partialize: (state) => ({
        selectedLGAs: state.selectedLGAs,
        viewport: state.viewport,
      }),
    }
  )
);
