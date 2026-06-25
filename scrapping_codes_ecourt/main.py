"""
main.py — Unified FastAPI entry point for all eCourts scrapers
═══════════════════════════════════════════════════════════════════
Mamla.AI — Single process, single port (8001), two mounted sub-apps.

Mount map:
  /dc/*   →  District Court scraper  (ecourts_fastapi_scrapper_cnr_and_causelist_casestatus_and_courtstatus)
  /hc/*   →  High Court scraper      (hcecourt_fastapi_complete_scrapper)

Adding a future scraper:
  1. from <module> import app as sc_app
  2. app.mount("/sc", sc_app)
  3. Add "SC_SCRAPER_BASE_URL=http://localhost:8001/sc" to legalenv
  4. Add a Django service client pointing to that base URL.
  No changes to existing scrapers or Django views needed.

Security:
  uvicorn is bound to 127.0.0.1 only via start_scrapper.sh.
  CORS allow_origins=["*"] is safe because the listener is localhost-only.

Env:
  Loads Legalv1/legalenv automatically before importing sub-apps.
  Maps CAPSOLVER_API → CAPSOLVER_API_KEY so the DC scraper validates
  at import time without needing the shell script to pre-inject it.
  Shell-injected env vars always take precedence over legalenv values.

Run:
  uvicorn main:app --host 127.0.0.1 --port 8001 --workers 2
  Docs:
    http://localhost:8001/dc/docs  (District Court)
    http://localhost:8001/hc/docs  (High Court)
═══════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ─────────────────────────────────────────────────────────────────
#  ENV BOOTSTRAP  (single point — must happen before sub-app imports)
#
#  The DC scraper raises RuntimeError at import if CAPSOLVER_API_KEY
#  is not set. We load legalenv here so running `uvicorn main:app`
#  directly (dev/prod) works without pre-setting the env in the shell.
#
#  legalenv key:   CAPSOLVER_API=CAP-...
#  sub-app expects: CAPSOLVER_API_KEY=CAP-...  (with _KEY suffix)
#
#  Already-set env vars are NOT overwritten — the shell-injected value
#  from start_scrapper.sh still takes precedence if present.
# ─────────────────────────────────────────────────────────────────

_LEGALENV = (
    Path(__file__).resolve().parent.parent          # scrapping_codes_ecourt/ → project root
    / "Legalv1" / "legalenv"
)

_KEY_MAP = {
    # legalenv key      : env var name expected by scrapers
    "CAPSOLVER_API":      "CAPSOLVER_API_KEY",
    "LOG_LEVEL":          "LOG_LEVEL",
}

def _load_legalenv() -> None:
    if not _LEGALENV.exists():
        return
    with _LEGALENV.open() as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            target = _KEY_MAP.get(key, key)          # remap or pass through as-is
            if target and target not in os.environ:  # never overwrite existing env
                os.environ[target] = val

_load_legalenv()

# ─────────────────────────────────────────────────────────────────
#  LOGGING  (after env bootstrap so LOG_LEVEL from legalenv applies)
# ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="[%(levelname)s -- %(asctime)s -- %(process)d -- %(funcName)s -- %(module)s -- %(lineno)d -- %(name)s] || %(message)s",
)
log = logging.getLogger("scraper.main")
log.info("legalenv loaded from %s", _LEGALENV)

# ─────────────────────────────────────────────────────────────────
#  IMPORT SUB-APPS
#  Each scraper exposes its own FastAPI instance as `app`.
#  We import them under aliases to avoid shadowing our own `app`.
#  Imports must come AFTER _load_legalenv() so CAPSOLVER_API_KEY is
#  already set when the DC scraper validates it at module level.
# ─────────────────────────────────────────────────────────────────

from ecourts_fastapi_scrapper_cnr_and_causelist_casestatus_and_courtstatus import (
    app as dc_app,
)
from hcecourt_fastapi_complete_scrapper import app as hc_app

# ─────────────────────────────────────────────────────────────────
#  ROOT APPLICATION
# ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Mamla.AI — Unified eCourts Scraper",
    description=(
        "Single entry point for all eCourts FastAPI scrapers.\n\n"
        "| Prefix | Scraper | Docs |\n"
        "|--------|---------|------|\n"
        "| `/dc`  | District Court (ecourts.gov.in) | [/dc/docs](/dc/docs) |\n"
        "| `/hc`  | High Courts (hcservices.ecourts.gov.in) | [/hc/docs](/hc/docs) |\n\n"
        "All sub-app endpoints, response formats, and request/response contracts are "
        "unchanged — only the URL base prefix is added. "
        "Django service clients point to `http://localhost:8001/dc` and "
        "`http://localhost:8001/hc` respectively."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────
#  MOUNT SUB-APPS
#  Starlette strips the prefix before dispatching to each sub-app,
#  so each sub-app continues to see its own root-relative paths.
# ─────────────────────────────────────────────────────────────────

app.mount("/dc", dc_app)
app.mount("/hc", hc_app)

# ─────────────────────────────────────────────────────────────────
#  ROOT ENDPOINTS
# ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["Info"], summary="Mounted scraper map")
def index():
    return {
        "service": "Mamla.AI Unified eCourts Scraper",
        "scrapers": {
            "dc": {
                "label": "District Court",
                "base": "/dc",
                "docs": "/dc/docs",
                "health": "/dc/health",
            },
            "hc": {
                "label": "High Courts (25 HCs)",
                "base": "/hc",
                "docs": "/hc/docs",
                "health": "/hc/health",
            },
        },
    }


@app.get("/health", tags=["Info"], summary="Aggregated health — polls both sub-app /health endpoints")
async def health():
    """
    Checks both scraper /health endpoints in parallel and returns a combined status.
    Overall status is "ok" only when both are reachable and return ok.
    """
    base = "http://127.0.0.1:8001"

    async def _check(label: str, path: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{base}{path}")
                data = r.json()
                return {"status": "ok", "detail": data}
        except Exception as exc:
            return {"status": "unreachable", "error": str(exc)}

    dc_result, hc_result = await asyncio.gather(
        _check("dc", "/dc/health"),
        _check("hc", "/hc/health"),
    )

    overall = "ok" if dc_result["status"] == "ok" and hc_result["status"] == "ok" else "degraded"

    return JSONResponse(
        status_code=200,
        content={
            "status": overall,
            "scrapers": {
                "dc": dc_result,
                "hc": hc_result,
            },
        },
    )
