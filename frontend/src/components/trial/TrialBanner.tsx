import React, { useEffect, useState } from 'react';
import { useTrial } from '../../hooks/useTrial';
import { UsageMeters } from './UsageMeters';
import { UpgradeCTA } from './UpgradeCTA';

export const TrialBanner: React.FC = () => {
  const { trialStatus, isLoading, error, fetchTrialStatus, extendTrial, clearError } =
    useTrial();
  const [isDismissed, setIsDismissed] = useState(false);
  const [isExtending, setIsExtending] = useState(false);

  useEffect(() => {
    fetchTrialStatus();
  }, [fetchTrialStatus]);

  // Don't show banner if dismissed, converted, or no trial data
  if (
    isDismissed ||
    !trialStatus ||
    trialStatus.converted ||
    !trialStatus.is_active
  ) {
    return null;
  }

  const handleDismiss = () => {
    setIsDismissed(true);
  };

  const handleExtend = async () => {
    setIsExtending(true);
    try {
      await extendTrial();
    } catch (err) {
      console.error('Failed to extend trial:', err);
    } finally {
      setIsExtending(false);
    }
  };

  // Determine color scheme based on days remaining
  const getColorScheme = (daysRemaining: number) => {
    if (daysRemaining > 7) {
      return {
        bg: 'bg-green-50',
        border: 'border-green-200',
        text: 'text-green-800',
        accent: 'text-green-600',
        buttonBg: 'bg-green-600 hover:bg-green-700',
        buttonText: 'text-white',
      };
    } else if (daysRemaining >= 3) {
      return {
        bg: 'bg-yellow-50',
        border: 'border-yellow-200',
        text: 'text-yellow-800',
        accent: 'text-yellow-600',
        buttonBg: 'bg-yellow-600 hover:bg-yellow-700',
        buttonText: 'text-white',
      };
    } else {
      return {
        bg: 'bg-red-50',
        border: 'border-red-200',
        text: 'text-red-800',
        accent: 'text-red-600',
        buttonBg: 'bg-red-600 hover:bg-red-700',
        buttonText: 'text-white',
      };
    }
  };

  const colors = getColorScheme(trialStatus.days_remaining);

  if (isLoading && !trialStatus) {
    return (
      <div className="bg-gray-50 border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-center">
          <svg
            className="animate-spin h-5 w-5 text-gray-400"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
          <span className="ml-2 text-sm text-gray-500">Loading trial status...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`${colors.bg} border-b ${colors.border}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            {/* Trial status header */}
            <div className="flex items-center mb-3">
              <div className="flex items-center">
                <svg
                  className={`h-5 w-5 ${colors.accent} mr-2`}
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
                    clipRule="evenodd"
                  />
                </svg>
                <h3 className={`text-sm font-semibold ${colors.text}`}>
                  Trial Account
                </h3>
              </div>
              <span className={`ml-3 text-sm font-medium ${colors.accent}`}>
                {trialStatus.days_remaining} {trialStatus.days_remaining === 1 ? 'day' : 'days'} remaining
              </span>
            </div>

            {/* Usage meters */}
            <div className="mb-3">
              <UsageMeters usage={trialStatus.usage} />
            </div>

            {/* Action buttons */}
            <div className="flex items-center space-x-3">
              <UpgradeCTA size="small" />
              {trialStatus.can_extend && !trialStatus.extended && (
                <button
                  onClick={handleExtend}
                  disabled={isExtending}
                  className={`inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md ${colors.buttonText} ${colors.buttonBg} focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-50 disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {isExtending ? (
                    <>
                      <svg
                        className="animate-spin -ml-0.5 mr-1.5 h-3 w-3"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        ></circle>
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                      </svg>
                      Extending...
                    </>
                  ) : (
                    'Extend Trial'
                  )}
                </button>
              )}
            </div>

            {/* Error message */}
            {error && (
              <div className="mt-2 flex items-center">
                <p className="text-xs text-red-600">{error}</p>
                <button
                  onClick={clearError}
                  className="ml-2 text-xs text-red-500 hover:text-red-700 underline"
                >
                  Dismiss
                </button>
              </div>
            )}
          </div>

          {/* Dismiss button */}
          <button
            onClick={handleDismiss}
            className={`ml-4 inline-flex items-center p-1 rounded-md ${colors.text} hover:bg-white/50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-transparent`}
          >
            <span className="sr-only">Dismiss</span>
            <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};
