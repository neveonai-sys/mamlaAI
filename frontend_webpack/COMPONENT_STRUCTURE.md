# Frontend Component Structure

## Modular Organization

The frontend components have been reorganized into a modular structure for better maintainability and clarity:

```
src/components/
├── auth/                    # Authentication related components
│   ├── LoginSupabase.js
│   ├── SignupSupabase.js
│   ├── ResetPasswordSupabase.js
│   └── index.js
│
├── ai-drafting/             # AI draft generation & editing
│   ├── DraftWithAI.js       # Main AI drafting interface
│   ├── DraftViewerComponent.js
│   ├── InitialQueryComponent.js
│   ├── SaveAIDraft.js
│   ├── SavedAIDraftsList.js
│   ├── DraftSectionEditor.js
│   ├── SectionHistory.js
│   ├── TestAIDrafting.js
│   ├── DraftPreview.js
│   └── index.js
│
├── chat/                    # TalkDoc/RAG chat functionality
│   ├── ChatWithDocs.jsx
│   ├── ChatPane.jsx
│   ├── ChatHistoryPanel.jsx
│   ├── DocPicker.jsx
│   ├── talktodocApi.js
│   └── index.js
│
├── calendar/                # Calendar management
│   └── CalendarComponent.js
│
├── layout/                  # App layout & navigation
│   ├── Layout.jsx
│   ├── Navbar.jsx
│   ├── ProtectedRoutes.jsx
│   ├── LogoutButton.js
│   └── index.js
│
├── common/                  # Shared/reusable components
│   ├── AxiosInstance.jsx    # HTTP client configuration
│   ├── InactivityHandler.js
│   ├── LoadingOverlay.js
│   ├── MamlaaiLogo.jsx
│   ├── Message.jsx
│   ├── SearchBar.jsx
│   ├── DocumentPreview.jsx
│   ├── LazyDataGrid.js
│   ├── LazyFullCalendar.js
│   └── index.js
│
├── forms/                   # Form components
│   ├── MyButton.jsx
│   ├── MyPassField.jsx
│   └── MyTextField.jsx
│
├── tabs/                    # Tab components for drafting
│   ├── CreateNewDraftTab.js
│   ├── LoadDraftTab.js
│   └── LoadTemplateTab.js
│
├── unused/                  # Deprecated/unused components
│   ├── Login.js             # Old auth (replaced by LoginSupabase)
│   ├── Signup.js            # Old signup
│   ├── Signup_v2.js
│   ├── ForgetPassword.js
│   ├── CalendarComponent_v2.js
│   ├── Talk2Doc.jsx         # Old TalkDoc version
│   └── TalkDoc.jsx
│
└── [Root level components]  # App-level components
    ├── Home.js
    ├── About.jsx
    ├── CreateDrafts.js
    ├── OnboardClient.js
    ├── SendEmailComponent.js
    ├── SessionsList.js
    ├── TodaysUpdates.jsx
    ├── MyUpdates.jsx
    ├── Feedback.js
    ├── WelcomePage.js
    └── LocationComponent.js
```

## Module Purpose Alignment with Backend

This structure mirrors the Django backend organization:

| Frontend Module | Backend Module | Purpose |
|----------------|----------------|---------|
| `auth/` | `users/` | Authentication & user management |
| `ai-drafting/` | `ai_draft/` | AI-powered legal document drafting |
| `chat/` | `talkdoc/` | RAG-based document Q&A |
| `calendar/` | `calendar_management/` | Meeting & calendar functionality |
| `common/` | `core/` | Shared utilities & configurations |

## Import Usage

Components can now be imported cleanly from their modules:

```javascript
// Old way
import LoginSupabase from './components/LoginSupabase';
import DraftWithAI from './components/DraftWithAI';

// New way (modular)
import { LoginSupabase } from './components/auth';
import { DraftWithAI } from './components/ai-drafting';
import { AxiosInstance } from './components/common';
```

## Deprecated Components (`unused/` folder)

These components are kept for reference but should not be used:
- **Login.js, Signup.js** - Replaced by Supabase-based auth
- **CalendarComponent_v2.js** - Older calendar version
- **Talk2Doc.jsx, TalkDoc.jsx** - Replaced by ChatWithDocs

**TODO**: These can be safely deleted after confirming no dependencies.

## Benefits

1. **Clear Organization**: Each module has a specific purpose
2. **Better Maintainability**: Easier to locate and update components
3. **Reduced Confusion**: Clear separation between active and deprecated code
4. **Scalability**: Easy to add new features within appropriate modules
5. **Aligned with Backend**: Frontend structure mirrors backend organization
