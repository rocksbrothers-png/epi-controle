from dotenv import load_dotenv

import os
from datetime import timezone
from pathlib import Path

load_dotenv()

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ModuleNotFoundError:
    bcrypt = None
    BCRYPT_AVAILABLE = False

try:
    import psycopg2
    from psycopg2 import pool as psycopg2_pool
    from psycopg2.extras import DictCursor
    DB_CONNECTOR_AVAILABLE = True
    DBIntegrityError = psycopg2.IntegrityError
except ModuleNotFoundError:
    psycopg2 = None
    psycopg2_pool = None
    DictCursor = None
    DB_CONNECTOR_AVAILABLE = False
    DBIntegrityError = Exception

BASE_DIR = Path(__file__).resolve().parent.parent / "static"
UTC = timezone.utc
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
DB_POOL_MINCONN = int(os.environ.get("DB_POOL_MINCONN", "1"))
DB_POOL_MAXCONN = int(os.environ.get("DB_POOL_MAXCONN", "10"))
PASSWORD_RECOVERY_KEY = os.environ.get("PASSWORD_RECOVERY_KEY", "").strip()
APP_ENV = str(os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "").strip().lower()
_IS_PRODUCTION_ENV = APP_ENV in {"prod", "production"}
_JWT_SECRET_FROM_ENV = os.environ.get("JWT_SECRET", "").strip()
_JWT_SECRET_FALLBACK = PASSWORD_RECOVERY_KEY or "dev-local-jwt-secret"
JWT_SECRET_FROM_ENV = bool(_JWT_SECRET_FROM_ENV)
JWT_SECRET_IS_FALLBACK = not JWT_SECRET_FROM_ENV
if _IS_PRODUCTION_ENV and not _JWT_SECRET_FROM_ENV:
    raise RuntimeError("JWT_SECRET é obrigatório quando APP_ENV/ENVIRONMENT=prod|production.")
if _IS_PRODUCTION_ENV and not BCRYPT_AVAILABLE:
    raise RuntimeError("bcrypt é obrigatório quando APP_ENV/ENVIRONMENT=prod|production.")
JWT_SECRET = _JWT_SECRET_FROM_ENV or _JWT_SECRET_FALLBACK
JWT_EXP_SECONDS = int(os.environ.get("JWT_EXP_SECONDS", "28800"))
# Refresh token de vida longa (default 30 dias) usado em /api/auth/refresh.
JWT_REFRESH_EXP_SECONDS = int(os.environ.get("JWT_REFRESH_EXP_SECONDS", str(30 * 24 * 3600)))
SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.environ.get("SMTP_FROM", "").strip()
