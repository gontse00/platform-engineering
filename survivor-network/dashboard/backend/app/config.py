"""
Application Configuration - Local Survivor Network
Centralized configuration loaded from environment variables for Kind/Local Dev.
"""

import os

# =============================================================================
# Local Data Tier 
# =============================================================================

# PostgreSQL Configuration
DB_HOST = os.environ.get("DB_HOST", "survivor-db-postgresql.data.svc.cluster.local")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "survivor")
DB_USER = os.environ.get("DB_USER", "survivor")
DB_PASS = os.environ.get("DB_PASS", "survivor-pw")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# MinIO / S3 Configuration (Replaces Firebase Storage)
S3_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "survivor-storage.data.svc.cluster.local:9000")
S3_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "survivor-admin")
S3_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "survivor-storage-pw")
S3_SECURE = os.environ.get("S3_SECURE", "false").lower() == "true"
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "survivor-assets")

# =============================================================================
# URLs & Network
# =============================================================================

# These match your Ingress rules in Terraform
API_BASE_URL = os.environ.get("API_BASE_URL", "http://minio-api.127.0.0.1.nip.io")
MAP_BASE_URL = os.environ.get("MAP_BASE_URL", "http://minio.127.0.0.1.nip.io")

# =============================================================================
# Map Settings & Defaults
# =============================================================================

MAP_WIDTH = int(os.environ.get("MAP_WIDTH", "100"))
MAP_HEIGHT = int(os.environ.get("MAP_HEIGHT", "100"))
DEFAULT_MAX_PARTICIPANTS = int(os.environ.get("DEFAULT_MAX_PARTICIPANTS", "500"))

# =============================================================================
# CORS Origins
# =============================================================================

def get_cors_origins() -> list[str]:
    """Get allowed CORS origins including our local nip.io domains."""
    return [
        MAP_BASE_URL,
        "http://minio.127.0.0.1.nip.io",
        "http://localhost:3000",  # Local React dev
        "http://localhost:5173",  # Vite dev
        "http://127.0.0.1:8000",
    ]

def get_cors_origin_regex() -> str:
    """Regex to allow local nip.io subdomains."""
    return r"http://.*\.127\.0\.0\.1\.nip\.io"