from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
    DATABASE_PATH = str(Path(os.getenv("DATABASE_PATH", DATA_DIR / "calendario.db")))
    UPLOADS_DIR = str(Path(os.getenv("UPLOADS_DIR", DATA_DIR / "uploads")))
    EXPORTS_DIR = str(Path(os.getenv("EXPORTS_DIR", DATA_DIR / "exports")))
    BACKUPS_DIR = str(Path(os.getenv("BACKUPS_DIR", DATA_DIR / "backups")))
    CACHE_DIR = str(Path(os.getenv("CACHE_DIR", DATA_DIR / "cache")))
    LOGS_DIR = str(Path(os.getenv("LOGS_DIR", DATA_DIR / "logs")))
    GENERATED_DIR = str(Path(os.getenv("GENERATED_DIR", BASE_DIR / "static" / "generated")))
    BRANDING_DIR = str(BASE_DIR / "static" / "branding")
    RUNTIME_DIRS = (
        str(DATA_DIR),
        UPLOADS_DIR,
        EXPORTS_DIR,
        BACKUPS_DIR,
        CACHE_DIR,
        LOGS_DIR,
        GENERATED_DIR,
    )

    NEXAR_COMERCIO_PATH = os.getenv("NEXAR_COMERCIO_PATH", "")
    NEXAR_COMERCIO_DB = os.getenv("NEXAR_COMERCIO_DB", "")
    DATA_SOURCE = os.getenv("DATA_SOURCE", "manual")
    CSV_DATA_SOURCE_PATH = os.getenv("CSV_DATA_SOURCE_PATH", "")

    BRAND_NAME = os.getenv("BRAND_NAME", "Nexar Marketing")
    BRAND_PRIMARY = os.getenv("BRAND_PRIMARY", "#1D4ED8")
    BRAND_SECONDARY = os.getenv("BRAND_SECONDARY", "#0F172A")
    BRAND_ACCENT = os.getenv("BRAND_ACCENT", "#F59E0B")
    BRAND_FONT_FAMILY = os.getenv("BRAND_FONT_FAMILY", "DejaVuSans")
    BRAND_INSTAGRAM = os.getenv("BRAND_INSTAGRAM", os.getenv("BRAND_FOOTER_HANDLE", "@usuario"))
    BRAND_URL = os.getenv("BRAND_URL", os.getenv("BRAND_FOOTER_URL", "www.tumarca.com"))
    BRAND_LOGO_PATH = os.getenv("BRAND_LOGO_PATH", str(BASE_DIR / "static" / "branding" / "logo.png"))
    BRAND_BACKGROUNDS_DIR = os.getenv(
        "BRAND_BACKGROUNDS_DIR",
        str(BASE_DIR / "static" / "branding" / "fondos"),
    )
