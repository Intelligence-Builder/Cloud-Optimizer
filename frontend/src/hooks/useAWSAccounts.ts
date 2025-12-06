import { create } from 'zustand';
import {
  awsAccountsApi,
  AWSAccount,
  ConnectWithRoleRequest,
  ConnectWithKeysRequest,
  SetupInstructions,
} from '../api/awsAccounts';

interface AWSAccountsState {
  accounts: AWSAccount[];
  selectedAccount: AWSAccount | null;
  setupInstructions: SetupInstructions | null;
  isLoading: boolean;
  isConnecting: boolean;
  error: string | null;
  lastFetched: number | null;

  // Actions
  fetchAccounts: () => Promise<void>;
  fetchSetupInstructions: () => Promise<void>;
  connectWithRole: (request: ConnectWithRoleRequest) => Promise<AWSAccount>;
  connectWithKeys: (request: ConnectWithKeysRequest) => Promise<AWSAccount>;
  validateAccount: (accountId: string) => Promise<void>;
  disconnectAccount: (accountId: string) => Promise<void>;
  selectAccount: (account: AWSAccount | null) => void;
  clearError: () => void;
  shouldRefetch: () => boolean;
}

const REFETCH_INTERVAL = 5 * 60 * 1000; // 5 minutes

export const useAWSAccounts = create<AWSAccountsState>((set, get) => ({
  accounts: [],
  selectedAccount: null,
  setupInstructions: null,
  isLoading: false,
  isConnecting: false,
  error: null,
  lastFetched: null,

  fetchAccounts: async () => {
    set({ isLoading: true, error: null });
    try {
      const accounts = await awsAccountsApi.listAccounts();
      set({
        accounts,
        isLoading: false,
        error: null,
        lastFetched: Date.now(),
      });
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to fetch AWS accounts';
      set({
        isLoading: false,
        error: errorMessage,
      });
    }
  },

  fetchSetupInstructions: async () => {
    set({ isLoading: true, error: null });
    try {
      const instructions = await awsAccountsApi.getSetupInstructions();
      set({
        setupInstructions: instructions,
        isLoading: false,
        error: null,
      });
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to fetch setup instructions';
      set({
        isLoading: false,
        error: errorMessage,
      });
    }
  },

  connectWithRole: async (request: ConnectWithRoleRequest) => {
    set({ isConnecting: true, error: null });
    try {
      const account = await awsAccountsApi.connectWithRole(request);
      // Add to accounts list
      set((state) => ({
        accounts: [...state.accounts, account],
        isConnecting: false,
        error: null,
      }));
      return account;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to connect AWS account';
      set({
        isConnecting: false,
        error: errorMessage,
      });
      throw err;
    }
  },

  connectWithKeys: async (request: ConnectWithKeysRequest) => {
    set({ isConnecting: true, error: null });
    try {
      const account = await awsAccountsApi.connectWithKeys(request);
      // Add to accounts list
      set((state) => ({
        accounts: [...state.accounts, account],
        isConnecting: false,
        error: null,
      }));
      return account;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to connect AWS account';
      set({
        isConnecting: false,
        error: errorMessage,
      });
      throw err;
    }
  },

  validateAccount: async (accountId: string) => {
    set({ isLoading: true, error: null });
    try {
      const updatedAccount = await awsAccountsApi.validateAccount(accountId);
      // Update account in list
      set((state) => ({
        accounts: state.accounts.map((a) =>
          a.account_id === accountId ? updatedAccount : a
        ),
        selectedAccount:
          state.selectedAccount?.account_id === accountId
            ? updatedAccount
            : state.selectedAccount,
        isLoading: false,
        error: null,
      }));
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to validate account';
      set({
        isLoading: false,
        error: errorMessage,
      });
      throw err;
    }
  },

  disconnectAccount: async (accountId: string) => {
    set({ isLoading: true, error: null });
    try {
      await awsAccountsApi.disconnectAccount(accountId);
      // Remove from accounts list
      set((state) => ({
        accounts: state.accounts.filter((a) => a.account_id !== accountId),
        selectedAccount:
          state.selectedAccount?.account_id === accountId
            ? null
            : state.selectedAccount,
        isLoading: false,
        error: null,
      }));
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to disconnect account';
      set({
        isLoading: false,
        error: errorMessage,
      });
      throw err;
    }
  },

  selectAccount: (account: AWSAccount | null) => {
    set({ selectedAccount: account });
  },

  clearError: () => set({ error: null }),

  shouldRefetch: () => {
    const { lastFetched } = get();
    if (!lastFetched) return true;
    return Date.now() - lastFetched > REFETCH_INTERVAL;
  },
}));
