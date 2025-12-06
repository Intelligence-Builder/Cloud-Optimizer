import { useEffect, useState } from 'react';
import { useAWSAccounts } from '../../hooks/useAWSAccounts';
import { AWSAccount } from '../../api/awsAccounts';

type ConnectionMethod = 'role' | 'keys' | null;
type WizardStep = 'select' | 'configure' | 'review';

interface FormData {
  // Role connection
  roleArn: string;
  externalId: string;
  // Keys connection
  accessKeyId: string;
  secretAccessKey: string;
  // Common
  awsAccountId: string;
  friendlyName: string;
  region: string;
}

const initialFormData: FormData = {
  roleArn: '',
  externalId: '',
  accessKeyId: '',
  secretAccessKey: '',
  awsAccountId: '',
  friendlyName: '',
  region: 'us-east-1',
};

const AWS_REGIONS = [
  'us-east-1',
  'us-east-2',
  'us-west-1',
  'us-west-2',
  'eu-west-1',
  'eu-west-2',
  'eu-central-1',
  'ap-southeast-1',
  'ap-southeast-2',
  'ap-northeast-1',
];

export function AWSAccountConnection() {
  const {
    accounts,
    isLoading,
    isConnecting,
    error,
    fetchAccounts,
    fetchSetupInstructions,
    connectWithRole,
    connectWithKeys,
    validateAccount,
    disconnectAccount,
    setupInstructions,
    clearError,
    shouldRefetch,
  } = useAWSAccounts();

  const [showWizard, setShowWizard] = useState(false);
  const [wizardStep, setWizardStep] = useState<WizardStep>('select');
  const [connectionMethod, setConnectionMethod] = useState<ConnectionMethod>(null);
  const [formData, setFormData] = useState<FormData>(initialFormData);
  const [showInstructions, setShowInstructions] = useState(false);
  const [confirmDisconnect, setConfirmDisconnect] = useState<string | null>(null);

  useEffect(() => {
    if (shouldRefetch()) {
      fetchAccounts();
    }
  }, [fetchAccounts, shouldRefetch]);

  const resetWizard = () => {
    setShowWizard(false);
    setWizardStep('select');
    setConnectionMethod(null);
    setFormData(initialFormData);
    clearError();
  };

  const handleSelectMethod = (method: ConnectionMethod) => {
    setConnectionMethod(method);
    setWizardStep('configure');
    if (method === 'role') {
      fetchSetupInstructions();
    }
  };

  const handleFormChange = (field: keyof FormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleConnect = async () => {
    try {
      if (connectionMethod === 'role') {
        await connectWithRole({
          role_arn: formData.roleArn,
          external_id: formData.externalId || undefined,
          aws_account_id: formData.awsAccountId || undefined,
          friendly_name: formData.friendlyName || undefined,
          region: formData.region,
        });
      } else if (connectionMethod === 'keys') {
        await connectWithKeys({
          access_key_id: formData.accessKeyId,
          secret_access_key: formData.secretAccessKey,
          aws_account_id: formData.awsAccountId || undefined,
          friendly_name: formData.friendlyName || undefined,
          region: formData.region,
        });
      }
      resetWizard();
    } catch {
      // Error is handled by the store
    }
  };

  const handleDisconnect = async (accountId: string) => {
    try {
      await disconnectAccount(accountId);
      setConfirmDisconnect(null);
    } catch {
      // Error is handled by the store
    }
  };

  const handleValidate = async (accountId: string) => {
    try {
      await validateAccount(accountId);
    } catch {
      // Error is handled by the store
    }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      connected: 'bg-green-100 text-green-800 border-green-200',
      pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      error: 'bg-red-100 text-red-800 border-red-200',
    };
    return styles[status] || styles.pending;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">AWS Accounts</h2>
          <p className="text-sm text-gray-500 mt-1">
            Connect your AWS accounts to enable security scanning and optimization
          </p>
        </div>
        <button
          onClick={() => setShowWizard(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          Connect Account
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start justify-between">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-red-500 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <p className="text-red-800">{error}</p>
          </div>
          <button onClick={clearError} className="text-red-500 hover:text-red-700">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      )}

      {/* Account List */}
      {isLoading && accounts.length === 0 ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-500">Loading accounts...</p>
        </div>
      ) : accounts.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
          <svg className="w-12 h-12 text-gray-400 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <h3 className="mt-4 text-lg font-medium text-gray-900">No AWS accounts connected</h3>
          <p className="mt-2 text-gray-500">Connect your first AWS account to get started</p>
          <button
            onClick={() => setShowWizard(true)}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Connect Account
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {accounts.map((account: AWSAccount) => (
            <AccountCard
              key={account.account_id}
              account={account}
              onValidate={() => handleValidate(account.account_id)}
              onDisconnect={() => setConfirmDisconnect(account.account_id)}
              isLoading={isLoading}
              statusBadge={getStatusBadge(account.status)}
            />
          ))}
        </div>
      )}

      {/* Connection Wizard Modal */}
      {showWizard && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                {wizardStep === 'select' && 'Choose Connection Method'}
                {wizardStep === 'configure' && `Configure ${connectionMethod === 'role' ? 'IAM Role' : 'Access Keys'}`}
                {wizardStep === 'review' && 'Review & Connect'}
              </h3>
              <button onClick={resetWizard} className="text-gray-400 hover:text-gray-600">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6">
              {/* Step 1: Select Method */}
              {wizardStep === 'select' && (
                <div className="space-y-4">
                  <button
                    onClick={() => handleSelectMethod('role')}
                    className="w-full p-4 border border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors text-left"
                  >
                    <div className="flex items-start">
                      <div className="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                        <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                        </svg>
                      </div>
                      <div className="ml-4">
                        <h4 className="font-medium text-gray-900">IAM Role (Recommended)</h4>
                        <p className="text-sm text-gray-500 mt-1">
                          Cross-account role assumption. More secure, no credentials stored.
                        </p>
                      </div>
                    </div>
                  </button>

                  <button
                    onClick={() => handleSelectMethod('keys')}
                    className="w-full p-4 border border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors text-left"
                  >
                    <div className="flex items-start">
                      <div className="flex-shrink-0 w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                        <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                        </svg>
                      </div>
                      <div className="ml-4">
                        <h4 className="font-medium text-gray-900">Access Keys</h4>
                        <p className="text-sm text-gray-500 mt-1">
                          IAM user credentials. Simpler setup, credentials encrypted at rest.
                        </p>
                      </div>
                    </div>
                  </button>
                </div>
              )}

              {/* Step 2: Configure */}
              {wizardStep === 'configure' && (
                <div className="space-y-4">
                  {connectionMethod === 'role' && (
                    <>
                      {/* Instructions Toggle */}
                      <button
                        onClick={() => setShowInstructions(!showInstructions)}
                        className="w-full text-left text-sm text-blue-600 hover:text-blue-700 flex items-center"
                      >
                        <svg className={`w-4 h-4 mr-1 transition-transform ${showInstructions ? 'rotate-90' : ''}`} fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                        </svg>
                        View setup instructions
                      </button>

                      {showInstructions && setupInstructions && (
                        <div className="bg-gray-50 rounded-lg p-4 text-sm space-y-3">
                          <p className="font-medium text-gray-700">1. Create an IAM role in your AWS account</p>
                          <p className="font-medium text-gray-700">2. Attach this policy to the role:</p>
                          <pre className="bg-gray-800 text-green-400 p-3 rounded text-xs overflow-x-auto">
                            {JSON.stringify(setupInstructions.iam_policy, null, 2)}
                          </pre>
                          <p className="font-medium text-gray-700">3. Set this trust policy:</p>
                          <pre className="bg-gray-800 text-green-400 p-3 rounded text-xs overflow-x-auto">
                            {JSON.stringify(setupInstructions.trust_policy, null, 2)}
                          </pre>
                        </div>
                      )}

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Role ARN <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={formData.roleArn}
                          onChange={(e) => handleFormChange('roleArn', e.target.value)}
                          placeholder="arn:aws:iam::123456789012:role/CloudOptimizerRole"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          External ID (optional)
                        </label>
                        <input
                          type="text"
                          value={formData.externalId}
                          onChange={(e) => handleFormChange('externalId', e.target.value)}
                          placeholder="Your external ID for additional security"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                    </>
                  )}

                  {connectionMethod === 'keys' && (
                    <>
                      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800">
                        <strong>Note:</strong> For production use, we recommend IAM role assumption instead of access keys.
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Access Key ID <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={formData.accessKeyId}
                          onChange={(e) => handleFormChange('accessKeyId', e.target.value)}
                          placeholder="AKIAIOSFODNN7EXAMPLE"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Secret Access Key <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="password"
                          value={formData.secretAccessKey}
                          onChange={(e) => handleFormChange('secretAccessKey', e.target.value)}
                          placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                    </>
                  )}

                  {/* Common Fields */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Friendly Name (optional)
                    </label>
                    <input
                      type="text"
                      value={formData.friendlyName}
                      onChange={(e) => handleFormChange('friendlyName', e.target.value)}
                      placeholder="e.g., Production, Development"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Default Region
                    </label>
                    <select
                      value={formData.region}
                      onChange={(e) => handleFormChange('region', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      {AWS_REGIONS.map((region) => (
                        <option key={region} value={region}>{region}</option>
                      ))}
                    </select>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
              {wizardStep === 'select' ? (
                <button
                  onClick={resetWizard}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800"
                >
                  Cancel
                </button>
              ) : (
                <button
                  onClick={() => setWizardStep('select')}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800"
                >
                  Back
                </button>
              )}

              {wizardStep === 'configure' && (
                <button
                  onClick={handleConnect}
                  disabled={isConnecting || (connectionMethod === 'role' && !formData.roleArn) || (connectionMethod === 'keys' && (!formData.accessKeyId || !formData.secretAccessKey))}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                >
                  {isConnecting ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Connecting...
                    </>
                  ) : (
                    'Connect Account'
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Disconnect Confirmation Modal */}
      {confirmDisconnect && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Disconnect AWS Account?</h3>
            <p className="text-gray-600 mb-6">
              This will remove the connection and stop all scanning for this account.
              This action cannot be undone.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setConfirmDisconnect(null)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDisconnect(confirmDisconnect)}
                disabled={isLoading}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                {isLoading ? 'Disconnecting...' : 'Disconnect'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Account Card Component
interface AccountCardProps {
  account: AWSAccount;
  onValidate: () => void;
  onDisconnect: () => void;
  isLoading: boolean;
  statusBadge: string;
}

function AccountCard({ account, onValidate, onDisconnect, isLoading, statusBadge }: AccountCardProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex items-start">
          <div className="flex-shrink-0 w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
            <svg className="w-6 h-6 text-orange-600" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2L2 7v10l10 5 10-5V7L12 2zm0 2.18l6.9 3.45L12 11.09 5.1 7.63 12 4.18zM4 8.82l7 3.5v6.36l-7-3.5V8.82zm9 9.86v-6.36l7-3.5v6.36l-7 3.5z"/>
            </svg>
          </div>
          <div className="ml-4">
            <h4 className="font-medium text-gray-900">
              {account.friendly_name || `AWS Account ${account.aws_account_id}`}
            </h4>
            <p className="text-sm text-gray-500">
              {account.aws_account_id} &middot; {account.default_region}
            </p>
            <div className="flex items-center mt-2 space-x-2">
              <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${statusBadge}`}>
                {account.status}
              </span>
              <span className="text-xs text-gray-400">
                via {account.connection_type === 'role' ? 'IAM Role' : 'Access Keys'}
              </span>
            </div>
            {account.last_error && (
              <p className="text-sm text-red-600 mt-2">{account.last_error}</p>
            )}
          </div>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={onValidate}
            disabled={isLoading}
            className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50"
            title="Revalidate connection"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
          <button
            onClick={onDisconnect}
            disabled={isLoading}
            className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
            title="Disconnect account"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

export default AWSAccountConnection;
