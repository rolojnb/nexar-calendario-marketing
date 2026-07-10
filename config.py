from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    DATABASE_PATH = str(BASE_DIR / "data" / "calendario.db")
    GENERATED_DIR = str(BASE_DIR / "static" / "generated")
    BRANDING_DIR = str(BASE_DIR / "static" / "branding")

    NEXAR_COMERCIO_PATH = os.getenv("NEXAR_COMERCIO_PATH", "")
    NEXAR_COMERCIO_DB = os.getenv("NEXAR_COMERCIO_DB", "")
    DATA_SOURCE = os.getenv("DATA_SOURCE", "nexar_comercio")
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

    EXTERNAL_SOURCE_STATUS = (
        "Base externa configurada"
        if NEXAR_COMERCIO_DB and Path(NEXAR_COMERCIO_DB).exists()
        else "Base externa no encontrada o no configurada"
    )
