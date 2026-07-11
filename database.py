from __future__ import annotations

import sqlite3
from pathlib import Path


def get_connection(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def ensure_runtime_directories(paths: list[str] | tuple[str, ...]) -> None:
    for raw_path in paths:
        if raw_path:
            Path(raw_path).mkdir(parents=True, exist_ok=True)


def _add_column(connection: sqlite3.Connection, columns: set[str], column: str, definition: str) -> None:
    if column not in columns:
        connection.execute(f"ALTER TABLE marketing_posts ADD COLUMN {column} {definition}")
        columns.add(column)


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with get_connection(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS marketing_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                canal TEXT NOT NULL,
                tipo TEXT NOT NULL,
                titulo TEXT NOT NULL,
                texto TEXT NOT NULL,
                hashtags TEXT DEFAULT '',
                caption TEXT DEFAULT '',
                cta TEXT DEFAULT '',
                visual_headline TEXT DEFAULT '',
                visual_subtitle TEXT DEFAULT '',
                visual_cta TEXT DEFAULT '',
                strategy_used TEXT DEFAULT '',
                content_provider TEXT DEFAULT '',
                content_model TEXT DEFAULT '',
                generation_status TEXT DEFAULT 'generated',
                imagen_path TEXT DEFAULT '',
                producto_nombre TEXT DEFAULT '',
                producto_id TEXT DEFAULT '',
                categoria_nombre TEXT DEFAULT '',
                imagen_producto_path TEXT DEFAULT '',
                origen_contenido TEXT DEFAULT 'generico',
                fecha_especial_nombre TEXT DEFAULT '',
                prioridad TEXT DEFAULT '',
                estado TEXT DEFAULT 'borrador',
                created_at TEXT NOT NULL,
                updated_at TEXT DEFAULT ''
            )
            """
        )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(marketing_posts)").fetchall()
        }
        _add_column(connection, columns, "fecha_especial_nombre", "TEXT DEFAULT ''")
        _add_column(connection, columns, "prioridad", "TEXT DEFAULT ''")
        _add_column(connection, columns, "caption", "TEXT DEFAULT ''")
        _add_column(connection, columns, "cta", "TEXT DEFAULT ''")
        _add_column(connection, columns, "visual_headline", "TEXT DEFAULT ''")
        _add_column(connection, columns, "visual_subtitle", "TEXT DEFAULT ''")
        _add_column(connection, columns, "visual_cta", "TEXT DEFAULT ''")
        _add_column(connection, columns, "strategy_used", "TEXT DEFAULT ''")
        _add_column(connection, columns, "content_provider", "TEXT DEFAULT ''")
        _add_column(connection, columns, "content_model", "TEXT DEFAULT ''")
        _add_column(connection, columns, "generation_status", "TEXT DEFAULT 'generated'")
        _add_column(connection, columns, "producto_nombre", "TEXT DEFAULT ''")
        _add_column(connection, columns, "producto_id", "TEXT DEFAULT ''")
        _add_column(connection, columns, "categoria_nombre", "TEXT DEFAULT ''")
        _add_column(connection, columns, "imagen_producto_path", "TEXT DEFAULT ''")
        _add_column(connection, columns, "origen_contenido", "TEXT DEFAULT 'generico'")
        _add_column(connection, columns, "updated_at", "TEXT DEFAULT ''")
        connection.execute(
            """
            UPDATE marketing_posts
            SET caption = texto
            WHERE COALESCE(caption, '') = '' AND COALESCE(texto, '') != ''
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS business_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                nombre_comercial TEXT NOT NULL DEFAULT '',
                rubro TEXT NOT NULL DEFAULT '',
                descripcion TEXT NOT NULL DEFAULT '',
                publico_objetivo TEXT NOT NULL DEFAULT '',
                ciudad_zona TEXT NOT NULL DEFAULT '',
                propuesta_valor TEXT NOT NULL DEFAULT '',
                productos_servicios_principales TEXT NOT NULL DEFAULT '',
                objetivo_comercial TEXT NOT NULL DEFAULT '',
                tono_comunicacion TEXT NOT NULL DEFAULT 'cercano y profesional',
                instagram TEXT NOT NULL DEFAULT '',
                whatsapp TEXT NOT NULL DEFAULT '',
                sitio_web TEXT NOT NULL DEFAULT '',
                colores_marca TEXT NOT NULL DEFAULT '',
                logo_path TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS catalog_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT NOT NULL DEFAULT '',
                categoria TEXT NOT NULL DEFAULT '',
                precio REAL,
                stock REAL,
                item_type TEXT NOT NULL DEFAULT 'producto',
                featured INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                image_path TEXT NOT NULL DEFAULT '',
                deleted_at TEXT DEFAULT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
