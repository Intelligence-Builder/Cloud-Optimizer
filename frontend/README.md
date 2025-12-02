# Cloud Optimizer Frontend

React + TypeScript + Vite frontend for the Cloud Optimizer application.

## Features

- **Authentication**: Login/Register pages with JWT token management
- **Chat Interface**: Real-time streaming chat with AI assistant
- **Markdown Support**: Full markdown rendering with syntax highlighting
- **Trial Status**: Visual indicators for trial status and query limits
- **Mobile Responsive**: Tailwind CSS for responsive design

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **React Router** - Client-side routing
- **React Query** - Server state management
- **Zustand** - Client state management
- **Axios** - HTTP client
- **React Markdown** - Markdown rendering
- **Highlight.js** - Code syntax highlighting

## Project Structure

```
frontend/
├── src/
│   ├── api/              # API client and endpoints
│   │   ├── client.ts     # Axios client with interceptors
│   │   ├── auth.ts       # Authentication API
│   │   └── chat.ts       # Chat API with SSE streaming
│   ├── components/       # Reusable components
│   │   ├── chat/         # Chat-specific components
│   │   │   ├── ChatContainer.tsx  # Main chat container
│   │   │   ├── ChatMessage.tsx    # Individual message
│   │   │   └── ChatInput.tsx      # Message input
│   │   ├── Layout.tsx    # Main layout with header
│   │   └── ProtectedRoute.tsx  # Route protection
│   ├── hooks/            # Custom React hooks
│   │   ├── useAuth.ts    # Authentication state
│   │   └── useChat.ts    # Chat state and streaming
│   ├── pages/            # Page components
│   │   ├── Login.tsx     # Login page
│   │   ├── Register.tsx  # Registration page
│   │   └── Chat.tsx      # Main chat page
│   ├── App.tsx           # Root component with routes
│   ├── main.tsx          # Application entry point
│   └── index.css         # Global styles
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Backend API running on http://localhost:8080

### Installation

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file (optional):
```bash
cp .env.example .env
```

3. Start development server:
```bash
npm run dev
```

The application will be available at http://localhost:3000

### Build for Production

```bash
npm run build
```

Build output will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Configuration

### Environment Variables

Create a `.env` file in the frontend directory:

```env
VITE_API_BASE_URL=http://localhost:8080/api/v1
```

### API Proxy

Vite is configured to proxy `/api` requests to the backend server. See `vite.config.ts`.

## Components

### ChatMessage
Displays individual chat messages with:
- User/assistant role indicators
- Timestamp (relative)
- Markdown rendering for assistant messages
- Code syntax highlighting
- Streaming indicator

### ChatInput
Auto-resizing textarea with:
- Send button
- Loading state
- Keyboard shortcuts (Enter to send, Shift+Enter for newline)
- Character indicator

### ChatContainer
Main chat interface with:
- Auto-scrolling message list
- SSE streaming support
- Error handling
- Loading states
- Welcome screen for empty state

### Layout
Application layout with:
- Header with logo and user menu
- Trial status indicators
- Query usage display
- Responsive design

## State Management

### Authentication (Zustand)
- User data and token stored in localStorage
- Auto-refresh on app load
- Logout clears all state

### Chat (Custom Hook)
- Message list management
- SSE streaming integration
- Error handling
- Session management

## API Integration

### Authentication Flow
1. User submits login/register form
2. API returns JWT token
3. Token stored in localStorage
4. Axios interceptor adds token to all requests
5. 401 errors trigger automatic logout

### Chat Streaming
1. User sends message
2. Message added to UI immediately
3. SSE connection established
4. Chunks streamed and appended to assistant message
5. Connection closed on completion

## Styling

Using Tailwind CSS with custom configuration:

- **Primary color**: Blue (customizable in `tailwind.config.js`)
- **Component classes**: Pre-defined in `index.css`
- **Markdown styles**: Custom classes for rendered content
- **Responsive breakpoints**: Tailwind defaults

## Scripts

```bash
npm run dev      # Start dev server
npm run build    # Build for production
npm run preview  # Preview production build
npm run lint     # Run ESLint
```

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Issues Implemented

- Issue #62: React/Vite/Tailwind Setup
- Issue #63: ChatMessage Component
- Issue #64: ChatInput Component
- Issue #65: ChatContainer Component
- Issue #66-67: API Client & Hooks
- Issue #68-71: Pages & Layout

## Future Enhancements

- [ ] Session history sidebar
- [ ] Dark mode toggle
- [ ] Message editing/deletion
- [ ] File upload support
- [ ] Export chat history
- [ ] Keyboard shortcuts
- [ ] Accessibility improvements
