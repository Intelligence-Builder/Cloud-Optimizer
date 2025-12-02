# Document Upload Component Architecture

## Component Hierarchy

```
DocumentsPage (Container)
├── DocumentUpload (Upload UI)
│   ├── Drop Zone
│   │   ├── File Input (hidden)
│   │   ├── Upload Icon
│   │   └── Instructions
│   └── Uploading Files List
│       └── UploadingFile Cards
│           ├── Filename + Size
│           ├── Progress Bar
│           └── Status Icon
└── DocumentList (Display UI)
    ├── Header (title + refresh)
    ├── Empty State (when no docs)
    ├── Error State (when API fails)
    └── Document Cards
        ├── File Icon
        ├── Metadata (name, size, date)
        ├── Status Badge
        └── Delete Button
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      DocumentsPage                          │
│                                                               │
│  ┌─────────────────┐                                        │
│  │ refreshTrigger  │ ◄─────────────────┐                   │
│  │   (state: 0)    │                    │                   │
│  └────────┬────────┘                    │                   │
│           │                              │                   │
│           │         onUploadComplete     │                   │
│           │         callback             │                   │
│           ▼                              │                   │
│  ┌─────────────────────────────────────────────┐           │
│  │          DocumentUpload                      │           │
│  │  ┌─────────────────────────────────────┐   │           │
│  │  │ 1. User drops/selects files         │   │           │
│  │  │ 2. Validate (type, size, count)     │   │           │
│  │  │ 3. Create UploadingFile state       │   │           │
│  │  │ 4. Call documentsApi.uploadDocument │   │           │
│  │  │ 5. Track progress (0-100%)          │   │           │
│  │  │ 6. Update status (success/error)    │   │           │
│  │  │ 7. Call onUploadComplete() ─────────┼───┼───────────┘
│  │  │ 8. Auto-dismiss after delay         │   │
│  │  └─────────────────────────────────────┘   │
│  └─────────────────────────────────────────────┘
│           │
│           │ passes refreshTrigger
│           ▼
│  ┌─────────────────────────────────────────────┐
│  │          DocumentList                        │
│  │  ┌─────────────────────────────────────┐   │
│  │  │ 1. useEffect on refreshTrigger      │   │
│  │  │ 2. Call documentsApi.listDocuments  │   │
│  │  │ 3. Update documents state           │   │
│  │  │ 4. Render document cards            │   │
│  │  │ 5. Handle delete actions            │   │
│  │  └─────────────────────────────────────┘   │
│  └─────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────┘
```

## API Layer

```
┌─────────────────────────────────────────────────────────────┐
│                    documents.ts (API)                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  uploadDocument(file, onProgress)                           │
│    ├─ Create FormData                                       │
│    ├─ POST /documents/upload                                │
│    ├─ Track upload progress                                 │
│    └─ Return: UploadDocumentResponse                        │
│                                                               │
│  listDocuments(limit, offset)                               │
│    ├─ GET /documents/?limit&offset                          │
│    └─ Return: DocumentListResponse                          │
│                                                               │
│  getDocument(documentId)                                    │
│    ├─ GET /documents/{id}                                   │
│    └─ Return: Document                                      │
│                                                               │
│  deleteDocument(documentId)                                 │
│    ├─ DELETE /documents/{id}                                │
│    └─ Return: void                                          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ uses
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  apiClient (Axios)                           │
├─────────────────────────────────────────────────────────────┤
│  Base URL: http://localhost:8080/api/v1                     │
│  Headers: { Authorization: Bearer {token} }                 │
│  Interceptors:                                               │
│    - Add auth token to requests                             │
│    - Handle 401 (redirect to login)                         │
└─────────────────────────────────────────────────────────────┘
```

## State Management

### DocumentUpload Component State

```typescript
// Map of uploading files keyed by unique ID
uploadingFiles: Map<string, UploadingFile>

// UploadingFile structure:
{
  file: File,              // Original File object
  progress: number,        // 0-100
  status: 'uploading' | 'success' | 'error',
  error?: string          // Error message if failed
}

// UI state
isDragging: boolean       // Visual feedback for drag-over
dragCounter: number       // Track nested drag events
```

### DocumentList Component State

```typescript
documents: Document[]     // Array of uploaded documents
loading: boolean          // Initial load state
error: string | null      // Error message if load failed
deletingId: string | null // ID of document being deleted
```

## File Upload Process Flow

```
┌──────────────┐
│ User Action  │
│ (drag/click) │
└──────┬───────┘
       │
       ▼
┌─────────────────────┐
│ Validate Files      │
│ - Type (PDF/TXT)    │
│ - Size (<10MB)      │
│ - Count (≤5)        │
└──────┬──────────────┘
       │
       ├─ Invalid ──────► Show Error (5s) ──► Auto-dismiss
       │
       ▼ Valid
┌──────────────────────┐
│ Create Upload State  │
│ - Generate unique ID │
│ - Set status: upload │
│ - Set progress: 0    │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Call API             │
│ documentsApi.upload  │
└──────┬───────────────┘
       │
       ├─ Progress ─────► Update progress bar (0-100%)
       │
       ├─ Success ──────► Show checkmark ──► Wait 2s ──► Remove
       │                   Call onUploadComplete()
       │
       └─ Error ────────► Show error message
```

