import apiClient from './client';

// Request types
export interface ConnectWithRoleRequest {
  role_arn: string;
  aws_account_id?: string;
  external_id?: string;
  friendly_name?: string;
  region?: string;
}

export interface ConnectWithKeysRequest {
  access_key_id: string;
  secret_access_key: string;
  aws_account_id?: string;
  friendly_name?: string;
  region?: string;
}

// Response types
export interface AWSAccount {
  account_id: string;
  aws_account_id: string;
  friendly_name: string | null;
  connection_type: 'role' | 'keys';
  status: 'connected' | 'pending' | 'error';
  default_region: string;
  last_validated_at: string | null;
  last_error: string | null;
  updated_at: string;
}

export interface SetupInstructions {
  iam_policy: Record<string, unknown>;
  trust_policy: Record<string, unknown>;
}

export const awsAccountsApi = {
  /**
   * List all AWS accounts for the current user
   */
  listAccounts: async (): Promise<AWSAccount[]> => {
    const response = await apiClient.get('/aws-accounts/');
    return response.data;
  },

  /**
   * Get a specific AWS account by ID
   */
  getAccount: async (accountId: string): Promise<AWSAccount> => {
    const response = await apiClient.get(`/aws-accounts/${accountId}`);
    return response.data;
  },

  /**
   * Connect AWS account using IAM role assumption
   */
  connectWithRole: async (request: ConnectWithRoleRequest): Promise<AWSAccount> => {
    const response = await apiClient.post('/aws-accounts/connect/role', request);
    return response.data;
  },

  /**
   * Connect AWS account using IAM access keys
   */
  connectWithKeys: async (request: ConnectWithKeysRequest): Promise<AWSAccount> => {
    const response = await apiClient.post('/aws-accounts/connect/keys', request);
    return response.data;
  },

  /**
   * Revalidate an existing AWS account connection
   */
  validateAccount: async (accountId: string): Promise<AWSAccount> => {
    const response = await apiClient.post(`/aws-accounts/${accountId}/validate`);
    return response.data;
  },

  /**
   * Disconnect an AWS account
   */
  disconnectAccount: async (accountId: string): Promise<void> => {
    await apiClient.delete(`/aws-accounts/${accountId}`);
  },

  /**
   * Get IAM policy and trust policy templates for setup
   */
  getSetupInstructions: async (): Promise<SetupInstructions> => {
    const response = await apiClient.get('/aws-accounts/setup-instructions');
    return response.data;
  },
};
