# GitHub Issue #67 - Component Architecture

## Component Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                         TrialBanner                              │
│  (Main orchestration component)                                 │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Trial Status Header                                     │    │
│  │ - Clock icon                                           │    │
│  │ - "Trial Account"                                      │    │
│  │ - "X days remaining" (color-coded)                     │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                  UsageMeters                            │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │    │
│  │  │ Security │  │   Chat   │  │Documents │            │    │
│  │  │  Scans   │  │Questions │  │          │            │    │
│  │  │  5 / 100 │  │ 10 / 50  │  │  2 / 20  │            │    │
│  │  │ ████░░░░ │  │ ████░░░░ │  │ ██░░░░░░ │            │    │
│  │  └──────────┘  └──────────┘  └──────────┘            │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Action Buttons                                          │    │
│  │ ┌────────────────┐  ┌─────────────┐                   │    │
│  │ │ Upgrade to Pro │  │ Extend Trial│  [X]              │    │
│  │ └────────────────┘  └─────────────┘  Dismiss          │    │
│  │    (UpgradeCTA)                                        │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  [Error message display (if present)]                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. TrialBanner (Main Component)
**Responsibility**: Orchestrates all child components and manages overall state

**Features**:
- Fetches trial status on mount
- Manages dismiss state
- Manages extend trial operation
- Handles error display
- Determines color scheme based on days remaining
- Controls visibility based on trial status

**State Management**:
- Uses `useTrial` hook for global state
- Local state for dismiss and extending operations

---

### 2. UsageMeters (Reusable Component)
**Responsibility**: Displays usage metrics with progress bars

**Structure**:
```
UsageMeters (Container)
├── UsageMeter (Security Scans)
├── UsageMeter (Chat Questions)
└── UsageMeter (Documents)
```

**Each UsageMeter Shows**:
- Icon (specific to usage type)
- Label (e.g., "Security Scans")
- Current/Limit (e.g., "5 / 100")
- Progress bar (color-coded)
- Warning messages (if approaching/at limit)

**Progress Bar Colors**:
- Blue: Normal usage (< 80%)
- Yellow: Approaching limit (80-99%)
- Red: Limit reached (100%)

---

### 3. UpgradeCTA (Reusable Button Component)
**Responsibility**: Call-to-action button for upgrading

**Features**:
- Opens AWS Marketplace in new tab
- Configurable sizes: small, medium, large
- Two variants: primary (blue), secondary (outlined)
- Icons: lightning bolt + external link
- Security: noopener, noreferrer flags

**Props Interface**:
```typescript
interface UpgradeCTAProps {
  size?: 'small' | 'medium' | 'large';
  variant?: 'primary' | 'secondary';
  className?: string;
}
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Backend API                              │
│  GET /trial/status  |  POST /trial/extend                   │
└──────────────┬──────────────────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────────────────┐
│                     trialApi                                 │
│  (API Client)                                                │
└──────────────┬──────────────────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────────────────┐
│                   useTrial Hook                              │
│  (Zustand Store - Global State)                             │
│                                                              │
│  State:                                                      │
│  - trialStatus: TrialStatus | null                          │
│  - isLoading: boolean                                       │
│  - error: string | null                                     │
│  - lastFetched: number | null                               │
│                                                              │
│  Actions:                                                    │
│  - fetchTrialStatus()                                       │
│  - extendTrial()                                            │
│  - clearError()                                             │
└──────────────┬──────────────────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────────────────┐
│                  TrialBanner                                 │
│  (Consumes useTrial hook)                                   │
│                                                              │
│  Passes data to:                                            │
│  ├── UsageMeters (usage data)                               │
│  └── UpgradeCTA (no props needed)                           │
└─────────────────────────────────────────────────────────────┘
```

---

## State Management Flow

### Initial Load
```
1. TrialBanner mounts
   ↓
2. useEffect calls fetchTrialStatus()
   ↓
3. useTrial.fetchTrialStatus() sets isLoading = true
   ↓
4. trialApi.getStatus() calls GET /trial/status
   ↓
5. API response received
   ↓
6. useTrial updates state:
   - trialStatus = response data
   - isLoading = false
   - lastFetched = Date.now()
   ↓
7. TrialBanner re-renders with trial data
   ↓
8. UsageMeters and UpgradeCTA render with data
```

