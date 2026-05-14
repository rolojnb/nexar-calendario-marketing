from __future__ import annotations

import sqlite3
from pathlib import Path


def get_connection(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


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
                cta TEXT DEFAULT '',
                imagen_path TEXT DEFAULT '',
                producto_nombre TEXT DEFAULT '',
                producto_id TEXT DEFAULT '',
                categoria_nombre TEXT DEFAULT '',
                imagen_producto_path TEXT DEFAULT '',
                origen_contenido TEXT DEFAULT 'generico',
                fecha_especial_nombre TEXT DEFAULT '',
                prioridad TEXT DEFAULT '',
                estado TEXT DEFAULT 'borrador',
                created_at TEXT NOT NULL
            )
            """
        )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(marketing_posts)").fetchall()
        }
        if "fecha_especial_nombre" not in columns:
            connection.execute(
                "ALTER TABLE marketing_posts ADD COLUMN fecha_especial_nombre TEXT DEFAULT ''"
            )
        if "prioridad" not in columns:
            connection.execute(
                "ALTER TABLE marketing_posts ADD COLUMN prioridad TEXT DEFAULT ''"
            )
        if "cta" not in columns:
            connection.execute(
                "ALTER TABLE marketing_posts ADD COLUMN cta TEXT DEFAULT ''"
            )
        if "producto_nombre" not in columns:
            connection.execute(
                "ALTER TABLE marketing_posts ADD COLUMN producto_nombre TEXT DEFAULT ''"
            )
        if "producto_id" not in columns:
            connection.execute(
                "ALTER TABLE marketing_posts ADD COLUMN producto_id TEXT DEFAULT ''"
            )
        if "categoria_nombre" not in columns:
            connection.execute(
                "ALTER TABLE marketing_posts ADD COLUMN categoria_nombre TEXT DEFAULT ''"
            )
        if "imagen_producto_path" not in columns:
            connection.execute(
                "ALTER TABLE marketing_posts ADD COLUMN imagen_producto_path TEXT DEFAULT ''"
            )
        if "origen_contenido" not in columns:
            connection.execute(
                "ALTER TABLE marketing_posts ADD COLUMN origen_contenido TEXT DEFAULT 'generico'"
            )
        connection.commit()
