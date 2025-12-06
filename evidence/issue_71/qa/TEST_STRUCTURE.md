# Frontend Test Structure Overview

**Issue #71:** 6.5.10 Write frontend tests
**Date:** 2025-12-06

---

## Directory Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── chat/
│   │   │   ├── __tests__/
│   │   │   │   └── ChatMessage.test.tsx ✅ (20 tests, 100% coverage)
│   │   │   ├── ChatContainer.tsx ❌ (not tested)
│   │   │   ├── ChatHistory.tsx ❌ (not tested)
│   │   │   ├── ChatInput.tsx ❌ (not tested)
│   │   │   └── ChatMessage.tsx ✅ (fully tested)
│   │   │
│   │   ├── document/
│   │   │   ├── __tests__/
│   │   │   │   └── DocumentUpload.test.tsx ✅ (22 tests, 97% coverage)
│   │   │   ├── DocumentList.tsx ❌ (not tested)
│   │   │   └── DocumentUpload.tsx ✅ (fully tested)
│   │   │
│   │   ├── trial/
│   │   │   ├── __tests__/
│   │   │   │   └── TrialBanner.test.tsx ✅ (31 tests, 86% coverage)
│   │   │   ├── index.ts
│   │   │   ├── TrialBanner.tsx ✅ (well tested)
│   │   │   ├── UsageMeters.tsx ❌ (not tested)
│   │   │   └── UpgradeCTA.tsx ❌ (not tested)
│   │   │
│   │   ├── layout/
│   │   │   └── Sidebar.tsx ❌ (not tested)
│   │   │
│   │   ├── aws/
│   │   │   ├── AWSAccountConnection.tsx ❌ (not tested)
│   │   │   └── index.ts
│   │   │
│   │   ├── Layout.tsx ❌ (not tested)
│   │   └── ProtectedRoute.tsx ❌ (not tested)
│   │
│   ├── hooks/
│   │   ├── __tests__/
│   │   │   └── useChat.test.ts ✅ (27 tests, 100% coverage)
│   │   ├── useAWSAccounts.ts ❌ (not tested)
│   │   ├── useAuth.ts ❌ (not tested)
│   │   ├── useChat.ts ✅ (fully tested)
│   │   └── useTrial.ts ❌ (not tested)
│   │
│   ├── pages/
│   │   ├── Chat.tsx ❌ (not tested)
│   │   ├── DocumentsPage.tsx ❌ (not tested)
│   │   ├── Login.tsx ❌ (not tested)
│   │   └── Register.tsx ❌ (not tested)
│   │
│   ├── api/
│   │   ├── auth.ts ❌ (not tested)
│   │   ├── awsAccounts.ts ❌ (not tested)
│   │   ├── chat.ts ❌ (not tested)
│   │   ├── client.ts ❌ (not tested)
│   │   ├── documents.ts ❌ (not tested)
│   │   └── trial.ts ❌ (not tested)
│   │
│   ├── utils/
│   │   └── dateUtils.ts ❌ (not tested)
│   │
│   └── test/
│       └── setup.ts ✅ (test infrastructure)
│
├── vitest.config.ts ✅ (test configuration)
└── package.json ✅ (test scripts)
```

---

## Test Coverage Map

```
Legend:
🟢 Excellent (80-100%)
🟡 Good (60-79%)
🟠 Fair (40-59%)
🔴 Poor (0-39%)

Component Tests:
🟢 ChatMessage.tsx          100% │████████████████████│ 20 tests
🟢 DocumentUpload.tsx        97% │███████████████████░│ 22 tests
🟢 TrialBanner.tsx           86% │█████████████████░░░│ 31 tests
🔴 ChatContainer.tsx          0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 ChatHistory.tsx            0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 ChatInput.tsx              0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 DocumentList.tsx           0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 UsageMeters.tsx            0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 UpgradeCTA.tsx             0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 Layout.tsx                 0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 Sidebar.tsx                0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 ProtectedRoute.tsx         0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 AWSAccountConnection.tsx   0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests

Hook Tests:
🟢 useChat.ts               100% │████████████████████│ 27 tests
🔴 useAuth.ts                 0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 useTrial.ts                0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 useAWSAccounts.ts          0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests

