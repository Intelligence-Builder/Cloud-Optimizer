# Trial Components Usage Guide

## Overview
Implementation of GitHub issue #67: TrialBanner and UsageMeters components for Cloud Optimizer.

## Files Created

### API Layer
- `/src/api/trial.ts` - Trial API functions and TypeScript types

### State Management
- `/src/hooks/useTrial.ts` - Zustand hook for trial state management

### Components
- `/src/components/trial/TrialBanner.tsx` - Main trial status banner
- `/src/components/trial/UsageMeters.tsx` - Usage progress bars component
- `/src/components/trial/UpgradeCTA.tsx` - Upgrade button component
- `/src/components/trial/index.ts` - Export barrel for easy imports

## Features Implemented

### TrialBanner Component
- Days remaining displayed prominently
- Color-coded status based on days remaining:
  - Green: >7 days remaining
  - Yellow: 3-7 days remaining
  - Red: <3 days remaining
- Integrated usage meters showing current/limit with progress bars
- Extend trial button (when can_extend is true)
- Upgrade to Pro button with AWS Marketplace link
- Dismissible banner (reappears on refresh)
- Automatically hidden when converted === true or trial inactive
- Loading state while fetching trial data
- Error handling with dismiss capability

### UsageMeters Component
- Progress bars for three usage types:
  - Security Scans
  - Chat Questions
  - Documents
- Semantic color coding:
  - Blue: Normal usage (<80%)
  - Yellow: Approaching limit (80-99%)
  - Red: At limit (100%)
- Visual status messages for limits
- Responsive grid layout (stacks on mobile, 3 columns on desktop)
- Icons for each usage type
- Accessibility support (ARIA labels, roles)

### UpgradeCTA Component
- Configurable sizes: small, medium, large
- Two variants: primary (blue) and secondary (outlined)
- Opens AWS Marketplace in new tab
- Lightning bolt and external link icons
- Proper focus states for accessibility

### useTrial Hook (Zustand)
- State management for trial status
- Automatic refetch logic (5-minute interval)
- Loading and error states
- Trial extend functionality
- Error clearing capability

## Usage Examples

### Basic Usage - Add to Layout

```typescript
import { TrialBanner } from './components/trial';

function Layout() {
  return (
    <div>
      <TrialBanner />
      {/* Rest of your layout */}
    </div>
  );
}
```

### Using Individual Components

```typescript
import { UsageMeters, UpgradeCTA } from './components/trial';
import { useTrial } from './hooks/useTrial';

function CustomTrialDisplay() {
  const { trialStatus, isLoading, fetchTrialStatus } = useTrial();

  useEffect(() => {
    fetchTrialStatus();
  }, []);

  if (!trialStatus || isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <h2>Trial Status</h2>
      <UsageMeters usage={trialStatus.usage} />
      <UpgradeCTA size="large" variant="primary" />
    </div>
  );
}
```

### Using UpgradeCTA Standalone

```typescript
import { UpgradeCTA } from './components/trial';

function PricingPage() {
  return (
    <div>
      <h1>Upgrade Your Plan</h1>
      <UpgradeCTA size="large" variant="primary" />
    </div>
  );
}
```

### Manual Trial Extension

```typescript
import { useTrial } from './hooks/useTrial';

function TrialExtendButton() {
  const { extendTrial, isLoading, error } = useTrial();

  const handleExtend = async () => {
    try {
      await extendTrial();
      alert('Trial extended successfully!');
    } catch (err) {
      console.error('Failed to extend trial:', err);
    }
  };

  return (
    <button onClick={handleExtend} disabled={isLoading}>
      {isLoading ? 'Extending...' : 'Extend Trial'}
    </button>
  );
}
```

## API Integration

The components expect the following API endpoints:

### GET /trial/status
```typescript
{
  trial_id: string;
  status: string;
  is_active: boolean;
  started_at: string;
  expires_at: string;
  days_remaining: number;
  extended: boolean;
  can_extend: boolean;
  converted: boolean;
  usage: {
    scans: { current: number; limit: number; remaining: number };
    questions: { current: number; limit: number; remaining: number };
    documents: { current: number; limit: number; remaining: number };
  }
}
```

### POST /trial/extend
```typescript
{
  trial_id: string;
  expires_at: string;
  extended_at: string;
  message: string;
}
```

## Configuration

### Update AWS Marketplace URL
Edit `/src/components/trial/UpgradeCTA.tsx`:
```typescript
const AWS_MARKETPLACE_URL = 'YOUR_ACTUAL_AWS_MARKETPLACE_URL';
```

### Customize Refetch Interval
Edit `/src/hooks/useTrial.ts`:
```typescript
const REFETCH_INTERVAL = 5 * 60 * 1000; // Change to desired milliseconds
```

### Customize Color Thresholds
Edit `/src/components/trial/TrialBanner.tsx` in the `getColorScheme` function:
```typescript
if (daysRemaining > 7) {
  // Green
} else if (daysRemaining >= 3) {
  // Yellow
} else {
  // Red
}
```

## Styling

All components use Tailwind CSS with responsive design:
- Mobile-first approach
- Responsive grid layouts
- Accessible focus states
- Semantic color coding
- Smooth transitions and animations

## Accessibility Features

- ARIA labels on progress bars
- Keyboard navigation support
- Screen reader support
- Semantic HTML structure
- Focus indicators on all interactive elements

## Testing

To test the components:

1. Start the development server:
```bash
cd frontend
npm run dev
```

2. Mock trial data in your app:
```typescript
// For testing, you can manually set trial status
import { useTrial } from './hooks/useTrial';

const { trialStatus } = useTrial.getState();
```

3. Test different scenarios:
- Trial with >7 days (green theme)
- Trial with 3-7 days (yellow theme)
- Trial with <3 days (red theme)
- Usage at 50%, 85%, 100%
- can_extend true/false
- converted true (banner should hide)

## TypeScript Support

All components are fully typed with TypeScript:
- Compilation verified: ✓
- Type checking passed: ✓
- IntelliSense support: ✓

## Browser Compatibility

Tested and compatible with:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers

## Next Steps

1. Add TrialBanner to your main Layout component
2. Update the AWS Marketplace URL in UpgradeCTA.tsx
3. Test with your backend API endpoints
4. Customize colors/thresholds as needed
5. Add analytics tracking for upgrade button clicks (optional)

## Notes

- Banner is dismissible but will reappear on page refresh
- Trial status auto-refreshes every 5 minutes
- Banner automatically hides for converted users
- All components are responsive and mobile-friendly
- Components follow existing project patterns (Zustand, Tailwind, TypeScript)
