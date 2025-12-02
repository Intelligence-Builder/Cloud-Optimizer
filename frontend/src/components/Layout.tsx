import React, { useState } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import clsx from 'clsx';

export const Layout: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const trialStatus = user?.trial_status;
  const isTrialActive = trialStatus?.is_trial && (trialStatus?.days_remaining ?? 0) > 0;
  const isTrialExpired = trialStatus?.is_trial && (trialStatus?.days_remaining ?? 0) <= 0;

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <svg
                className="w-5 h-5 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"
                />
              </svg>
            </div>
            <h1 className="text-xl font-bold text-gray-900">Cloud Optimizer</h1>
          </div>

          {/* Trial Status & User Menu */}
          <div className="flex items-center space-x-4">
            {/* Trial Status Badge */}
            {isTrialActive && (
              <div className="px-3 py-1 bg-primary-50 border border-primary-200 rounded-lg">
                <span className="text-sm font-medium text-primary-700">
                  Trial: {trialStatus.days_remaining} days left
                </span>
              </div>
            )}
            {isTrialExpired && (
              <div className="px-3 py-1 bg-red-50 border border-red-200 rounded-lg">
                <span className="text-sm font-medium text-red-700">Trial Expired</span>
              </div>
            )}
            {trialStatus && (
              <div className="px-3 py-1 bg-gray-50 border border-gray-200 rounded-lg">
                <span className="text-sm text-gray-600">
                  {trialStatus.queries_used}/{trialStatus.queries_limit} queries
                </span>
              </div>
            )}

            {/* User Menu */}
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
                  <span className="text-sm font-semibold text-white">
                    {user?.username.charAt(0).toUpperCase()}
                  </span>
                </div>
                <span className="text-sm font-medium text-gray-700">{user?.username}</span>
                <svg
                  className={clsx(
                    'w-4 h-4 text-gray-500 transition-transform',
                    showUserMenu && 'rotate-180'
                  )}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>

              {/* Dropdown Menu */}
              {showUserMenu && (
                <>
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setShowUserMenu(false)}
                  />
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-20">
                    <div className="px-4 py-2 border-b border-gray-100">
                      <p className="text-xs text-gray-500">Signed in as</p>
                      <p className="text-sm font-medium text-gray-900">{user?.email}</p>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                    >
                      Sign out
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
};
