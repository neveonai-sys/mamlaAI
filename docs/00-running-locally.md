# 00 — Running Locally & Deployment

> Start/stop scripts handle most of this automatically. Read this when setting up a fresh machine or debugging the startup sequence.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | conda env `myenv` recommended |
| Node.js | 18+ | `npm` ≥ 9 |
| MongoDB | Atlas (cloud) or local 6+ | Prod uses `mamladb`, dev uses `legaldb` |
| Redis | 6+ | Prod uses DB 0, dev uses DB 1 |
| OpenSearch | 2.x | Shared instance; dev uses `dev_` index prefix |

---

## Environment Files

Create two env files in `Legalv1/` — both are git-ignored:

```
Legalv1/legalenv        ← prod
Legalv1/legalenv.dev    ← dev
```

Required keys in each file:

```env
# MongoDB
MONGO_URI=mongodb+srv://...
MONGO_DB_NAME=mamladb          # prod | legaldb for dev

# Django
SECRET_KEY=...
ENCRYPTION_KEY=...
FRONTEND_URL=https://mamla.ai  # http://localhost:3001 for dev

# Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SECRET_KEY=sb_secret_xxxx
SUPABASE_JWT_TOKEN=sb_publishable_xxxx

# Email (Resend SDK)
RESEND_API_KEY=re_xxxx
EMAIL_FROM=mamla@noreply.mamla.ai

# LLM
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
LLM_DEFAULT_PROVIDER=openrouter   # or openai

# Redis / Celery
CELERY_BROKER_URL=redis://localhost:6379/0    # /1 for dev
CELERY_RESULT_BACKEND=redis://localhost:6379/0
REDIS_URL=redis://localhost:6379/0

# OpenSearch
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_USE_SSL=false
OPENSEARCH_VERIFY_CERTS=false
OPENSEARCH_INDEX_PREFIX=          # leave blank for prod | dev_ for dev

# eCourts scraper
CAPSOLVER_API=CAP-xxxx
ECOURTS_USE_LANGGRAPH=false       # true to enable LangGraph orchestration
ECOURTS_SCRAPER_BASE_URL=http://localhost:8001/dc
HC_SCRAPER_BASE_URL=http://localhost:8001/hc
```

---

## Python Dependencies

```bash
conda activate myenv
pip install -r Legalv1/requirements.txt
```

---

## Fresh Database Initialisation (prod only)

Run once after pointing `MONGO_DB_NAME=mamladb` to an empty Atlas cluster:

```bash
cd Legalv1
DJANGO_MODE=prod python manage.py initialize_prod_db
```

This creates all MongoDB indexes across 7 groups (core app indexes, eCourts hierarchy, eCourts scraper cache, AI-drafts extended, TalkDoc RAG, user sessions, LangGraph agent registries). Idempotent — safe to re-run.

---

## Start / Stop (scripts in repo root)

### Production

```bash
./start.sh          # full prod start: backend + frontend build
./stop.sh prod      # stop prod Gunicorn + Celery workers only
```

Individually:

```bash
./start_backend.sh prod     # Gunicorn on :8000, Redis DB 0, named Celery workers
./start_frontend.sh prod    # npm run build → Nginx serves dist/

./stop_backend.sh prod      # kill Gunicorn + prod Celery workers (dev untouched)
./stop_frontend.sh prod
```

### Development

```bash
./start_backend.sh dev      # runserver on :8100, Redis DB 1, dev Celery workers
./start_frontend.sh dev     # webpack-dev-server on :3001, /api proxied to :8100

./stop.sh dev
```

Both prod and dev can run simultaneously on the same machine without interference.

---

## Manual Start (without scripts)

### Backend

```bash
cd Legalv1
conda activate myenv

# Django dev server
DJANGO_MODE=dev python manage.py runserver 0.0.0.0:8100

# Gunicorn (prod)
DJANGO_MODE=prod gunicorn Legalv1.wsgi:application -c gunicorn_config.py

# Celery worker (prod)
DJANGO_MODE=prod celery -A Legalv1 worker -Q default,ecourts_realtime,ecourts_background \
    -n prod_worker@%h --loglevel=info

# Celery beat (prod only — do NOT run in dev)
DJANGO_MODE=prod celery -A Legalv1 beat --loglevel=info
```

### Frontend

```bash
cd mamlaAI_ground_zero/frontend
npm install

# Dev (hot reload, proxies /api to :8100)
npm start

# Production build
npm run build
# Output: dist/  — point Nginx root here
```

---

## Frontend Environment Injection

The webpack build reads these from the shell environment at build time:

| Variable | Purpose |
|----------|---------|
| `REACT_APP_API_BASE_URL` | API base URL for prod build (e.g. `https://mamla.ai/api/`) |
| `REACT_APP_SUPABASE_URL` | Supabase project URL |
| `REACT_APP_SUPABASE_PUBLISHABLE_KEY` | Supabase publishable (`sb_publishable_*`) key |

Dev build gets these from `webpack.dev.js` defaults + the shell.

---

## Nginx (Production)

The tracked Nginx config is `mamla.ai` in the repo root. Copy to the server:

```bash
sudo cp mamla.ai /etc/nginx/sites-available/mamla.ai
sudo nginx -t
sudo systemctl reload nginx
```

Key settings in the config:
- `root` points to `mamlaAI_ground_zero/frontend/dist/`
- `client_max_body_size` raised for `/api/` traffic (TalkDoc uploads)
- `www.mamla.ai` redirects to `https://mamla.ai`

---

## Prod/Dev Isolation Summary

| Item | Prod | Dev |
|------|------|-----|
| Env file | `legalenv` | `legalenv.dev` |
| Django port | **8000** | **8100** |
| Frontend port | Nginx (80/443) | webpack-dev-server **3001** |
| MongoDB DB | `mamladb` | `legaldb` |
| Redis DB | **0** | **1** |
| Celery workers | `prod_worker@%h`, `prod_ecourts@%h` | `dev_worker@%h`, `dev_ecourts@%h` |
| Celery beat | ✅ runs | ❌ skipped |
| OpenSearch prefix | _(empty)_ | `dev_` |
| Logs | `logs/` | `logs/dev/` |

---

## Useful One-liners

```bash
# Verify MongoDB is pointing to the right database
cd Legalv1
DJANGO_MODE=prod python -c "from core.init_clients import get_mongo_db; print(get_mongo_db().name)"
# → mamladb

# Check Django starts clean (prod)
DJANGO_MODE=prod python manage.py check

# Run calendar recurring regression
DJANGO_MODE=dev python scripts/calendar_recurring_regression.py

# Backfill TalkDoc document metadata (one-off)
DJANGO_MODE=prod python scripts/backfill_talkdoc_document_metadata.py
```
