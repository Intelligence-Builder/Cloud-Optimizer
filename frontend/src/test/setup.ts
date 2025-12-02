import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// Reset after each test
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// Mock environment variables
vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8080/api/v1');

// Mock EventSource for SSE tests
class MockEventSource {
  url: string;
  listeners: { [key: string]: ((event: MessageEvent) => void)[] } = {};
  readyState: number = 0;

  constructor(url: string) {
    this.url = url;
    this.readyState = 1; // OPEN
  }

  addEventListener(event: string, handler: (event: MessageEvent) => void) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(handler);
  }

  removeEventListener(event: string, handler: (event: MessageEvent) => void) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter((h) => h !== handler);
    }
  }

  dispatchEvent(event: MessageEvent) {
    const handlers = this.listeners[event.type];
    if (handlers) {
      handlers.forEach((handler) => handler(event));
    }
    return true;
  }

  close() {
    this.readyState = 2; // CLOSED
  }

  // Helper method for tests to simulate events
  simulateMessage(data: string) {
    const event = new MessageEvent('message', { data });
    this.dispatchEvent(event);
  }

  simulateError() {
    const event = new Event('error');
    this.dispatchEvent(event as MessageEvent);
  }
}

// @ts-ignore - Mock EventSource globally
global.EventSource = MockEventSource as any;

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return [];
  }
  unobserve() {}
} as any;

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
} as any;

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock scrollTo
window.scrollTo = vi.fn();
