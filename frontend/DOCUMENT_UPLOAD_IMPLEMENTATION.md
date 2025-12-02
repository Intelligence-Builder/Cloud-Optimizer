# Document Upload Component Implementation

## Overview
Implementation of GitHub issue #66: DocumentUpload component with drag-drop functionality for Cloud Optimizer.

## Files Created

### 1. API Layer
**File**: `src/api/documents.ts`
- TypeScript interfaces for Document entities
- API functions for document operations (upload, list, get, delete)
- Upload progress tracking support
- Follows existing patterns from `chat.ts`

### 2. Upload Component
**File**: `src/components/document/DocumentUpload.tsx`
- Drag-and-drop zone with visual feedback
- File picker fallback (click anywhere in zone)
- File validation (PDF/TXT only, 10MB max)
- Multiple file support (configurable max, default 5)
- Real-time upload progress bars
- Success/error state handling
- Toast-like notifications for file status

### 3. List Component
**File**: `src/components/document/DocumentList.tsx`
- Displays uploaded documents
- Shows file metadata (size, type, upload time)
- Status badges (pending, processing, completed, failed)
- Delete functionality with confirmation
- Auto-refresh on upload complete
- Empty state and error handling

### 4. Demo Page
**File**: `src/pages/DocumentsPage.tsx`
- Example implementation showing both components
- Demonstrates refresh trigger pattern
- Ready to integrate into app routing

## Features Implemented

### Drag and Drop
- Visual feedback on drag-over (border highlight + background color)
- Drag counter to handle nested elements correctly
- Support for multiple files in single drop

### File Validation
- **Type**: Only PDF (`application/pdf`) and TXT (`text/plain`)
- **Size**: Maximum 10MB per file
- **Count**: Configurable maximum files (default 5)
- Clear error messages for validation failures

### Upload Progress
- Real-time progress bar (0-100%)
- Animated spinner during upload
- Success checkmark on completion
- Error icon with detailed message
- Auto-dismiss after completion (2s) or error display (5s)

### Document List
- File type icons (PDF in red, TXT in gray)
- Human-readable file sizes (B, KB, MB)
- Relative timestamps ("2 minutes ago")
- Status badges with color coding
- Delete with confirmation dialog
- Refresh button for manual updates
- Loading and error states

## Usage

### Basic Usage
```tsx
import { DocumentUpload } from '../components/document/DocumentUpload';
import { DocumentList } from '../components/document/DocumentList';

function MyPage() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  return (
    <>
      <DocumentUpload
        onUploadComplete={() => setRefreshTrigger(prev => prev + 1)}
      />
      <DocumentList refreshTrigger={refreshTrigger} />
    </>
  );
}
```

### Props

#### DocumentUpload
```tsx
interface DocumentUploadProps {
  onUploadComplete?: () => void;  // Called after successful upload
  maxFiles?: number;               // Max files per upload (default: 5)
}
```

#### DocumentList
```tsx
interface DocumentListProps {
  refreshTrigger?: number;  // Increment to trigger refresh
}
```

## API Endpoints Used

### Upload Document
```
POST /documents/upload
Content-Type: multipart/form-data
Authorization: Bearer {token}

Response: {
  document_id: string;
  filename: string;
  content_type: string;
  file_size: number;
  status: string;
  created_at: string;
}
```

### List Documents
```
GET /documents/?limit=50&offset=0
Authorization: Bearer {token}

Response: {
  documents: Document[];
  total: number;
  limit: number;
  offset: number;
}
```

### Delete Document
```
DELETE /documents/{document_id}
Authorization: Bearer {token}
```

## Styling
- Uses Tailwind CSS (no additional CSS files)
- Follows existing design patterns from Layout.tsx
- Color scheme:
  - Primary: `primary-600` (brand color)
  - Success: `green-500`
  - Error: `red-500`
  - Warning: `yellow-500`
- Responsive and accessible

## State Management
- Local React state (useState)
- No external state management required
- Efficient re-render optimization with useCallback

## Error Handling
- Network errors caught and displayed
- Validation errors shown inline
- User-friendly error messages
- Retry functionality on list errors

## Dependencies
All dependencies already present in package.json:
- `react` - Core framework
- `axios` - HTTP client (via apiClient)
- `clsx` - Conditional classes
- `date-fns` - Date formatting

## Integration Steps

### 1. Add Route
In your router configuration:
```tsx
import { DocumentsPage } from './pages/DocumentsPage';

// Add to routes
{
  path: '/documents',
  element: <DocumentsPage />
}
```

### 2. Add Navigation
In your navigation menu:
```tsx
<Link to="/documents">Documents</Link>
```

### 3. Optional: Add to Chat Context
If you want to reference documents in chat:
```tsx
import { documentsApi } from '../api/documents';

// In your chat component
const documents = await documentsApi.listDocuments();
```

## Testing Checklist

- [ ] Drag files into drop zone - border highlights
- [ ] Click zone to open file picker
- [ ] Try uploading non-PDF/TXT file - shows error
- [ ] Try uploading >10MB file - shows error
- [ ] Upload multiple files - shows progress for each
- [ ] Successful upload - shows checkmark, auto-dismisses
- [ ] List shows uploaded documents
- [ ] Delete document - asks for confirmation
- [ ] Refresh button updates list
- [ ] Empty state shows when no documents
- [ ] Error state shows on API failure

## Known Limitations

1. **No pagination UI**: DocumentList uses default limit (50), but doesn't show pagination controls
2. **No download feature**: Delete is implemented, but download would require backend support
3. **No file preview**: Would require additional backend endpoints
4. **No drag reorder**: Files process in order received
5. **No resume uploads**: If upload fails, must retry entire file

## Future Enhancements

- [ ] Pagination controls for large document lists
- [ ] Document download functionality
- [ ] PDF preview modal
- [ ] Search/filter documents
- [ ] Bulk delete
- [ ] Upload queue management
- [ ] Resume failed uploads
- [ ] Drag to reorder
- [ ] Document tagging/categorization

## TypeScript
All components are fully typed with:
- Interface definitions for all props
- Type-safe API responses
- Proper event typing
- No `any` types used

## Accessibility
- Keyboard navigation support
- ARIA labels on interactive elements
- Screen reader friendly
- High contrast colors
- Focus indicators

## Browser Support
- Modern browsers (Chrome, Firefox, Safari, Edge)
- Requires File API support
- Requires drag-and-drop API support
