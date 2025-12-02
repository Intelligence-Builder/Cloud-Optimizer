import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { TrialBanner } from '../TrialBanner';
import { useTrial } from '../../../hooks/useTrial';

// Mock the useTrial hook
vi.mock('../../../hooks/useTrial', () => ({
  useTrial: vi.fn(),
}));

// Mock child components
vi.mock('../UsageMeters', () => ({
  UsageMeters: ({ usage }: any) => (
    <div data-testid="usage-meters">
      Chats: {usage.chats_used}/{usage.chats_limit}
    </div>
  ),
}));

vi.mock('../UpgradeCTA', () => ({
  UpgradeCTA: ({ size }: any) => (
    <button data-testid="upgrade-cta">Upgrade {size}</button>
  ),
}));

describe('TrialBanner', () => {
  const mockTrialStatus = {
    is_active: true,
    days_remaining: 10,
    converted: false,
    extended: false,
    can_extend: true,
    usage: {
      chats_used: 5,
      chats_limit: 100,
      documents_used: 2,
      documents_limit: 50,
    },
  };

  const mockUseTrial = {
    trialStatus: mockTrialStatus,
    isLoading: false,
    error: null,
    fetchTrialStatus: vi.fn(),
    extendTrial: vi.fn().mockResolvedValue(undefined),
    clearError: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useTrial).mockReturnValue(mockUseTrial);
  });

  describe('Rendering', () => {
    it('renders trial banner with correct information', async () => {
      render(<TrialBanner />);

      await waitFor(() => {
        expect(screen.getByText('Trial Account')).toBeInTheDocument();
        expect(screen.getByText('10 days remaining')).toBeInTheDocument();
      });
    });

    it('fetches trial status on mount', () => {
      render(<TrialBanner />);

      expect(mockUseTrial.fetchTrialStatus).toHaveBeenCalled();
    });

    it('displays usage meters', async () => {
      render(<TrialBanner />);

      await waitFor(() => {
        expect(screen.getByTestId('usage-meters')).toBeInTheDocument();
        expect(screen.getByText(/Chats: 5\/100/)).toBeInTheDocument();
      });
    });

    it('displays upgrade CTA button', async () => {
      render(<TrialBanner />);

      await waitFor(() => {
        expect(screen.getByTestId('upgrade-cta')).toBeInTheDocument();
      });
    });

    it('shows "day" singular when 1 day remaining', async () => {
      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        trialStatus: { ...mockTrialStatus, days_remaining: 1 },
      });

      render(<TrialBanner />);

      await waitFor(() => {
        expect(screen.getByText('1 day remaining')).toBeInTheDocument();
      });
    });

    it('shows "days" plural when multiple days remaining', async () => {
      render(<TrialBanner />);

      await waitFor(() => {
        expect(screen.getByText('10 days remaining')).toBeInTheDocument();
      });
    });
  });

  describe('Color Schemes', () => {
    it('uses green color scheme when > 7 days remaining', async () => {
      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        trialStatus: { ...mockTrialStatus, days_remaining: 10 },
      });

      const { container } = render(<TrialBanner />);

      await waitFor(() => {
        const banner = container.querySelector('.bg-green-50');
        expect(banner).toBeInTheDocument();
      });
    });

    it('uses yellow color scheme when 3-7 days remaining', async () => {
      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        trialStatus: { ...mockTrialStatus, days_remaining: 5 },
      });

      const { container } = render(<TrialBanner />);

      await waitFor(() => {
        const banner = container.querySelector('.bg-yellow-50');
        expect(banner).toBeInTheDocument();
      });
    });

    it('uses red color scheme when < 3 days remaining', async () => {
      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        trialStatus: { ...mockTrialStatus, days_remaining: 2 },
      });

      const { container } = render(<TrialBanner />);

      await waitFor(() => {
        const banner = container.querySelector('.bg-red-50');
        expect(banner).toBeInTheDocument();
      });
    });
  });

  describe('Extend Trial', () => {
    it('shows extend trial button when can_extend is true', async () => {
      render(<TrialBanner />);

      await waitFor(() => {
        expect(screen.getByText('Extend Trial')).toBeInTheDocument();
      });
    });

    it('does not show extend trial button when can_extend is false', async () => {
      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        trialStatus: { ...mockTrialStatus, can_extend: false },
      });

      render(<TrialBanner />);

      await waitFor(() => {
        expect(screen.queryByText('Extend Trial')).not.toBeInTheDocument();
      });
    });

    it('does not show extend trial button when already extended', async () => {
      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        trialStatus: { ...mockTrialStatus, extended: true },
      });

      render(<TrialBanner />);

      await waitFor(() => {
        expect(screen.queryByText('Extend Trial')).not.toBeInTheDocument();
      });
    });

    it('calls extendTrial when button is clicked', async () => {
      render(<TrialBanner />);

      await waitFor(() => {
        const extendButton = screen.getByText('Extend Trial');
        fireEvent.click(extendButton);
      });

      expect(mockUseTrial.extendTrial).toHaveBeenCalled();
    });

    it('shows loading state when extending trial', async () => {
      const slowExtend = vi.fn(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        extendTrial: slowExtend,
      });

      render(<TrialBanner />);

      await waitFor(() => {
        const extendButton = screen.getByText('Extend Trial');
        fireEvent.click(extendButton);
      });

      await waitFor(() => {
        expect(screen.getByText('Extending...')).toBeInTheDocument();
      });
    });

    it('disables button while extending', async () => {
      const slowExtend = vi.fn(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        extendTrial: slowExtend,
      });

      render(<TrialBanner />);

      await waitFor(() => {
        const extendButton = screen.getByText('Extend Trial');
        fireEvent.click(extendButton);
      });

      const extendingButton = await screen.findByText('Extending...');
      expect(extendingButton.closest('button')).toBeDisabled();
    });
  });

  describe('Error Handling', () => {
    it('displays error message when present', async () => {
      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        error: 'Failed to extend trial',
      });

      render(<TrialBanner />);

      await waitFor(() => {
        expect(screen.getByText('Failed to extend trial')).toBeInTheDocument();
      }, { timeout: 3000 });
    });

    it('shows dismiss button for errors', async () => {
      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        error: 'Failed to extend trial',
      });

      render(<TrialBanner />);

      await waitFor(() => {
        // Look for the Dismiss button text (not sr-only text)
        const dismissButtons = screen.getAllByText('Dismiss');
        expect(dismissButtons.length).toBeGreaterThan(0);
      }, { timeout: 3000 });
    });

    it('clears error when dismiss button is clicked', async () => {
      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        error: 'Failed to extend trial',
      });

      render(<TrialBanner />);

      await waitFor(() => {
        const dismissButtons = screen.getAllByText('Dismiss');
        // Click the error dismiss button (not the sr-only one)
        const errorDismiss = dismissButtons.find((btn) => btn.className.includes('underline'));
        if (errorDismiss) {
          fireEvent.click(errorDismiss);
        }
      }, { timeout: 3000 });

      expect(mockUseTrial.clearError).toHaveBeenCalled();
    });
  });

  describe('Loading State', () => {
    it('does not show banner when loading with no trial status', () => {
      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        isLoading: true,
        trialStatus: null,
      });

      const { container } = render(<TrialBanner />);

      // When trialStatus is null, component returns null regardless of loading state
      expect(container.firstChild).toBeNull();
    });

    it('does not show spinner when trial status is null', () => {
      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        isLoading: true,
        trialStatus: null,
      });

      const { container } = render(<TrialBanner />);

      // No spinner when trialStatus is null (component doesn't render)
      const spinner = container.querySelector('.animate-spin');
      expect(spinner).toBeNull();
    });
  });

  describe('Visibility Conditions', () => {
    it('does not render when trialStatus is null', () => {
      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        trialStatus: null,
        isLoading: false,
      });

      const { container } = render(<TrialBanner />);

      expect(container.firstChild).toBeNull();
    });

    it('does not render when trial is not active', () => {
      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        trialStatus: { ...mockTrialStatus, is_active: false },
      });

      const { container } = render(<TrialBanner />);

      expect(container.firstChild).toBeNull();
    });

    it('does not render when user has converted', () => {
      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        trialStatus: { ...mockTrialStatus, converted: true },
      });

      const { container } = render(<TrialBanner />);

      expect(container.firstChild).toBeNull();
    });

    it('does not render when dismissed', async () => {
      render(<TrialBanner />);

      await waitFor(() => {
        // Find and click the dismiss button (X button)
        const dismissButton = screen.getByRole('button', { name: /dismiss/i });
        fireEvent.click(dismissButton);
      });

      // Banner should be removed
      await waitFor(() => {
        expect(screen.queryByText('Trial Account')).not.toBeInTheDocument();
      });
    });
  });

  describe('Dismiss Functionality', () => {
    it('renders dismiss button', async () => {
      render(<TrialBanner />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /dismiss/i })).toBeInTheDocument();
      });
    });

    it('hides banner when dismiss button is clicked', async () => {
      render(<TrialBanner />);

      await waitFor(() => {
        const dismissButton = screen.getByRole('button', { name: /dismiss/i });
        fireEvent.click(dismissButton);
      });

      expect(screen.queryByText('Trial Account')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper button roles', async () => {
      render(<TrialBanner />);

      await waitFor(() => {
        const buttons = screen.getAllByRole('button');
        expect(buttons.length).toBeGreaterThan(0);
      });
    });

    it('has screen reader text for dismiss button', async () => {
      render(<TrialBanner />);

      await waitFor(() => {
        expect(screen.getByText('Dismiss')).toHaveClass('sr-only');
      });
    });
  });

  describe('Edge Cases', () => {
    it('handles exactly 3 days remaining (boundary)', async () => {
      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        trialStatus: { ...mockTrialStatus, days_remaining: 3 },
      });

      const { container } = render(<TrialBanner />);

      await waitFor(() => {
        // Should use yellow scheme for 3 days
        expect(container.querySelector('.bg-yellow-50')).toBeInTheDocument();
      });
    });

    it('handles exactly 7 days remaining (boundary)', async () => {
      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        trialStatus: { ...mockTrialStatus, days_remaining: 7 },
      });

      const { container } = render(<TrialBanner />);

      await waitFor(() => {
        // Should use yellow scheme for 7 days
        expect(container.querySelector('.bg-yellow-50')).toBeInTheDocument();
      });
    });

    it('handles 0 days remaining', async () => {
      vi.mocked(useTrial).mockReturnValue({
        ...mockUseTrial,
        trialStatus: { ...mockTrialStatus, days_remaining: 0 },
      });

      render(<TrialBanner />);

      await waitFor(() => {
        expect(screen.getByText('0 days remaining')).toBeInTheDocument();
      });
    });
  });
});