### Extend Trial Flow
```
1. User clicks "Extend Trial" button
   ↓
2. TrialBanner.handleExtend() called
   ↓
3. Sets local isExtending = true
   ↓
4. useTrial.extendTrial() called
   ↓
5. trialApi.extendTrial() calls POST /trial/extend
   ↓
6. Success: automatically calls fetchTrialStatus()
   ↓
7. New trial status received
   ↓
8. Banner re-renders with updated data
   ↓
9. isExtending = false
```

### Error Handling Flow
```
1. API call fails (network error, server error, etc.)
   ↓
2. Catch block in useTrial hook
   ↓
3. Set error state: error = error.message
   ↓
4. Set isLoading = false
   ↓
5. TrialBanner detects error state
   ↓
6. Displays error message with dismiss button
   ↓
7. User clicks dismiss
   ↓
8. useTrial.clearError() sets error = null
   ↓
9. Error message hidden
```

---

## Color Scheme Logic

### Color Determination Flow
```
days_remaining value
        ↓
getColorScheme(days_remaining)
        ↓
    ┌───────┐
    │ > 7?  │ → YES → Green scheme (safe)
    └───┬───┘
        │ NO
        ↓
    ┌───────┐
    │ >= 3? │ → YES → Yellow scheme (warning)
    └───┬───┘
        │ NO
        ↓
    Red scheme (urgent)
```

### Color Schemes
```typescript
Green (> 7 days):
  bg: 'bg-green-50'
  border: 'border-green-200'
  text: 'text-green-800'
  accent: 'text-green-600'

Yellow (3-7 days):
  bg: 'bg-yellow-50'
  border: 'border-yellow-200'
  text: 'text-yellow-800'
  accent: 'text-yellow-600'

Red (< 3 days):
  bg: 'bg-red-50'
  border: 'border-red-200'
  text: 'text-red-800'
  accent: 'text-red-600'
```

---

## Visibility Logic

### Banner Display Decision Tree
```
TrialBanner.render()
        ↓
    ┌─────────┐
    │isDismissed│ → YES → return null (hide)
    └────┬────┘
         │ NO
         ↓
    ┌─────────┐
    │trialStatus│ → NULL → return null (hide)
    │  exists?  │
    └────┬────┘
         │ YES
         ↓
    ┌─────────┐
    │converted?│ → YES → return null (hide)
    └────┬────┘
         │ NO
         ↓
    ┌─────────┐
    │is_active?│ → NO → return null (hide)
    └────┬────┘
         │ YES
         ↓
    Render banner (show)
```

**Banner is HIDDEN when**:
1. User dismissed it (session-based)
2. No trial status data available
3. User converted to paid plan
4. Trial is not active (expired)

**Banner is SHOWN when**:
- Active trial
- Not converted
- Not dismissed
- Has trial status data

---

## File Structure

```
frontend/src/
├── components/
│   └── trial/
│       ├── TrialBanner.tsx       # Main component
│       ├── UsageMeters.tsx       # Usage display component
│       ├── UpgradeCTA.tsx        # Upgrade button component
│       ├── index.ts              # Barrel exports
│       ├── README.md             # Component documentation
│       └── __tests__/
│           └── TrialBanner.test.tsx  # Test suite (31 tests)
│
├── hooks/
│   └── useTrial.ts               # Zustand state management
│
└── api/
    └── trial.ts                  # API client
```

---

## Responsive Design

### Desktop Layout (≥ 640px)
```
┌─────────────────────────────────────────────────────────┐
│ Trial Account | 5 days remaining              [X]       │
│                                                          │
│ ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│ │ Security │  │   Chat   │  │Documents │              │
│ │  Scans   │  │Questions │  │          │              │
│ │  5 / 100 │  │ 10 / 50  │  │  2 / 20  │              │
│ │ ████░░░░ │  │ ████░░░░ │  │ ██░░░░░░ │              │
│ └──────────┘  └──────────┘  └──────────┘              │
│                                                          │
│ [Upgrade to Pro]  [Extend Trial]                       │
└─────────────────────────────────────────────────────────┘
```

