# Trial Components Architecture

## Component Hierarchy

```
App/Layout
└── TrialBanner (main container)
    ├── useTrial hook (state management)
    ├── UsageMeters (usage display)
    │   └── UsageMeter (individual meter) × 3
    │       ├── Scans
    │       ├── Questions
    │       └── Documents
    └── UpgradeCTA (call-to-action button)
```

## Data Flow

```
Backend API
    ↓
[trialApi]
    ↓
[useTrial (Zustand Store)]
    ↓
[TrialBanner Component]
    ↓
├─→ [UsageMeters Component]
│   └─→ [Individual UsageMeter Components]
└─→ [UpgradeCTA Component]
```

## State Management Flow

```
┌─────────────────────────────────────────┐
│         useTrial (Zustand)              │
├─────────────────────────────────────────┤
│ State:                                   │
│  - trialStatus: TrialStatus | null      │
│  - isLoading: boolean                   │
│  - error: string | null                 │
│  - lastFetched: number | null           │
├─────────────────────────────────────────┤
│ Actions:                                 │
│  - fetchTrialStatus()                   │
│  - extendTrial()                        │
│  - clearError()                         │
│  - shouldRefetch()                      │
└─────────────────────────────────────────┘
         ↓                    ↑
         ↓                    ↑
    [Components]         [API Calls]
         ↓                    ↑
         ↓                    ↑
    [User Actions]    [Backend Endpoints]
```

## Component Responsibilities

### TrialBanner
**Purpose**: Main container orchestrating trial display
**Responsibilities**:
- Fetch trial status on mount
- Manage dismiss state (local)
- Handle trial extension
- Coordinate child components
- Display loading/error states
- Apply color theming based on days remaining

**Color Scheme Logic**:
```
Days > 7:  Green (safe)
Days 3-7:  Yellow (warning)
Days < 3:  Red (urgent)
```

### UsageMeters
**Purpose**: Display usage limits with visual progress bars
**Responsibilities**:
- Render three usage meters (scans, questions, documents)
- Pass usage data to individual meters
- Responsive grid layout

### UsageMeter (internal)
**Purpose**: Individual usage progress bar
**Responsibilities**:
- Calculate percentage used
- Color-code progress bar (blue/yellow/red)
- Display current/limit numbers
- Show warning messages near limits
- Provide accessibility features

**Progress Bar Colors**:
```
0-79%:   Blue (normal)
80-99%:  Yellow (approaching limit)
100%:    Red (limit reached)
```

### UpgradeCTA
**Purpose**: Call-to-action for upgrading account
**Responsibilities**:
- Link to AWS Marketplace
- Configurable size and variant
- Open in new tab with security attributes
- Visual feedback on hover/focus

## API Integration

### Trial API Module (`src/api/trial.ts`)

```typescript
// Endpoints
GET  /trial/status   → TrialStatus
POST /trial/extend   → ExtendTrialResponse

// Types
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
```

## Features Implemented

### Acceptance Criteria Status
- [x] Days remaining displayed prominently
- [x] Color changes based on days remaining (green/yellow/red)
- [x] Usage meters show current/limit with progress bars
- [x] Extend trial button (if can_extend is true)
- [x] Upgrade button links to AWS Marketplace
- [x] Banner hidden when converted === true
- [x] TypeScript compiles without errors
- [x] Mobile responsive design
- [x] Dismissible banner

### Additional Features
- [x] Loading states
- [x] Error handling
- [x] Auto-refetch logic (5-minute interval)
- [x] Accessibility support (ARIA labels)
- [x] Smooth animations and transitions
- [x] Icon integration
- [x] Configurable CTA sizes and variants

## File Structure

```
frontend/src/
├── api/
│   └── trial.ts                  # API functions and types
├── hooks/
│   └── useTrial.ts               # Zustand state management
└── components/
    └── trial/
        ├── index.ts              # Export barrel
        ├── README.md             # Component documentation
        ├── TrialBanner.tsx       # Main banner component
        ├── UsageMeters.tsx       # Usage display component
        └── UpgradeCTA.tsx        # Upgrade button component
```

## Design Patterns Used

### State Management: Zustand
- Similar to existing `useAuth` hook
- Centralized trial state
- Easy to access from any component
- No prop drilling needed

### Component Composition
- Small, focused components
- Reusable parts (UpgradeCTA can be used anywhere)
- Clear separation of concerns

### Responsive Design
- Mobile-first approach
- Grid layouts that adapt
- Touch-friendly button sizes

### Accessibility
- Semantic HTML
- ARIA labels and roles
- Keyboard navigation
- Focus indicators
- Screen reader support

## Integration Example

```typescript
// App.tsx or Layout.tsx
import { TrialBanner } from './components/trial';

function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Trial banner at the top */}
      <TrialBanner />

      {/* Main navigation */}
      <nav>{/* ... */}</nav>

      {/* Page content */}
      <main>{/* ... */}</main>
    </div>
  );
}
```

## Testing Scenarios

1. **Fresh Trial (>7 days)**
   - Banner should be green
   - All usage meters at low percentage
   - Extend button visible if can_extend=true

2. **Mid-Trial (3-7 days)**
   - Banner should be yellow
   - Usage meters showing moderate usage
   - Warning tone in messaging

3. **Expiring Soon (<3 days)**
   - Banner should be red
   - Urgent messaging
   - Upgrade CTA prominent

4. **High Usage (80-99%)**
   - Progress bars turn yellow
   - "Approaching limit" message

5. **At Limit (100%)**
   - Progress bars turn red
   - "Limit reached" message

6. **Converted User**
   - Banner should not appear
   - converted = true

7. **Extended Trial**
   - extended = true
   - can_extend = false
   - Shows extended status

## Performance Considerations

- Auto-refetch with 5-minute interval prevents excessive API calls
- Zustand provides efficient re-renders
- Components only re-render when relevant state changes
- Dismiss state stored locally (not in store)
- Lazy loading possible if needed

## Future Enhancements

Potential improvements:
- [ ] Persist dismiss state in localStorage
- [ ] Add confetti animation on trial extension
- [ ] Email reminder integration
- [ ] Usage trend graphs
- [ ] Custom messaging per usage type
- [ ] A/B testing different CTA copy
- [ ] Analytics event tracking
- [ ] In-app notifications for limit warnings
- [ ] Countdown timer for last 24 hours
- [ ] Social proof ("X users upgraded this week")

## Dependencies

- React 18+
- Zustand (already in project)
- Tailwind CSS (already in project)
- TypeScript 5+
- Axios (via apiClient)

No additional dependencies required!