Page Tests:
🔴 Login.tsx                  0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 Register.tsx               0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 Chat.tsx                   0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 DocumentsPage.tsx          0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests

API Client Tests:
🔴 auth.ts                    0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 awsAccounts.ts             0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 chat.ts                    0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 client.ts                  0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 documents.ts               0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
🔴 trial.ts                   0% │░░░░░░░░░░░░░░░░░░░░│ 0 tests
```

---

## Test File Organization

### Chat Feature Tests

```
chat/
├── __tests__/
│   ├── ChatMessage.test.tsx ✅
│   ├── ChatContainer.test.tsx ⏭️ (needed)
│   ├── ChatHistory.test.tsx ⏭️ (needed)
│   └── ChatInput.test.tsx ⏭️ (needed)
│
└── Components:
    ├── ChatMessage.tsx ✅ Tested
    ├── ChatContainer.tsx ❌ Untested
    ├── ChatHistory.tsx ❌ Untested
    └── ChatInput.tsx ❌ Untested
```

### Document Feature Tests

```
document/
├── __tests__/
│   ├── DocumentUpload.test.tsx ✅
│   └── DocumentList.test.tsx ⏭️ (needed)
│
└── Components:
    ├── DocumentUpload.tsx ✅ Tested
    └── DocumentList.tsx ❌ Untested
```

### Trial Feature Tests

```
trial/
├── __tests__/
│   ├── TrialBanner.test.tsx ✅
│   ├── UsageMeters.test.tsx ⏭️ (needed)
│   └── UpgradeCTA.test.tsx ⏭️ (needed)
│
└── Components:
    ├── TrialBanner.tsx ✅ Tested
    ├── UsageMeters.tsx ❌ Untested
    └── UpgradeCTA.tsx ❌ Untested
```

### Hook Tests

```
hooks/
├── __tests__/
│   ├── useChat.test.ts ✅
│   ├── useAuth.test.ts ⏭️ (needed - HIGH PRIORITY)
│   ├── useTrial.test.ts ⏭️ (needed)
│   └── useAWSAccounts.test.ts ⏭️ (needed)
│
└── Hooks:
    ├── useChat.ts ✅ Tested
    ├── useAuth.ts ❌ Untested
    ├── useTrial.ts ❌ Untested
    └── useAWSAccounts.ts ❌ Untested
```

### Page Tests (All Needed)

```
pages/
├── __tests__/ ⏭️ (create this directory)
│   ├── Login.test.tsx ⏭️ (needed - HIGH PRIORITY)
│   ├── Register.test.tsx ⏭️ (needed - HIGH PRIORITY)
│   ├── Chat.test.tsx ⏭️ (needed)
│   └── DocumentsPage.test.tsx ⏭️ (needed)
│
└── Pages:
    ├── Login.tsx ❌ Untested
    ├── Register.tsx ❌ Untested
    ├── Chat.tsx ❌ Untested
    └── DocumentsPage.tsx ❌ Untested
```

### API Client Tests (All Needed)

```
api/
├── __tests__/ ⏭️ (create this directory)
│   ├── auth.test.ts ⏭️ (needed)
│   ├── awsAccounts.test.ts ⏭️ (needed)
│   ├── chat.test.ts ⏭️ (needed)
│   ├── client.test.ts ⏭️ (needed)
│   ├── documents.test.ts ⏭️ (needed)
│   └── trial.test.ts ⏭️ (needed)
│
└── API Clients:
    ├── auth.ts ❌ Untested
    ├── awsAccounts.ts ❌ Untested
    ├── chat.ts ❌ Untested
    ├── client.ts ❌ Untested
    ├── documents.ts ❌ Untested
    └── trial.ts ❌ Untested
```

---

## Test Dependency Graph

```
Pages (Integration Level)
│
├── Login.tsx
│   ├── useAuth.ts ❌
│   └── api/auth.ts ❌
│
├── Register.tsx
│   ├── useAuth.ts ❌
│   └── api/auth.ts ❌
│
├── Chat.tsx
│   ├── ChatContainer.tsx ❌
│   │   ├── ChatMessage.tsx ✅
│   │   ├── ChatInput.tsx ❌
│   │   │   └── useChat.ts ✅
│   │   └── useChat.ts ✅
│   ├── ChatHistory.tsx ❌
│   │   └── useChat.ts ✅
│   └── TrialBanner.tsx ✅
│       └── useTrial.ts ❌
│
└── DocumentsPage.tsx
    ├── DocumentUpload.tsx ✅
    │   └── api/documents.ts ❌
    └── DocumentList.tsx ❌
        └── api/documents.ts ❌