### Mobile Layout (< 640px)
```
┌──────────────────────────────┐
│ Trial Account | 5 days  [X]  │
│                              │
│ ┌──────────────────────────┐ │
│ │ Security Scans           │ │
│ │ 5 / 100                  │ │
│ │ ████░░░░░░░░░░░░         │ │
│ └──────────────────────────┘ │
│                              │
│ ┌──────────────────────────┐ │
│ │ Chat Questions           │ │
│ │ 10 / 50                  │ │
│ │ ████████░░░░░░░░         │ │
│ └──────────────────────────┘ │
│                              │
│ ┌──────────────────────────┐ │
│ │ Documents                │ │
│ │ 2 / 20                   │ │
│ │ ██░░░░░░░░░░░░░░         │ │
│ └──────────────────────────┘ │
│                              │
│ [Upgrade to Pro]             │
│ [Extend Trial]               │
└──────────────────────────────┘
```

**Responsive Grid**:
```css
grid-cols-1        /* Mobile: 1 column */
sm:grid-cols-3     /* Desktop: 3 columns */
```

---

## TypeScript Types

### Complete Type Hierarchy
```typescript
interface UsageInfo {
  current: number;
  limit: number;
  remaining: number;
}

interface TrialUsage {
  scans: UsageInfo;
  questions: UsageInfo;
  documents: UsageInfo;
}

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

interface TrialState {
  trialStatus: TrialStatus | null;
  isLoading: boolean;
  error: string | null;
  lastFetched: number | null;
  fetchTrialStatus: () => Promise<void>;
  extendTrial: () => Promise<void>;
  clearError: () => void;
  shouldRefetch: () => boolean;
}
```

---

## Accessibility Features

### Screen Reader Support
```tsx
// Hidden text for screen readers
<span className="sr-only">Dismiss</span>

// ARIA labels on progress bars
aria-label={`${label}: ${current} of ${limit} used`}

// Proper roles
role="progressbar"
role="button"
```

### Keyboard Navigation
- All buttons focusable
- Focus visible states
- Tab order logical
- Enter/Space activate buttons

### Color Contrast
- WCAG AA compliant
- Text colors meet contrast requirements
- Visual indicators don't rely solely on color

---

## Testing Architecture

### Test Structure
```
TrialBanner.test.tsx
├── Rendering (6 tests)
│   ├── Renders with correct information
│   ├── Fetches on mount
│   ├── Displays usage meters
│   ├── Displays upgrade CTA
│   ├── Singular/plural days
│   └── ...
│
├── Color Schemes (3 tests)
│   ├── Green > 7 days
│   ├── Yellow 3-7 days
│   └── Red < 3 days
│
├── Extend Trial (6 tests)
│   ├── Shows button when can_extend
│   ├── Hides when can't extend
│   ├── Calls extendTrial on click
│   ├── Loading state
│   └── ...
│
├── Error Handling (3 tests)
├── Loading State (2 tests)
├── Visibility Conditions (4 tests)
├── Dismiss Functionality (2 tests)
├── Accessibility (2 tests)
└── Edge Cases (3 tests)
```

### Mocking Strategy
```typescript
// Mock useTrial hook
vi.mock('../../../hooks/useTrial')

// Mock child components
vi.mock('../UsageMeters')
vi.mock('../UpgradeCTA')

// Mock API calls in useTrial tests
vi.mock('../api/trial')
```

---

## Summary

This architecture provides:
- ✅ Clear separation of concerns
- ✅ Reusable components
- ✅ Type-safe data flow
- ✅ Comprehensive error handling
- ✅ Accessibility built-in
- ✅ Responsive design
- ✅ Testable structure
- ✅ Production-ready quality

**Total Components**: 3 (TrialBanner, UsageMeters, UpgradeCTA)
**Total Tests**: 31 passing tests
**Lines of Code**: ~1,050 (including tests and docs)
