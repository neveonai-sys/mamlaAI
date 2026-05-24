# Mamla.AI — Documentation Index

This folder contains **professional documentation** for the codebase so that any developer or AI assistant can understand **what** the system does, **how** it is structured, **where** key logic lives, and **how to continue work** incrementally.

---

## Document Map

| Document | Purpose | Use when |
|----------|---------|----------|
| **[00-agent-quickref.md](./00-agent-quickref.md)** | **Single-page cheat sheet: exact file paths, collections, URL prefixes, conventions** | **Start every task here — replaces scanning the codebase** |
| [01-architecture-overview.md](./01-architecture-overview.md) | High-level system, repo layout, how backend and frontend connect | Onboarding, big-picture context |
| [02-backend-legalv1.md](./02-backend-legalv1.md) | Django backend: apps, auth flow, DB, env, entry points | Working on API, auth, or backend logic |
| [03-frontend-webpack.md](./03-frontend-webpack.md) | Frontend guide for the active MamlaAI UI and the previous webpack UI | Working on UI, routes, or frontend API calls |
| [04-api-reference.md](./04-api-reference.md) | Consolidated API endpoints, auth requirements, patterns | Implementing or changing APIs |
| [16-project-graphify.md](./16-project-graphify.md) | End-to-end project graph for backend, frontend, and integrations | Use as the canonical map for AI assistants and developers |
| [05-changelog-and-improvements.md](./05-changelog-and-improvements.md) | Code review summary, what was done, incremental improvement plans | Planning next steps or continuing refactors |
| [06-ecourts-scraper.md](./06-ecourts-scraper.md) | eCourts scraper: architecture, APIs, cache/jobs, Celery, env, conventions | Working on eCourts APIs, scrapers, or court-data features |

---

## Quick Conventions

- **Backend** lives under `Legalv1/` (Django 5.x, MongoDB, Supabase, Celery).
- **Active frontend** lives under `mamlaAI_ground_zero/frontend/` (React 18, Redux Toolkit, Tailwind, Webpack 5).
- **Previous frontend** lives under `frontend_webpack/` and is kept for reference/parity only.
- **Auth** is **Supabase-only**; legacy JWT/OTP flows have been removed.
- **API base path**: `/api/` (e.g. `/api/users/check-auth/`, `/api/health/`).
- **Environment**: Backend uses `legalenv` (dotenv); frontend uses `process.env.REACT_APP_*` (Webpack DefinePlugin).

Use the docs above by name when asking an AI or a human to "continue from docs/02-backend-legalv1.md" or "follow the API reference in docs/04-api-reference.md".

**For AI assistants (e.g. Cursor):** Prefer reading the relevant doc from this folder before making changes. Start from [README.md](./README.md) and the doc that matches your task (backend → 02, API → 04, eCourts → 06, frontend → 03, etc.) so you don't have to read every line of code.
