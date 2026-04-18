# Implementation Plan: Resend SDK + MONGO_DB_NAME + Prod/Dev Co-location + DB Init

## TL;DR

Four workstreams:

1. **Email** — migrate all email sends from raw SMTP / Django mail backend to the Resend Python SDK
2. **MongoDB** — wire `MONGO_DB_NAME` env var through settings and replace every hardcoded `['legaldb']` (~23 files)
3. **Co-location** — verify prod + dev can run on the same server simultaneously (already implemented — documented here for reference)
4. **Prod DB init** — one-off management command to create all collections/indexes on a fresh prod MongoDB

---

## Part 1 — Resend SDK email migration

| Setting | Value |
|---------|-------|
| From address | `mamla@noreply.mamla.ai` |
| API key env var | `RESEND_API_KEY` (current `EMAIL_HOST_PASSWORD` value) |
| SDK | already installed (`pip install resend`) |
| Old SMTP config | removed from both env files |

### Phase A — Config

**`Legalv1/legalenv` (prod) and `Legalv1/legalenv.dev`** — remove these keys:

```
EMAIL_BACKEND
EMAIL_HOST
EMAIL_USE_TLS
EMAIL_PORT
EMAIL_HOST_USER
EMAIL_HOST_PASSWORD
```

Add:

```
RESEND_API_KEY=re_31hEZkR6_H5CpmgyRpVbHQvEtvtDfK9Ln
EMAIL_FROM=mamla@noreply.mamla.ai
```

**`Legalv1/Legalv1/settings.py`** — remove the six `EMAIL_*` reads; add:

```python
RESEND_API_KEY = os.getenv('RESEND_API_KEY')
EMAIL_FROM     = os.getenv('EMAIL_FROM', 'mamla@noreply.mamla.ai')
```

### Phase B — Code

All send calls follow the Resend SDK pattern:

```python
import resend
from django.conf import settings

resend.api_key = settings.RESEND_API_KEY

resend.Emails.send({
    "from":    settings.EMAIL_FROM,
    "to":      [recipient],
    "subject": subject,
    "html":    html_body,
})
```

Attachments (for `initiate_email`):

```python
"attachments": [
    {"filename": f.name, "content": base64.b64encode(f.read()).decode()}
    for f in attachments
]
```

**Files to change:**

| File | What changes |
|------|--------------|
| `Legalv1/utilities/routes/utils.py` | `Handutilities.initiate_email()` — replace `smtplib` raw SMTP; keep method signature so all task/view callers are unaffected |
| `Legalv1/utilities/views.py` | `send_mail_page()` — replace `send_mail()`; `send_email_v2()` — replace `EmailMessage`; `send_email()` unchanged (delegates to `initiate_email`) |
| `Legalv1/calendar_management/views.py` | `send_event_reminder()` — replace hardcoded `'from@example.com'` + `send_mail()` |

---

## Part 2 — MONGO_DB_NAME wiring

**Root cause**: `settings.py` never reads `MONGO_DB_NAME`, so prod silently hits `legaldb` on every request despite `MONGO_DB_NAME=mamladb` in `legalenv`.

### Step 1 — settings.py

Add near the `MONGO_URI` block:

```python
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'legaldb')
```

### Step 2 — core/init_clients.py

Add a `get_mongo_db()` helper below `get_mongo_client()`:

```python
def get_mongo_db():
    from django.conf import settings
    return db_clients.mongo[settings.MONGO_DB_NAME]
```

Also fix line ~109 inside `DatabaseClients`:

```python
# before
db = db_clients.mongo['legaldb']
# after
db = db_clients.mongo[settings.MONGO_DB_NAME]
```

### Step 3 — Replace all hardcoded `['legaldb']`

Import `get_mongo_db` (alongside or instead of `get_mongo_client`) and replace every `get_mongo_client()['legaldb']` and `mongo['legaldb']` call with `get_mongo_db()`.

**App files (~23 locations):**

| File | Lines |
|------|-------|
| `core/entitlements.py` | L64 |
| `core/views.py` | L30 |
| `calendar_management/tasks.py` | L18 |
| `calendar_management/routes/createupdateevents.py` | L162 |
| `todaysupdates/routes/handlesubscriptions.py` | L23 |
| `whatsapp_module/tasks.py` | L24, 168, 227, 262 |
| `whatsapp_module/views.py` | L29 |
| `search_facility/task.py` | L34 |
| `ai_draft/tasks.py` | L23 |
| `talkdoc/tasks.py` | L23, 315 |
| `talkdoc/storage.py` | L7 |
| `talkdoc/views.py` | L37, 483, 515 |
| `mamla_brain/auth.py` | L14 |
| `mamla_brain/views.py` | L43 |
| `utilities/tasks.py` | L19 |
| `cases/views.py` | L21 |
| `users/supabase_views.py` | L734 |
| `users/tasks.py` | L20 |
| `ecourt_scrapped/services/master_data.py` | L35 |
| `ecourt_scrapped/services/ecourts_crawler.py` | L306 |

