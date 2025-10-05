import { create } from 'zustand';

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

export const useMapStore = create<MapState>((set) => ({
  selectedLGAs: [],
  viewport: {
    latitude: -33.8688,
    longitude: 151.2093,
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
}));
