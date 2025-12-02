# Document Upload Component - Testing Checklist

## Pre-Testing Setup

### 1. Ensure Backend is Running
```bash
# Start the backend server
cd /path/to/backend
# Run your backend start command
```

### 2. Ensure Frontend is Running
```bash
cd /Users/robertstanley/desktop/cloud-optimizer/frontend
npm run dev
```

### 3. Login to Application
- Navigate to login page
- Login with valid credentials
- Ensure auth token is stored

### 4. Navigate to Documents Page
- Add route to your router (see INTEGRATION_EXAMPLE.tsx)
- Navigate to `/documents`

## Acceptance Criteria Testing

### ✅ Drag-Drop Zone Visual Feedback
- [ ] Default state: Gray dashed border, gray background
- [ ] On drag enter: Border turns primary-600 (blue), background turns primary-50 (light blue)
- [ ] On drag leave: Returns to default state
- [ ] Multiple drags: Handles nested drag events correctly

### ✅ File Picker Fallback
- [ ] Click anywhere in the drop zone
- [ ] File picker dialog opens
- [ ] Can select files via picker
- [ ] Selected files begin uploading

### ✅ File Type Validation
- [ ] Upload PDF file - ✓ Accepted
- [ ] Upload TXT file - ✓ Accepted
- [ ] Upload JPG file - ✗ Shows error: "Only PDF and TXT files are allowed"
- [ ] Upload PNG file - ✗ Shows error: "Only PDF and TXT files are allowed"
- [ ] Upload DOCX file - ✗ Shows error: "Only PDF and TXT files are allowed"
- [ ] Error message displayed in red with X icon
- [ ] Error auto-dismisses after 5 seconds

### ✅ Size Validation
- [ ] Upload file < 10MB - ✓ Accepted
- [ ] Upload file = 10MB - ✓ Accepted
- [ ] Upload file > 10MB - ✗ Shows error: "File size must be less than 10MB"
- [ ] Error message displayed in red with X icon
- [ ] Error auto-dismisses after 5 seconds

### ✅ Progress Bar
- [ ] Upload starts immediately after validation
- [ ] Progress bar appears showing 0%
- [ ] Progress bar updates smoothly (0-100%)
- [ ] Animated spinner shows during upload
- [ ] Progress bar fills completely before showing success

### ✅ Success/Error States
**Success:**
- [ ] Green checkmark icon appears on completion
- [ ] Success message: "Upload complete" in green
- [ ] Item auto-dismisses after 2 seconds
- [ ] DocumentList updates with new document

**Error:**
- [ ] Red X icon appears on error
- [ ] Error message displays (e.g., "Upload failed" or backend error)
- [ ] Item stays visible (doesn't auto-dismiss)
- [ ] User can see what went wrong

### ✅ Multiple File Support
- [ ] Can drag/drop 2 files at once - both upload
- [ ] Can drag/drop 5 files at once - all upload
- [ ] Try to upload 6 files at once - alert: "You can only upload up to 5 files at once"
- [ ] Each file shows individual progress bar
- [ ] Files upload concurrently (not sequentially)

### ✅ DocumentList Display
- [ ] Empty state shows when no documents
- [ ] Message: "No documents" with icon
- [ ] Subtext: "Get started by uploading your first document"

**Document Cards:**
- [ ] PDF files show red PDF icon
- [ ] TXT files show gray document icon
- [ ] Filename displays (truncated if too long)
- [ ] File size shows in MB (e.g., "2.45 MB")
- [ ] Relative timestamp (e.g., "2 minutes ago")
- [ ] Status badge shows correct color:
  - Yellow for "pending"
  - Blue for "processing"
  - Green for "completed"
  - Red for "failed"

### ✅ Delete Functionality
- [ ] Click delete (trash) icon on a document
- [ ] Confirmation dialog appears: "Are you sure you want to delete this document?"
- [ ] Click Cancel - nothing happens
- [ ] Click OK - document deletes
- [ ] Spinner shows in delete button during deletion
- [ ] Document removed from list after deletion
- [ ] If delete fails, alert shows with error message

## Additional Testing

### Edge Cases
- [ ] Upload same file twice - both uploads succeed
- [ ] Upload file with special characters in name
- [ ] Upload file with very long filename (>100 chars)
- [ ] Rapid uploads - multiple files in quick succession
- [ ] Cancel/leave page during upload (check browser behavior)

### Error Scenarios
- [ ] Backend offline - shows error message
- [ ] Invalid auth token - redirects to login (via interceptor)
- [ ] Network timeout - shows error message
- [ ] Backend returns 500 error - shows error message
- [ ] Malformed response - shows error message

### UI/UX
- [ ] Components are responsive (test at different widths)
- [ ] Text is readable (sufficient contrast)
- [ ] Interactive elements have hover states
- [ ] Loading states don't cause layout shift
- [ ] Animations are smooth (not janky)
- [ ] Focus indicators visible for keyboard navigation

### Performance
- [ ] Large file (9MB) uploads without freezing UI
- [ ] Multiple files upload without blocking interaction
- [ ] List with 50 documents renders quickly
- [ ] Scroll performance is smooth with many documents

### Browser Compatibility
Test in multiple browsers:
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari

## API Testing

### Using Browser DevTools Network Tab

**Upload Document:**
```
POST /api/v1/documents/upload
Status: 200 OK
Content-Type: multipart/form-data
Authorization: Bearer {token}

Response:
{
  "document_id": "uuid-here",
  "filename": "test.pdf",
  "content_type": "application/pdf",
  "file_size": 12345,
  "status": "pending",
  "created_at": "2025-12-02T10:00:00Z"
}
```

**List Documents:**
```
GET /api/v1/documents/?limit=50&offset=0
Status: 200 OK
Authorization: Bearer {token}

Response:
{
  "documents": [...],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

**Delete Document:**
```
DELETE /api/v1/documents/{document_id}
Status: 204 No Content
Authorization: Bearer {token}
```

## Regression Testing

After any changes, verify:
- [ ] Existing chat functionality still works
- [ ] Layout/navigation unchanged
- [ ] Auth flow still works
- [ ] No console errors
- [ ] No TypeScript errors

## Known Issues

Document any issues found during testing:

1. **Issue**: [Description]
   - **Steps to reproduce**:
   - **Expected**:
   - **Actual**:
   - **Severity**: Critical / High / Medium / Low

2. **Issue**: [Description]
   - **Steps to reproduce**:
   - **Expected**:
   - **Actual**:
   - **Severity**: Critical / High / Medium / Low

## Sign-Off

Testing completed by: _______________
Date: _______________
All acceptance criteria met: [ ] Yes [ ] No
Notes: _____________________________________