**ecourts_scraper special case:**

`ecourts_scraper/cache/collections.py` — replace the module-level constant:

```python
# before
DB_NAME = "legaldb"

# after
from django.conf import settings
DB_NAME = settings.MONGO_DB_NAME
```

**Standalone scripts (3 files):**

| File | Lines |
|------|-------|
| `scripts/optimize_database_indexes.py` | L28, 69, 120 |
| `scripts/backfill_talkdoc_document_metadata.py` | L47 |
| `scripts/calendar_recurring_regression.py` | L27 |

---

## Part 3 — Prod + Dev co-location

**Status: already fully implemented.** `start_backend.sh` handles all isolation.

| Concern | How isolated | Where configured |
|---------|--------------|-----------------|
| Port | 8000 Gunicorn (prod) / 8100 runserver (dev) | `start_backend.sh` |
| Redis | DB 0 (prod) / DB 1 (dev) | env files + `start_backend.sh` |
| OpenSearch | no prefix (prod) / `dev_` prefix (dev) | `legalenv` / `legalenv.dev` |
| MongoDB | `mamladb` (prod) / `legaldb` (dev) | env files (active after Part 2) |
| Celery workers | `prod_worker` / `dev_worker` (named) | `start_backend.sh` |
| Celery concurrency | prod: gevent×100, prefork×4 / dev: gevent×10, prefork×2 | `start_backend.sh` |
| Celery Beat | prod only (prevents double emails/triggers in dev) | `start_backend.sh` |
| Logs | `logs/` (prod) / `logs/dev/` (dev) | `start_backend.sh` |
| Supabase | separate projects + credentials | env files |
| Nginx | domain → port 8000 (user-managed, already configured) | Nginx config |

**Shared services (deliberate — already isolated):**

- **Redis**: single instance, DB 0 vs DB 1
- **OpenSearch**: single instance, index prefix separates data
- **eCourts FastAPI scraper** (`:8001`): single instance started by separate script; Django side stores results into its own MongoDB database (`mamladb` vs `legaldb`)

**Usage:**

```bash
./start_backend.sh prod   # production
./start_backend.sh dev    # development (separate terminal / tmux pane)
```

---

## Part 4 — Fresh prod DB initialization

A Django management command to create all collections and indexes on a fresh prod MongoDB. **Idempotent** — all `ensure_indexes()` calls check for existing indexes before creating.

### Collections and indexes covered

| Source | Collections | Indexes |
|--------|-------------|---------|
| `core/init_clients.py:ensure_indexes()` | user_details, draft_content_data, aidrafts_complete_data, cases, hearing_notes, case_notes, case_tasks | 17 |
| `ecourt_scrapped/services/ecourts_crawler.py:ensure_indexes()` | 7 eCourts hierarchy collections | 7 unique composite |
| `ecourts_scraper/cache/collections.py:ensure_ecourts_indexes()` | ecourts_cache (TTL), ecourts_scrape_jobs, ecourts_selectors, ecourts_reference_data | 7 |
| `scripts/optimize_database_indexes.py` | aidrafts_complete_data (extended), rag_documents, rag_chat_sessions, rag_messages, rag_chunks, user_sessions | ~20 |
| ecourts_scraper agent registries (3) | step_metrics, navigation_registry, captcha_optimizer | 6 |

### Files to create

```
Legalv1/core/management/__init__.py
Legalv1/core/management/commands/__init__.py
Legalv1/core/management/commands/initialize_prod_db.py
```

### Usage

```bash
# Run once on a fresh prod DB (or safely re-run — idempotent)
cd Legalv1
DJANGO_MODE=prod python manage.py initialize_prod_db
```

---

## Verification

| Step | Check |
|------|-------|
| Part 1 | `POST /api/utilities/send-simple-mail/` on dev → email appears in Resend dashboard |
| Part 2 | `DJANGO_MODE=prod python -c "from core.init_clients import get_mongo_db; print(get_mongo_db().name)"` → `mamladb` |
| Part 3 | `./start_backend.sh dev` + `./start_backend.sh prod` simultaneously → both ports accessible, no pid conflicts |
| Part 4 | `DJANGO_MODE=prod python manage.py initialize_prod_db` → completes without errors; verify collections in Atlas |

---

## Scope boundaries

**Included:** Resend SDK migration, MONGO_DB_NAME wiring, co-location verification, fresh-DB init command

**Excluded:** Nginx config (user-managed), per-env Resend API keys, fixing the pre-existing `ecourts_scraper` tasks in `CELERY_BEAT_SCHEDULE` (app is disabled), Resend webhook handling
