import apiClient from './client';

export interface UsageInfo {
  current: number;
  limit: number;
  remaining: number;
}

export interface TrialUsage {
  scans: UsageInfo;
  questions: UsageInfo;
  documents: UsageInfo;
}

export interface TrialStatus {
  trial_id: string;
  status: string;
  is_active: boolean;
  started_at: string;
  expires_at: string;
  days_remaining: number;
  extended: boolean;
  can_extend: boolean;
  converted: boolean;
  usage: TrialUsage;
}

export interface ExtendTrialResponse {
  trial_id: string;
  expires_at: string;
  extended_at: string;
  message: string;
}

export const trialApi = {
  getStatus: async (): Promise<TrialStatus> => {
    const response = await apiClient.get('/trial/status');
    return response.data;
  },

  extendTrial: async (): Promise<ExtendTrialResponse> => {
    const response = await apiClient.post('/trial/extend');
    return response.data;
  },
};