## Component Communication

```
┌───────────────┐
│ DocumentsPage │
└───────┬───────┘
        │
        │ Props: { onUploadComplete: callback }
        ▼
┌─────────────────┐
│ DocumentUpload  │  Upload completes
│                 │────────────────────────┐
└─────────────────┘                        │
                                            │ Callback
                                            │ triggers
                                            │
┌───────────────┐                          │
│ DocumentsPage │ ◄────────────────────────┘
│ refreshTrigger++ │
└───────┬────────┘
        │
        │ Props: { refreshTrigger: number }
        ▼
┌─────────────────┐
│ DocumentList    │  useEffect re-runs
│ loadDocuments() │  fetches new data
└─────────────────┘
```

## TypeScript Type Definitions

```typescript
// Core types
interface Document {
  document_id: string;
  filename: string;
  content_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  user_id?: string;
}

interface UploadingFile {
  file: File;
  progress: number;
  status: 'uploading' | 'success' | 'error';
  error?: string;
}

// API responses
interface UploadDocumentResponse {
  document_id: string;
  filename: string;
  content_type: string;
  file_size: number;
  status: string;
  created_at: string;
}

interface DocumentListResponse {
  documents: Document[];
  total: number;
  limit: number;
  offset: number;
}

// Component props
interface DocumentUploadProps {
  onUploadComplete?: () => void;
  maxFiles?: number;
}

interface DocumentListProps {
  refreshTrigger?: number;
}
```

## Event Handlers

### DocumentUpload

```
handleDragEnter    → Increment drag counter, set isDragging
handleDragLeave    → Decrement drag counter, unset if 0
handleDragOver     → Prevent default to allow drop
handleDrop         → Get files, reset drag state, upload
handleFileInput    → Get files from input, reset input
handleClick        → Trigger file input click
validateFile       → Check type and size
uploadFile         → Create state, call API, track progress
handleFiles        → Validate count, loop through files
```

### DocumentList

```
loadDocuments      → Fetch from API, update state
handleDelete       → Confirm, call delete API, update state
handleRefresh      → Manually call loadDocuments
```

## Styling Architecture

```
Tailwind Utility Classes
├── Layout
│   ├── Flexbox (flex, flex-col, items-center, justify-between)
│   ├── Spacing (p-4, m-2, space-y-4)
│   └── Sizing (w-full, h-12, max-w-4xl)
├── Colors
│   ├── Primary (primary-600, primary-50)
│   ├── Gray (gray-100, gray-400, gray-900)
│   ├── Success (green-500, green-50)
│   ├── Error (red-500, red-50)
│   └── Warning (yellow-500, yellow-50)
├── Typography
│   ├── Font size (text-sm, text-base, text-2xl)
│   ├── Font weight (font-medium, font-semibold, font-bold)
│   └── Text color (text-gray-900, text-white)
├── Borders
│   ├── Border width (border, border-2)
│   ├── Border style (border-dashed, border-solid)
│   ├── Border color (border-gray-200, border-primary-600)
│   └── Border radius (rounded, rounded-lg, rounded-full)
├── Effects
│   ├── Shadows (shadow-lg)
│   ├── Transitions (transition-all, transition-colors)
│   ├── Hover states (hover:bg-gray-100)
│   └── Animations (animate-spin)
└── Conditional (via clsx)
    ├── isDragging ? 'border-primary-600' : 'border-gray-300'
    └── status === 'error' ? 'text-red-600' : 'text-green-600'
```

## Performance Considerations

1. **useCallback** - Memoize event handlers to prevent re-renders
2. **Map for uploads** - Efficient O(1) lookups and updates
3. **Auto-dismiss** - Clean up completed uploads to prevent memory leaks
4. **Concurrent uploads** - Multiple files upload in parallel
5. **Lazy loading** - Only render visible documents (future: virtual scroll)

## Error Handling Strategy

```
API Errors
├── Network Error
│   └── Show: "Failed to connect to server"
├── 401 Unauthorized
│   └── Interceptor redirects to login
├── 400 Bad Request
│   └── Show validation error from backend
├── 500 Server Error
│   └── Show: "Server error, please try again"
└── Unknown Error
    └── Show: Generic error message

Validation Errors
├── Invalid Type
│   └── Show: "Only PDF and TXT files are allowed"
├── Too Large
│   └── Show: "File size must be less than 10MB"
└── Too Many Files
    └── Alert: "You can only upload up to X files"
```

## Security Considerations

1. **Auth Token** - Automatically added via axios interceptor
2. **CORS** - Backend must allow multipart/form-data
3. **File Type Validation** - Client-side (UX) + Server-side (security)
4. **File Size Limit** - Prevents DoS attacks
5. **CSRF Protection** - If using cookies (not applicable with Bearer token)

## Future Scalability

```
Current: Simple state management
  ↓
Next: React Query for caching
  ↓
Later: WebSocket for real-time status updates
  ↓
Advanced: Resume interrupted uploads
  ↓
Enterprise: S3 direct upload with presigned URLs
```
