import React from 'react';
import { TrialUsage } from '../../api/trial';

interface UsageMetersProps {
  usage: TrialUsage;
}

interface UsageMeterProps {
  label: string;
  current: number;
  limit: number;
  icon: React.ReactNode;
}

const UsageMeter: React.FC<UsageMeterProps> = ({ label, current, limit, icon }) => {
  const percentage = limit > 0 ? (current / limit) * 100 : 0;
  const isNearLimit = percentage >= 80;
  const isAtLimit = percentage >= 100;

  // Determine progress bar color based on usage
  const getProgressColor = () => {
    if (isAtLimit) return 'bg-red-500';
    if (isNearLimit) return 'bg-yellow-500';
    return 'bg-blue-500';
  };

  const getTextColor = () => {
    if (isAtLimit) return 'text-red-700';
    if (isNearLimit) return 'text-yellow-700';
    return 'text-gray-700';
  };

  return (
    <div className="flex-1 min-w-0">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center space-x-1.5">
          <span className="text-gray-500">{icon}</span>
          <span className="text-xs font-medium text-gray-600">{label}</span>
        </div>
        <span className={`text-xs font-semibold ${getTextColor()}`}>
          {current} / {limit}
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
        <div
          className={`h-full ${getProgressColor()} transition-all duration-300 ease-in-out`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
          role="progressbar"
          aria-valuenow={current}
          aria-valuemin={0}
          aria-valuemax={limit}
          aria-label={`${label}: ${current} of ${limit} used`}
        ></div>
      </div>
      {isAtLimit && (
        <p className="text-xs text-red-600 mt-0.5">Limit reached</p>
      )}
      {isNearLimit && !isAtLimit && (
        <p className="text-xs text-yellow-600 mt-0.5">Approaching limit</p>
      )}
    </div>
  );
};

export const UsageMeters: React.FC<UsageMetersProps> = ({ usage }) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <UsageMeter
        label="Security Scans"
        current={usage.scans.current}
        limit={usage.scans.limit}
        icon={
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
            />
          </svg>
        }
      />
      <UsageMeter
        label="Chat Questions"
        current={usage.questions.current}
        limit={usage.questions.limit}
        icon={
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
            />
          </svg>
        }
      />
      <UsageMeter
        label="Documents"
        current={usage.documents.current}
        limit={usage.documents.limit}
        icon={
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        }
      />
    </div>
  );
};
