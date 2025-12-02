# Trial Components - Quick Reference

## Import Statements

```typescript
// All components
import { TrialBanner, UsageMeters, UpgradeCTA } from './components/trial';

// State hook
import { useTrial } from './hooks/useTrial';

// API functions
import { trialApi } from './api/trial';

// Types
import type { TrialStatus, TrialUsage, UsageInfo } from './api/trial';
```

## Basic Integration

```typescript
// Add to Layout.tsx or App.tsx
import { TrialBanner } from './components/trial';

function Layout() {
  return (
    <>
      <TrialBanner />
      {/* Your content */}
    </>
  );
}
```

## Component Props

### TrialBanner
```typescript
// No props required - self-contained
<TrialBanner />
```

### UsageMeters
```typescript
interface UsageMetersProps {
  usage: TrialUsage;
}

<UsageMeters usage={trialStatus.usage} />
```

### UpgradeCTA
```typescript
interface UpgradeCTAProps {
  size?: 'small' | 'medium' | 'large';  // default: 'medium'
  variant?: 'primary' | 'secondary';    // default: 'primary'
  className?: string;                   // optional additional classes
}

<UpgradeCTA size="large" variant="primary" />
```

## Hook API

```typescript
const {
  trialStatus,      // TrialStatus | null
  isLoading,        // boolean
  error,            // string | null
  lastFetched,      // number | null
  fetchTrialStatus, // () => Promise<void>
  extendTrial,      // () => Promise<void>
  clearError,       // () => void
  shouldRefetch,    // () => boolean
} = useTrial();
```

## API Functions

```typescript
// Fetch trial status
const status = await trialApi.getStatus();

// Extend trial
const response = await trialApi.extendTrial();
```

## Color Scheme Logic

### Banner Colors (by days remaining)
- **Green**: > 7 days
- **Yellow**: 3-7 days
- **Red**: < 3 days

### Progress Bar Colors (by usage percentage)
- **Blue**: 0-79%
- **Yellow**: 80-99%
- **Red**: 100%

## Common Patterns

### Manual Fetch
```typescript
import { useTrial } from './hooks/useTrial';

function MyComponent() {
  const { fetchTrialStatus, trialStatus } = useTrial();

  useEffect(() => {
    fetchTrialStatus();
  }, []);

  return <div>{trialStatus?.days_remaining} days left</div>;
}
```

### Conditional Rendering
```typescript
function MyComponent() {
  const { trialStatus } = useTrial();

  if (trialStatus?.is_active && !trialStatus?.converted) {
    return <TrialBanner />;
  }

  return null;
}
```

### Error Handling
```typescript
function MyComponent() {
  const { extendTrial, error, clearError } = useTrial();

  const handleExtend = async () => {
    try {
      await extendTrial();
      alert('Success!');
    } catch (err) {
      // Error is already in store
      console.error(err);
    }
  };

  return (
    <>
      <button onClick={handleExtend}>Extend</button>
      {error && (
        <div>
          {error}
          <button onClick={clearError}>Dismiss</button>
        </div>
      )}
    </>
  );
}
```

## TypeScript Types

```typescript
interface TrialStatus {
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

interface TrialUsage {
  scans: UsageInfo;
  questions: UsageInfo;
  documents: UsageInfo;
}

interface UsageInfo {
  current: number;
  limit: number;
  remaining: number;
}

interface ExtendTrialResponse {
  trial_id: string;
  expires_at: string;
  extended_at: string;
  message: string;
}
```

## Configuration

### Update AWS Marketplace URL
```typescript
// src/components/trial/UpgradeCTA.tsx
const AWS_MARKETPLACE_URL = 'YOUR_ACTUAL_URL';
```

### Change Refetch Interval
```typescript
// src/hooks/useTrial.ts
const REFETCH_INTERVAL = 5 * 60 * 1000; // 5 minutes
```

### Customize Day Thresholds
```typescript
// src/components/trial/TrialBanner.tsx - getColorScheme()
if (daysRemaining > 7) {
  // Green
} else if (daysRemaining >= 3) {
  // Yellow
} else {
  // Red
}
```

### Customize Usage Warning Thresholds
```typescript
// src/components/trial/UsageMeters.tsx - UsageMeter
const percentage = (current / limit) * 100;
const isNearLimit = percentage >= 80;  // Change 80
const isAtLimit = percentage >= 100;
```

## Styling Classes

All components use Tailwind CSS. Key classes:

### Responsive
- `sm:` - Small screens and up
- `md:` - Medium screens and up
- `lg:` - Large screens and up

### Colors
- Green: `bg-green-50`, `text-green-800`, `border-green-200`
- Yellow: `bg-yellow-50`, `text-yellow-800`, `border-yellow-200`
- Red: `bg-red-50`, `text-red-800`, `border-red-200`
- Blue: `bg-blue-600`, `text-blue-600`

### Layout
- Grid: `grid grid-cols-1 sm:grid-cols-3 gap-4`
- Flex: `flex items-center justify-between`

## Accessibility

### ARIA Labels
```typescript
<div
  role="progressbar"
  aria-valuenow={current}
  aria-valuemin={0}
  aria-valuemax={limit}
  aria-label={`${label}: ${current} of ${limit} used`}
/>
```

### Screen Reader Text
```typescript
<span className="sr-only">Dismiss</span>
```

### Focus States
All interactive elements have focus states:
```typescript
focus:outline-none focus:ring-2 focus:ring-offset-2
```

## Testing Checklist

- [ ] Banner appears for active trials
- [ ] Banner hidden for converted users
- [ ] Color changes correctly (green/yellow/red)
- [ ] Usage meters display correct percentages
- [ ] Extend button works when can_extend is true
- [ ] Upgrade button opens AWS Marketplace
- [ ] Banner is dismissible
- [ ] Loading state shows correctly
- [ ] Errors display and can be dismissed
- [ ] Responsive on mobile
- [ ] Keyboard navigation works
- [ ] Screen readers work properly

## Troubleshooting

### Banner not appearing?
- Check `trialStatus?.is_active === true`
- Check `trialStatus?.converted === false`
- Check banner not dismissed (refresh page)
- Check trial API endpoint working

### Colors not changing?
- Verify `days_remaining` value
- Check color thresholds in `getColorScheme()`

### Extend button not working?
- Verify `can_extend === true`
- Check API endpoint `/trial/extend`
- Check for errors in console

### Progress bars stuck?
- Verify usage data structure matches types
- Check percentage calculation
- Ensure limit > 0

## File Locations

```
/Users/robertstanley/desktop/cloud-optimizer/frontend/src/
├── api/trial.ts
├── hooks/useTrial.ts
└── components/trial/
    ├── index.ts
    ├── README.md
    ├── TrialBanner.tsx
    ├── UsageMeters.tsx
    └── UpgradeCTA.tsx
```

## Documentation

- `/frontend/TRIAL_COMPONENTS_USAGE.md` - Comprehensive usage guide
- `/frontend/TRIAL_ARCHITECTURE.md` - Architecture documentation
- `/frontend/src/components/trial/README.md` - Component README

---

**Need help?** Check the comprehensive documentation in `TRIAL_COMPONENTS_USAGE.md`
