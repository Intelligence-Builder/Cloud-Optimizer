import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authApi, User, LoginRequest, RegisterRequest } from '../api/auth';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  clearError: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (data: LoginRequest) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authApi.login(data);
          localStorage.setItem('auth_token', response.access_token);
          set({
            user: response.user,
            token: response.access_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (err) {
          const errorMessage = err instanceof Error ? err.message : 'Login failed';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw err;
        }
      },

      register: async (data: RegisterRequest) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authApi.register(data);
          localStorage.setItem('auth_token', response.access_token);
          set({
            user: response.user,
            token: response.access_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (err) {
          const errorMessage = err instanceof Error ? err.message : 'Registration failed';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw err;
        }
      },

      logout: async () => {
        try {
          await authApi.logout();
        } catch (err) {
          console.error('Logout error:', err);
        } finally {
          localStorage.removeItem('auth_token');
          set({
            user: null,
            token: null,
            isAuthenticated: false,
            error: null,
          });
        }
      },

      refreshUser: async () => {
        const token = localStorage.getItem('auth_token');
        if (!token) {
          set({ user: null, token: null, isAuthenticated: false });
          return;
        }

        try {
          const user = await authApi.getCurrentUser();
          set({
            user,
            token,
            isAuthenticated: true,
          });
        } catch (err) {
          localStorage.removeItem('auth_token');
          set({
            user: null,
            token: null,
            isAuthenticated: false,
          });
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
