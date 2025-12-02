import { create } from 'zustand';
import { trialApi, TrialStatus } from '../api/trial';

interface TrialState {
  trialStatus: TrialStatus | null;
  isLoading: boolean;
  error: string | null;
  lastFetched: number | null;
  fetchTrialStatus: () => Promise<void>;
  extendTrial: () => Promise<void>;
  clearError: () => void;
  shouldRefetch: () => boolean;
}

const REFETCH_INTERVAL = 5 * 60 * 1000; // 5 minutes in milliseconds

export const useTrial = create<TrialState>((set, get) => ({
  trialStatus: null,
  isLoading: false,
  error: null,
  lastFetched: null,

  fetchTrialStatus: async () => {
    set({ isLoading: true, error: null });
    try {
      const status = await trialApi.getStatus();
      set({
        trialStatus: status,
        isLoading: false,
        error: null,
        lastFetched: Date.now(),
      });
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to fetch trial status';
      set({
        isLoading: false,
        error: errorMessage,
      });
    }
  },

  extendTrial: async () => {
    set({ isLoading: true, error: null });
    try {
      await trialApi.extendTrial();
      // Refetch trial status after extending
      await get().fetchTrialStatus();
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to extend trial';
      set({
        isLoading: false,
        error: errorMessage,
      });
      throw err;
    }
  },

  clearError: () => set({ error: null }),

  shouldRefetch: () => {
    const { lastFetched } = get();
    if (!lastFetched) return true;
    return Date.now() - lastFetched > REFETCH_INTERVAL;
  },
}));
