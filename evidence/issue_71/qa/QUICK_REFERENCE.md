# Frontend Tests - Quick Reference

**Issue #71:** 6.5.10 Write frontend tests
**Date:** 2025-12-06

---

## Quick Stats

- ✅ **100 tests** passing (0 failures)
- 📊 **17.33%** overall coverage (Target: 80%)
- 🎯 **4 components** fully tested (86-100% coverage)
- ⚠️ **27 modules** untested (0% coverage)

---

## Test Commands

```bash
# Run all tests
npm test

# Run with UI
npm run test:ui

# Run with coverage
npm run test:coverage

# Run specific file
npx vitest run src/components/chat/__tests__/ChatMessage.test.tsx
```

---

## Existing Test Files

| File | Tests | Coverage | Status |
|------|-------|----------|--------|
| ChatMessage.test.tsx | 20 | 100% | ✅ Excellent |
| useChat.test.ts | 27 | 100% | ✅ Excellent |
| DocumentUpload.test.tsx | 22 | 97% | ✅ Excellent |
| TrialBanner.test.tsx | 31 | 86% | ✅ Good |

---

## Priority Tests to Create

### 🔴 High Priority (Create First)

1. **useAuth.ts** - Authentication hook
   - Login/logout flows
   - Token management
   - Session persistence

2. **Login.tsx** - Login page
   - Form validation
   - Error handling
   - Redirect after login

3. **Register.tsx** - Registration page
   - Form validation
   - Password requirements
   - Success/error handling

4. **ChatContainer.tsx** - Main chat UI
   - Message list rendering
   - Input integration
   - Session management

5. **ChatInput.tsx** - Message input
   - User input handling
   - Send message action
   - Validation

### 🟡 Medium Priority

1. **ChatHistory.tsx** - Session history
2. **DocumentList.tsx** - Document display
3. **useTrial.ts** - Trial management hook
4. **useAWSAccounts.ts** - AWS integration hook
5. **API clients** - Network layer

### 🟢 Low Priority

1. **Layout.tsx** - Layout component
2. **Sidebar.tsx** - Navigation sidebar
3. **ProtectedRoute.tsx** - Route protection
4. **dateUtils.ts** - Utility functions

---

## Test File Template

### Component Test Template

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ComponentName } from '../ComponentName';

// Mock dependencies
vi.mock('../../api/module', () => ({
  apiFunction: vi.fn(),
}));

describe('ComponentName', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders correctly', () => {
      render(<ComponentName />);

      expect(screen.getByText('Expected Text')).toBeInTheDocument();
    });
  });

  describe('User Interactions', () => {
    it('handles click events', () => {
      render(<ComponentName />);

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(/* assertion */).toBe(true);
    });
  });

  describe('Edge Cases', () => {
    it('handles error states', () => {
      // Test implementation
    });
  });
});
```

### Hook Test Template

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useCustomHook } from '../useCustomHook';

vi.mock('../../api/module', () => ({
  apiFunction: vi.fn(),
}));

describe('useCustomHook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Initialization', () => {
    it('initializes with correct state', () => {
      const { result } = renderHook(() => useCustomHook());

      expect(result.current.value).toBe(expected);
    });
  });

  describe('State Updates', () => {
    it('updates state correctly', async () => {
      const { result } = renderHook(() => useCustomHook());

      await act(async () => {
        await result.current.updateFunction();
      });

      expect(result.current.value).toBe(newValue);
    });
  });
});
```

---

## Coverage Targets by Phase

### Phase 1: Critical Flows (Weeks 1-2)
**Target: 40% coverage**
- useAuth + Login + Register + ChatContainer + ChatInput

### Phase 2: Core Features (Weeks 3-4)
**Target: 60% coverage**
- ChatHistory + DocumentList + useTrial + useAWSAccounts + API clients

### Phase 3: Supporting (Weeks 5-6)
**Target: 80% coverage**
- Layout + Sidebar + ProtectedRoute + Utils + Integration tests

---

## Test Best Practices

### ✅ Do

- Use descriptive test names
- Group tests with `describe` blocks
- Test user interactions, not implementation
- Include edge cases and error scenarios
- Test accessibility (ARIA, semantic HTML)
- Use `waitFor` for async operations
- Clear mocks in `beforeEach`
- Mock external dependencies

### ❌ Don't

- Test implementation details
- Couple tests to internal state
- Forget to clean up mocks
- Skip error handling tests
- Ignore accessibility
- Write flaky async tests
- Duplicate test logic

---

## Common Testing Patterns

### Testing Async State

```typescript
await waitFor(() => {
  expect(screen.getByText('Loaded')).toBeInTheDocument();
}, { timeout: 3000 });
```

### Testing User Events

```typescript
import userEvent from '@testing-library/user-event';

const user = userEvent.setup();
await user.click(button);
await user.type(input, 'text');
```

### Testing API Calls

```typescript
vi.mocked(apiFunction).mockResolvedValue(mockData);

// Trigger action that calls API

await waitFor(() => {
  expect(apiFunction).toHaveBeenCalledWith(expectedArgs);
});
```

### Testing Error States

```typescript
vi.mocked(apiFunction).mockRejectedValue(
  new Error('API Error')
);

// Trigger action

await waitFor(() => {
  expect(screen.getByText('API Error')).toBeInTheDocument();
});
```

---

## Files in This Directory

- **test_summary.json** - Structured test data and metrics
- **TEST_REPORT.md** - Comprehensive test analysis report
- **COVERAGE_VISUALIZATION.md** - Visual coverage charts and roadmap
- **QUICK_REFERENCE.md** - This file (quick reference guide)
- **coverage_output.txt** - Raw coverage report output

---

## Useful Resources

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [Jest DOM Matchers](https://github.com/testing-library/jest-dom)
- [Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)

---

**Last Updated:** 2025-12-06
**Next Action:** Create tests for useAuth hook
