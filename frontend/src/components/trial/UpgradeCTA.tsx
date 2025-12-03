import React from 'react';

interface UpgradeCTAProps {
  size?: 'small' | 'medium' | 'large';
  variant?: 'primary' | 'secondary';
  className?: string;
}

export const UpgradeCTA: React.FC<UpgradeCTAProps> = ({
  size = 'medium',
  variant = 'primary',
  className = '',
}) => {
  // AWS Marketplace URL - update this with the actual Cloud Optimizer listing URL
  const AWS_MARKETPLACE_URL =
    'https://aws.amazon.com/marketplace/pp/prodview-cloudoptimizer';

  const handleUpgradeClick = () => {
    window.open(AWS_MARKETPLACE_URL, '_blank', 'noopener,noreferrer');
  };

  const getSizeClasses = () => {
    switch (size) {
      case 'small':
        return 'px-3 py-1.5 text-xs';
      case 'large':
        return 'px-6 py-3 text-base';
      case 'medium':
      default:
        return 'px-4 py-2 text-sm';
    }
  };

  const getVariantClasses = () => {
    if (variant === 'secondary') {
      return 'bg-white text-blue-600 border-2 border-blue-600 hover:bg-blue-50';
    }
    return 'bg-blue-600 text-white hover:bg-blue-700 border-2 border-transparent';
  };

  return (
    <button
      onClick={handleUpgradeClick}
      className={`inline-flex items-center font-semibold rounded-md transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${getSizeClasses()} ${getVariantClasses()} ${className}`}
    >
      <svg
        className={`-ml-0.5 mr-2 ${size === 'small' ? 'h-3 w-3' : size === 'large' ? 'h-5 w-5' : 'h-4 w-4'}`}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M13 10V3L4 14h7v7l9-11h-7z"
        />
      </svg>
      Upgrade to Pro
      <svg
        className={`ml-1.5 ${size === 'small' ? 'h-3 w-3' : size === 'large' ? 'h-4 w-4' : 'h-3.5 w-3.5'}`}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
        />
      </svg>
    </button>
  );
};

export default UpgradeCTA;
