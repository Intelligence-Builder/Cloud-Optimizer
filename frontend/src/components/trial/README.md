# Trial Components

Components for displaying trial status, usage metrics, and upgrade CTAs.

## Components

### TrialBanner
Main banner component that displays trial status at the top of the application.
- Auto-fetches trial status on mount
- Color-coded based on days remaining (green/yellow/red)
- Shows usage meters
- Includes extend trial and upgrade buttons
- Dismissible (reappears on refresh)
- Auto-hides for converted users

### UsageMeters
Displays progress bars for trial usage limits.
- Three meters: Security Scans, Chat Questions, Documents
- Color-coded progress bars (blue/yellow/red)
- Responsive grid layout
- Shows current/limit values

### UpgradeCTA
Call-to-action button for upgrading to Pro plan.
- Links to AWS Marketplace
- Configurable sizes (small/medium/large)
- Two variants (primary/secondary)
- Icons included

## Usage

```typescript
import { TrialBanner } from './components/trial';

function App() {
  return (
    <div>
      <TrialBanner />
      {/* Your app content */}
    </div>
  );
}
```

## State Management

Uses Zustand hook `useTrial` for state management:
- Trial status data
- Loading states
- Error handling
- Extend trial functionality

## API Integration

Requires backend endpoints:
- `GET /trial/status` - Fetch trial status
- `POST /trial/extend` - Extend trial period

See `/frontend/TRIAL_COMPONENTS_USAGE.md` for detailed documentation.
