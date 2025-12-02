import apiClient from './client';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface User {
  user_id: string;
  username: string;
  email: string;
  created_at: string;
  trial_status?: TrialStatus;
}

export interface TrialStatus {
  is_trial: boolean;
  trial_start_date: string | null;
  trial_end_date: string | null;
  days_remaining: number | null;
  queries_used: number;
  queries_limit: number;
}

export const authApi = {
  login: async (data: LoginRequest): Promise<AuthResponse> => {
    const formData = new URLSearchParams();
    formData.append('username', data.username);
    formData.append('password', data.password);

    const response = await apiClient.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  },

  register: async (data: RegisterRequest): Promise<AuthResponse> => {
    const response = await apiClient.post('/auth/register', data);
    return response.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },

  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout');
  },
};
