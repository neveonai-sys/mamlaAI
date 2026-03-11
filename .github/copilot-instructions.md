# Copilot Instructions — Mamla.AI

> **Every task starts here. Read the relevant doc before touching any code.**
> This file is loaded automatically by GitHub Copilot. Follow it for every task.

---

## RULE 1 — Docs before codebase

The `docs/` folder is the **single source of truth** for where things live, how they work, and what conventions to follow.

**Before reading any source file, read the matching doc:**

| Task type | Read this doc first |
|-----------|-------------------|
| Any task (start here) | `docs/00-agent-quickref.md` |
| Backend: Django apps, auth, DB, Celery | `docs/02-backend-legalv1.md` |
| API endpoints, auth requirements | `docs/04-api-reference.md` |
| Frontend: React, routes, Redux, Axios | `docs/03-frontend-webpack.md` |
| eCourts scraper / court data features | `docs/06-ecourts-scraper.md` |
| Architecture / big picture | `docs/01-architecture-overview.md` |
| What was changed, what's next | `docs/05-changelog-and-improvements.md` |

**`docs/00-agent-quickref.md` is the fastest entry point** — it maps every task to exact file paths in one page. Read it first on any task where you're not sure where to go.

---

## RULE 2 — Task workflow

1. Read `docs/00-agent-quickref.md` (< 5 seconds, saves 200+ lines of codebase scanning).
2. Read the specific doc for your task area (backend / frontend / API / eCourts).
3. Use the doc to navigate directly to the exact file(s). Read *only* those files.
4. For any non-trivial change, compare at least 2 plausible approaches, choose one deliberately, and state the reasoning before implementation.
5. Make the change.
6. Validate the change end-to-end: check editor errors, run the relevant build/check command, and re-open the affected flow to verify behavior.
7. If confidence is still below roughly 90%, iterate once more on the weakest gap instead of stopping at the first pass.
8. **Update the docs** (see Rule 3).

### Review Loop For Substantial Changes

For any feature, parity pass, or bug cluster affecting user workflow:

1. Re-audit the active flow and restate the requirements.
2. Compare UX/architecture options before coding.
3. Fix backend, frontend, and state/DB flow together where needed instead of applying surface patches in one layer only.
4. Verify with editor diagnostics plus the relevant runtime/build checks.
5. Re-check the original requirements for remaining loopholes before closing the task.

---

## RULE 3 — Maintain docs on every change

When you make a change, update the relevant doc **in the same response / commit**:

| Change type | Update this |
|-------------|------------|
| New API endpoint or changed path/auth | `docs/04-api-reference.md` + `docs/02-backend-legalv1.md` (URL table) |
| New Django app or changed app purpose | `docs/02-backend-legalv1.md` (app table) + `docs/01-architecture-overview.md` (repo layout) |
| New frontend route or component | `docs/03-frontend-webpack.md` (route table) |
| Auth flow changed | `docs/02-backend-legalv1.md` (auth section) + `docs/03-frontend-webpack.md` (auth flow) |
| New env var | `docs/02-backend-legalv1.md` (env section) |
| eCourts changes | `docs/06-ecourts-scraper.md` |
| Architecture refactor | `docs/01-architecture-overview.md` + `docs/05-changelog-and-improvements.md` |
| Any completed task or bug fix | `docs/05-changelog-and-improvements.md` (What Was Done table) |
| Quick-ref entry outdated | `docs/00-agent-quickref.md` |

---

## RULE 4 — Key conventions (never look these up again)

- **Backend root:** `Legalv1/` | **Settings:** `Legalv1/Legalv1/settings.py` | **URLs:** `Legalv1/Legalv1/urls.py`
- **Auth:** Supabase-only. Decorator: `@supabase_required` in `Legalv1/supabase_required.py`. No JWT/OTP.
- **DB:** MongoDB primary (`legaldb`). Client: `core.init_clients.get_mongo_client()`. No Django ORM models.
- **API prefix:** `/api/` everywhere (e.g. `/api/users/`, `/api/aidrafts/`, `/api/ecourts/`).
- **Frontend entry:** `frontend_webpack/src/AppContent.js` (all routes). API client: `src/components/common/AxiosInstance.jsx`.
- **Celery broker:** Redis. Queues: `default`, `ecourts_realtime`, `ecourts_background`.
- **eCourts:** `ecourts_api` app is ACTIVE (partner API, no Celery). `ecourts_scraper` is DISABLED (CAPTCHA issues).
- **Frontend env:** `process.env.REACT_APP_*` injected by Webpack DefinePlugin.

---

## RULE 5 — What NOT to do

- ❌ Do not read the entire codebase searching for where something lives — use the docs.
- ❌ Do not add a new auth system — Supabase only.
- ❌ Do not use Django ORM models — apps use raw MongoDB.
- ❌ Do not hardcode `mamla.ai` or `127.0.0.1:8000` — use `FRONTEND_URL` env and `AxiosInstance`.
- ❌ Do not leave docs stale after making a change.
