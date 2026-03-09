# 01 — Architecture Overview

## System Purpose

**Mamla.AI** is a legal-services platform for **lawyers**, **clients**, and **paralegals**. It provides:

- **AI-assisted legal drafting** (sessions, sections, save/load, PDF export)
- **Document chat (RAG)** via TalkDoc
- **Calendar / event management**
- **Court update subscriptions** (today’s updates)
- **Client onboarding** (lawyers onboard clients with token-based signup)
- **Session management** (view/terminate sessions; auth via Supabase)
- **WhatsApp** integration (webhook; low priority, left as-is for later)

---

## Repository Layout

```
Adalatai_ground_zero/
├── Legalv1/                    # Django backend (API + Celery)
│   ├── Legalv1/                # Project settings, root urls
│   ├── users/                  # Auth, profile, onboarding (Supabase + MongoDB)
│   ├── ai_draft/               # AI drafting sessions
│   ├── create_drafts/          # Template-based drafts
│   ├── calendar_management/    # Events CRUD
│   ├── calendersetup/          # Google Calendar OAuth
│   ├── utilities/              # Email, state/district/court
│   ├── search_facility/        # OpenSearch document search
│   ├── whatsapp_module/        # WhatsApp webhook (unchanged)
│   ├── todaysupdates/          # Court subscriptions
│   ├── talkdoc/                 # RAG document Q&A
│   └── core/                   # Shared clients (Mongo, Supabase), health view
├── frontend_webpack/           # React SPA
│   ├── src/
│   │   ├── index.js            # Entry; ErrorBoundary + Provider + App
│   │   ├── App.js               # ThemeProvider, Router, AppContent
│   │   ├── AppContent.js        # Auth check, route definitions, lazy routes
│   │   ├── store.js             # Redux store
│   │   ├── features/            # userSlice, chatDocsSlice
│   │   ├── components/          # Pages, layout, auth, ai-drafting, chat, etc.
│   │   ├── utils/               # securityUtils
│   │   ├── middleware/          # securityMiddleware (axios)
│   │   └── services/            # talkdocService, etc.
│   ├── webpack.common.js
│   ├── webpack.dev.js           # Dev server, proxy /api -> backend
│   └── webpack.prod.js          # Production build, env injection
└── docs/                       # This documentation set
```

---

## How Backend and Frontend Connect

1. **Development**  
   - Frontend dev server (e.g. port 3000) proxies `/api` to backend (e.g. port 8000).  
   - Frontend uses `baseURL: '/api/'` so requests go to same origin and are proxied.

2. **Production**  
   - Frontend is built to static files; backend serves them or they are served by a reverse proxy (e.g. Nginx).  
   - API base URL is configurable via `REACT_APP_API_BASE_URL` (default `https://mamla.ai/api/`).

3. **Auth**  
   - Login: `POST /api/users/login-user/` (Supabase); backend returns user info; frontend stores token (e.g. in secure storage) and sets Redux state.  
   - Protected routes: frontend calls `GET /api/users/check-auth/` (with credentials/token); backend validates Supabase token and returns user + sessions.  
   - Logout: `POST /api/users/sign-out-user/` (Supabase sign-out); frontend clears state and redirects to login.

4. **Credentials**  
   - Axios is configured with `withCredentials: true` for cookie-based auth where used.  
   - Bearer token is sent via `Authorization` header from secure storage when present.

---

## Technology Stack (Summary)

| Layer    | Technologies |
|----------|--------------|
| Backend  | Django 5.x, Django REST Framework, MongoDB, Supabase (auth), Redis, Celery, OpenSearch (search) |
| Frontend | React 18, React Router v6, Redux Toolkit, MUI v5, Axios, Webpack 5 |
| Auth     | Supabase (login, signup, password reset, session); no JWT/OTP legacy in use |

---

## Entry Points for Code Navigation

- **Backend entry**: `Legalv1/Legalv1/urls.py` → includes per-app urls (`users.urls`, `ai_draft.urls`, etc.).  
- **Backend config**: `Legalv1/Legalv1/settings.py` (env, CORS, DB, Celery).  
- **Frontend entry**: `frontend_webpack/src/index.js` → `App.js` → `AppContent.js`.  
- **Frontend routes**: `frontend_webpack/src/AppContent.js` (all `<Route>` definitions).  
- **API client**: `frontend_webpack/src/components/common/AxiosInstance.jsx` (baseURL, interceptors, auth header).

Use **02-backend-legalv1.md** and **03-frontend-webpack.md** for per-layer detail; **04-api-reference.md** for endpoint-level reference.
