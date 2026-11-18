"""Vercel Serverless Function Entrypoint for NEXORA ERP (FastAPI + React Portal)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add backend directory to Python path so 'app.*' imports resolve in Vercel serverless runtime
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# On Vercel Serverless, if no external PostgreSQL DATABASE_URL (e.g. Neon / Supabase) is set,
# use /tmp/nexora_erp.db because Vercel's project filesystem is read-only at runtime.
if not os.getenv("DATABASE_URL") and os.getenv("VERCEL"):
    os.environ["DATABASE_URL"] = "sqlite:////tmp/nexora_erp.db"

from app.main import app, initialize_database_and_seed  # noqa: E402

# Ensure database schema and demo data are initialized on cold start
try:
    initialize_database_and_seed()
except Exception:
    pass
