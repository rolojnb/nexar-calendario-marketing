from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

from PIL import Image
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from database import get_connection


ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_DATA_SOURCES = ("manual", "nexar_comercio")
HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")

DEFAULT_BUSINESS_PROFILE = {
    "nombre_comercial": "",
    "rubro": "",
    "descripcion": "",
    "publico_objetivo": "",
    "ciudad_zona": "",
    "propuesta_valor": "",
    "productos_servicios_principales": "",
    "objetivo_comercial": "",
    "tono_comunicacion": "cercano y profesional",
    "instagram": "",
    "whatsapp": "",
    "sitio_web": "",
    "colores_marca": "",
    "logo_path": "",
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uploads_root(db_path: str) -> Path:
    return Path(db_path).resolve().parent / "uploads"


def _normalize_text(value: Any, max_length: int) -> str:
    return str(value or "").strip()[:max_length]


def _normalize_decimal(value: Any) -> float | None:
    raw = str(value or "").strip().replace(",", ".")
    if not raw:
        return None
    try:
        parsed = float(raw)
    except ValueError:
        return None
    if parsed < 0:
        return None
    return parsed


def parse_brand_colors(raw_value: str) -> list[str]:
    colors: list[str] = []
    seen: set[str] = set()
    for chunk in (raw_value or "").replace(";", ",").split(","):
        color = chunk.strip()
        if not color:
            continue
        if not color.startswith("#"):
            color = f"#{color}"
        if not HEX_COLOR_RE.fullmatch(color):
            continue
        normalized = color.upper()
        if normalized in seen:
            continue
        seen.add(normalized)
        colors.append(normalized)
    return colors


def empty_business_profile() -> dict[str, str]:
    return dict(DEFAULT_BUSINESS_PROFILE)


def validate_business_profile(payload: Mapping[str, Any]) -> tuple[dict[str, str], list[str]]:
    data = {
        "nombre_comercial": _normalize_text(payload.get("nombre_comercial"), 120),
        "rubro": _normalize_text(payload.get("rubro"), 120),
        "descripcion": _normalize_text(payload.get("descripcion"), 600),
        "publico_objetivo": _normalize_text(payload.get("publico_objetivo"), 300),
        "ciudad_zona": _normalize_text(payload.get("ciudad_zona"), 120),
        "propuesta_valor": _normalize_text(payload.get("propuesta_valor"), 300),
        "productos_servicios_principales": _normalize_text(
            payload.get("productos_servicios_principales"),
            400,
        ),
        "objetivo_comercial": _normalize_text(payload.get("objetivo_comercial"), 300),
        "tono_comunicacion": _normalize_text(payload.get("tono_comunicacion"), 120)
        or DEFAULT_BUSINESS_PROFILE["tono_comunicacion"],
        "instagram": _normalize_text(payload.get("instagram"), 120),
        "whatsapp": _normalize_text(payload.get("whatsapp"), 60),
        "sitio_web": _normalize_text(payload.get("sitio_web"), 200),
        "colores_marca": _normalize_text(payload.get("colores_marca"), 200),
    }

    errors: list[str] = []
    if not data["nombre_comercial"]:
        errors.append("El nombre comercial es obligatorio.")
    if not data["rubro"]:
        errors.append("El rubro es obligatorio.")
    if not data["descripcion"]:
        errors.append("La descripción del negocio es obligatoria.")
    if not data["publico_objetivo"]:
        errors.append("El público objetivo es obligatorio.")
    if not data["objetivo_comercial"]:
        errors.append("El objetivo comercial es obligatorio.")
    if data["instagram"] and not data["instagram"].startswith("@"):
        data["instagram"] = f"@{data['instagram'].lstrip('@')}"
    if data["sitio_web"] and " " in data["sitio_web"]:
        errors.append("El sitio web no puede contener espacios.")
    if data["whatsapp"] and not re.fullmatch(r"[0-9+\-() ]{6,60}", data["whatsapp"]):
        errors.append("El WhatsApp debe contener solo números y símbolos válidos.")
    if data["colores_marca"] and not parse_brand_colors(data["colores_marca"]):
        errors.append("Los colores de marca deben ser hexadecimales separados por coma.")
    return data, errors


def validate_catalog_item(payload: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    item_type = str(payload.get("item_type") or "producto").strip().lower()
    if item_type not in {"producto", "servicio"}:
        item_type = "producto"

    data: dict[str, Any] = {
        "nombre": _normalize_text(payload.get("nombre"), 120),
        "descripcion": _normalize_text(payload.get("descripcion"), 600),
        "categoria": _normalize_text(payload.get("categoria"), 120),
        "item_type": item_type,
        "featured": str(payload.get("featured", "")).lower() in {"1", "true", "on", "si"},
        "active": str(payload.get("active", "")).lower() in {"1", "true", "on", "si"},
        "precio": _normalize_decimal(payload.get("precio")),
        "stock": _normalize_decimal(payload.get("stock")),
    }

    errors: list[str] = []
    if not data["nombre"]:
        errors.append("El nombre del producto o servicio es obligatorio.")
    if not data["descripcion"]:
        errors.append("La descripción es obligatoria.")
    if payload.get("precio") not in (None, "") and data["precio"] is None:
        errors.append("El precio debe ser numérico y no negativo.")
    if payload.get("stock") not in (None, "") and data["stock"] is None:
        errors.append("El stock debe ser numérico y no negativo.")
    return data, errors


def get_business_profile(db_path: str) -> dict[str, str]:
    with get_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT nombre_comercial, rubro, descripcion, publico_objetivo, ciudad_zona,
                   propuesta_valor, productos_servicios_principales, objetivo_comercial,
                   tono_comunicacion, instagram, whatsapp, sitio_web, colores_marca,
                   logo_path
            FROM business_profile
            WHERE id = 1
            """
        ).fetchone()

    profile = empty_business_profile()
    if not row:
        return profile
    profile.update({key: str(row[key] or "") for key in profile})
    return profile


def upsert_business_profile(db_path: str, payload: Mapping[str, Any]) -> dict[str, str]:
    data, errors = validate_business_profile(payload)
    if errors:
        raise ValueError("\n".join(errors))

    current = get_business_profile(db_path)
    logo_path = str(payload.get("logo_path") or current.get("logo_path") or "")
    if payload.get("remove_logo"):
        logo_path = ""

    timestamp = _utcnow()
    with get_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO business_profile (
                id, nombre_comercial, rubro, descripcion, publico_objetivo, ciudad_zona,
                propuesta_valor, productos_servicios_principales, objetivo_comercial,
                tono_comunicacion, instagram, whatsapp, sitio_web, colores_marca,
                logo_path, created_at, updated_at
            )
            VALUES (
                1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(id) DO UPDATE SET
                nombre_comercial = excluded.nombre_comercial,
                rubro = excluded.rubro,
                descripcion = excluded.descripcion,
                publico_objetivo = excluded.publico_objetivo,
                ciudad_zona = excluded.ciudad_zona,
                propuesta_valor = excluded.propuesta_valor,
                productos_servicios_principales = excluded.productos_servicios_principales,
                objetivo_comercial = excluded.objetivo_comercial,
                tono_comunicacion = excluded.tono_comunicacion,
                instagram = excluded.instagram,
                whatsapp = excluded.whatsapp,
                sitio_web = excluded.sitio_web,
                colores_marca = excluded.colores_marca,
                logo_path = excluded.logo_path,
                updated_at = excluded.updated_at
            """,
            (
                data["nombre_comercial"],
                data["rubro"],
                data["descripcion"],
                data["publico_objetivo"],
                data["ciudad_zona"],
                data["propuesta_valor"],
                data["productos_servicios_principales"],
                data["objetivo_comercial"],
                data["tono_comunicacion"],
                data["instagram"],
                data["whatsapp"],
                data["sitio_web"],
                data["colores_marca"],
                logo_path,
                timestamp,
                timestamp,
            ),
        )
        connection.commit()
    saved = get_business_profile(db_path)
    saved["logo_path"] = logo_path
    return saved


def get_selected_data_source(db_path: str, default_source: str = "manual") -> str:
    fallback = default_source if default_source in ALLOWED_DATA_SOURCES else "manual"
    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT value FROM app_settings WHERE key = 'data_source'"
        ).fetchone()
    if not row:
        return fallback
    selected = str(row["value"] or "").strip().lower()
    return selected if selected in ALLOWED_DATA_SOURCES else fallback