Legend:
✅ Component tested
❌ Component not tested
```

---

## Test Creation Priority Order

### Week 1-2: Authentication & Core Chat

```
Priority 1 (Critical):
1. hooks/__tests__/useAuth.test.ts
2. pages/__tests__/Login.test.tsx
3. pages/__tests__/Register.test.tsx
4. components/chat/__tests__/ChatContainer.test.tsx
5. components/chat/__tests__/ChatInput.test.tsx

Estimated: 102 tests, +22% coverage
```

### Week 3-4: Supporting Features

```
Priority 2 (Important):
6. components/chat/__tests__/ChatHistory.test.tsx
7. components/document/__tests__/DocumentList.test.tsx
8. hooks/__tests__/useTrial.test.ts
9. hooks/__tests__/useAWSAccounts.test.ts
10. api/__tests__/auth.test.ts
11. api/__tests__/chat.test.ts
12. api/__tests__/documents.test.ts

Estimated: 103 tests, +20% coverage
```

### Week 5-6: Remaining Components

```
Priority 3 (Nice to have):
13. components/trial/__tests__/UsageMeters.test.tsx
14. components/trial/__tests__/UpgradeCTA.test.tsx
15. components/layout/__tests__/Sidebar.test.tsx
16. components/__tests__/Layout.test.tsx
17. components/__tests__/ProtectedRoute.test.tsx
18. utils/__tests__/dateUtils.test.ts

Estimated: 60 tests, +20% coverage
```

---

## Testing Infrastructure

### Test Configuration Files

```
frontend/
├── vitest.config.ts
│   └── Defines:
│       ├── Test environment (happy-dom)
│       ├── Coverage thresholds (80%)
│       ├── Setup files
│       └── Alias paths (@/)
│
├── src/test/setup.ts
│   └── Provides:
│       ├── @testing-library/jest-dom matchers
│       ├── Mock EventSource
│       ├── Mock IntersectionObserver
│       ├── Mock ResizeObserver
│       ├── Mock window.matchMedia
│       └── Mock window.scrollTo
│
└── package.json
    └── Scripts:
        ├── "test": "vitest"
        ├── "test:ui": "vitest --ui"
        └── "test:coverage": "vitest run --coverage"
```

### Global Test Utilities

```typescript
// Available in all tests (from setup.ts)
- describe()
- it()
- expect()
- vi (Vitest mocking)
- beforeEach()
- afterEach()
- render() (React Testing Library)
- screen (React Testing Library)
- waitFor() (React Testing Library)
- renderHook() (React Testing Library)
- act() (React Testing Library)
- EventSource (mocked)
- IntersectionObserver (mocked)
- ResizeObserver (mocked)
```

---

## Coverage Goals Timeline

```
Current State (Week 0):
Coverage: 17.33%
Tests: 100
Files: 4
[████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 17.33%

After Phase 1 (Week 2):
Coverage: 40%
Tests: ~202
Files: 9
[████████████████░░░░░░░░░░░░░░░░░░░░░░] 40%

After Phase 2 (Week 4):
Coverage: 60%
Tests: ~305
Files: 16
[████████████████████████░░░░░░░░░░░░░░] 60%

After Phase 3 (Week 6):
Coverage: 80% ✅
Tests: ~365
Files: 22
[████████████████████████████████░░░░░░] 80%
```

---

## Test Metrics Summary

```
Current Metrics:
├── Test Files: 4
├── Total Tests: 100
├── Passing: 100 (100%)
├── Failing: 0 (0%)
├── Duration: 932ms
├── Avg per test: 9.32ms
└── Coverage: 17.33%

Target Metrics:
├── Test Files: 22 (+18)
├── Total Tests: 365 (+265)
├── Coverage: 80% (+62.67%)
└── Completion: 6 weeks
```

---

**Test Structure Documented:** 2025-12-06
**Next Action:** Create useAuth.test.ts