def set_selected_data_source(db_path: str, source: str, default_source: str = "manual") -> str:
    selected = str(source or "").strip().lower()
    if selected not in ALLOWED_DATA_SOURCES:
        selected = default_source if default_source in ALLOWED_DATA_SOURCES else "manual"
    with get_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES ('data_source', ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (selected, _utcnow()),
        )
        connection.commit()
    return selected


def list_catalog_items(
    db_path: str,
    *,
    include_inactive: bool = True,
    include_deleted: bool = False,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: list[Any] = []
    if not include_deleted:
        conditions.append("deleted_at IS NULL")
    if not include_inactive:
        conditions.append("active = 1")

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    with get_connection(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT id, nombre, descripcion, categoria, precio, stock, item_type,
                   featured, active, image_path, deleted_at, created_at, updated_at
            FROM catalog_items
            {where_clause}
            ORDER BY featured DESC, active DESC, updated_at DESC, id DESC
            """,
            params,
        ).fetchall()
    return [
        {
            **dict(row),
            "featured": bool(row["featured"]),
            "active": bool(row["active"]),
        }
        for row in rows
    ]


def get_catalog_item(db_path: str, item_id: int) -> dict[str, Any] | None:
    with get_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT id, nombre, descripcion, categoria, precio, stock, item_type,
                   featured, active, image_path, deleted_at, created_at, updated_at
            FROM catalog_items
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()
    if not row:
        return None
    return {
        **dict(row),
        "featured": bool(row["featured"]),
        "active": bool(row["active"]),
    }


def create_catalog_item(
    db_path: str,
    payload: Mapping[str, Any],
    *,
    image_path: str = "",
) -> int:
    data, errors = validate_catalog_item(payload)
    if errors:
        raise ValueError("\n".join(errors))

    timestamp = _utcnow()
    with get_connection(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO catalog_items (
                nombre, descripcion, categoria, precio, stock, item_type,
                featured, active, image_path, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["nombre"],
                data["descripcion"],
                data["categoria"],
                data["precio"],
                data["stock"],
                data["item_type"],
                int(data["featured"]),
                int(data["active"]),
                image_path,
                timestamp,
                timestamp,
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def update_catalog_item(
    db_path: str,
    item_id: int,
    payload: Mapping[str, Any],
    *,
    image_path: str | None = None,
    remove_image: bool = False,
) -> None:
    current = get_catalog_item(db_path, item_id)
    if not current or current.get("deleted_at"):
        raise ValueError("El producto o servicio no existe.")

    data, errors = validate_catalog_item(payload)
    if errors:
        raise ValueError("\n".join(errors))

    next_image_path = current.get("image_path", "")
    if image_path is not None:
        next_image_path = image_path
    if remove_image:
        next_image_path = ""

    with get_connection(db_path) as connection:
        connection.execute(
            """
            UPDATE catalog_items
            SET nombre = ?, descripcion = ?, categoria = ?, precio = ?, stock = ?,
                item_type = ?, featured = ?, active = ?, image_path = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                data["nombre"],
                data["descripcion"],
                data["categoria"],
                data["precio"],
                data["stock"],
                data["item_type"],
                int(data["featured"]),
                int(data["active"]),
                next_image_path,
                _utcnow(),
                item_id,
            ),
        )
        connection.commit()


def toggle_catalog_item_active(db_path: str, item_id: int) -> bool:
    current = get_catalog_item(db_path, item_id)
    if not current or current.get("deleted_at"):
        raise ValueError("El producto o servicio no existe.")
    active = not bool(current["active"])
    with get_connection(db_path) as connection:
        connection.execute(
            "UPDATE catalog_items SET active = ?, updated_at = ? WHERE id = ?",
            (int(active), _utcnow(), item_id),
        )
        connection.commit()
    return active


def soft_delete_catalog_item(db_path: str, item_id: int) -> None:
    current = get_catalog_item(db_path, item_id)
    if not current or current.get("deleted_at"):
        raise ValueError("El producto o servicio no existe.")
    with get_connection(db_path) as connection:
        connection.execute(
            """
            UPDATE catalog_items
            SET active = 0, deleted_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (_utcnow(), _utcnow(), item_id),
        )
        connection.commit()


def resolve_managed_path(db_path: str, stored_path: str) -> Path | None:
    if not stored_path:
        return None
    uploads_root = _uploads_root(db_path).resolve()
    candidate = Path(stored_path)
    if not candidate.is_absolute():
        app_root = uploads_root.parent.parent
        candidate_options = [
            (app_root / candidate).resolve(),
            (Path.cwd() / candidate).resolve(),
        ]
    else:
        candidate_options = [candidate.resolve()]

    for candidate_option in candidate_options:
        try:
            candidate_option.relative_to(uploads_root)
        except ValueError:
            continue
        if candidate_option.exists():
            return candidate_option
    return None


def delete_managed_file(db_path: str, stored_path: str) -> None:
    candidate = resolve_managed_path(db_path, stored_path)
    if candidate:
        candidate.unlink(missing_ok=True)


def store_image_upload(
    db_path: str,
    file_storage: FileStorage,
    *,
    bucket: str,
    prefix: str,
) -> str:
    if not file_storage or not file_storage.filename:
        raise ValueError("No se recibió ningún archivo.")

    filename = secure_filename(file_storage.filename)
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Solo se permiten imágenes PNG, JPG, JPEG o WEBP.")

    try:
        image = Image.open(file_storage.stream)
        image.verify()
        file_storage.stream.seek(0)
    except Exception as error:  # pragma: no cover - Pillow raises multiple subclasses
        raise ValueError("El archivo seleccionado no es una imagen válida.") from error

    uploads_root = _uploads_root(db_path)
    bucket_dir = uploads_root / bucket
    bucket_dir.mkdir(parents=True, exist_ok=True)
    output_name = f"{prefix}_{uuid4().hex}{extension}"
    output_path = bucket_dir / output_name
    file_storage.save(output_path)

    return str(Path("data") / "uploads" / bucket / output_name)


def build_brand_settings(base_settings: Mapping[str, str], profile: Mapping[str, str]) -> dict[str, str]:
    colors = parse_brand_colors(str(profile.get("colores_marca", "")))
    primary = colors[0] if len(colors) >= 1 else base_settings["primary"]
    secondary = colors[1] if len(colors) >= 2 else base_settings["secondary"]
    accent = colors[2] if len(colors) >= 3 else base_settings["accent"]

    brand_name = str(profile.get("nombre_comercial") or "").strip() or base_settings["name"]
    instagram = str(profile.get("instagram") or "").strip() or base_settings["instagram"]
    website = str(profile.get("sitio_web") or "").strip() or base_settings["url"]
    logo_path = str(profile.get("logo_path") or "").strip() or base_settings["logo_path"]

    return {
        "name": brand_name,
        "primary": primary,
        "secondary": secondary,
        "accent": accent,
        "font_family": base_settings["font_family"],
        "instagram": instagram,
        "url": website,
        "logo_path": logo_path,
        "backgrounds_dir": base_settings["backgrounds_dir"],
    }


def manual_data_available(db_path: str) -> bool:
    profile = get_business_profile(db_path)
    if profile["nombre_comercial"] or profile["objetivo_comercial"]:
        return True
    return bool(list_catalog_items(db_path, include_inactive=False))
