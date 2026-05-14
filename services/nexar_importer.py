from __future__ import annotations

import os
import sqlite3


COMMON_TABLES = ("productos", "categorias", "ventas", "detalle_ventas")
FORBIDDEN_SQL_TERMS = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "REPLACE")


def get_readonly_connection(db_path: str) -> sqlite3.Connection | None:
    """Open the external Nexar Comercio database in strict read-only mode.

    This module is read-only by design and must never modify Nexar Comercio.
    SQLite will reject write attempts because the URI is opened with mode=ro.
    """
    if not db_path or not os.path.exists(db_path):
        print(f"DB no encontrada: {db_path}")
        return None

    try:
        connection = sqlite3.connect(
            f"file:{db_path}?mode=ro",
            uri=True,
        )
        connection.row_factory = sqlite3.Row
        return connection
    except Exception as error:
        print(f"Error abriendo DB read-only: {error}")
        return None


def _is_safe_select_query(query: str) -> bool:
    normalized_query = " ".join(query.upper().split())
    if not normalized_query.startswith("SELECT"):
        return False
    return not any(term in normalized_query for term in FORBIDDEN_SQL_TERMS)


def _existing_tables(connection: sqlite3.Connection) -> set[str]:
    rows = _safe_fetchall(
        connection,
        "SELECT name FROM sqlite_master WHERE type = 'table'",
    )
    return {row["name"] for row in rows}


def _safe_fetchall(connection: sqlite3.Connection, query: str) -> list[sqlite3.Row]:
    if not _is_safe_select_query(query):
        print("Consulta rechazada: solo se permiten SELECT en modo read-only.")
        return []

    try:
        return connection.execute(query).fetchall()
    except sqlite3.Error as error:
        print(f"Error ejecutando SELECT read-only: {error}")
        return []


def _safe_count(connection: sqlite3.Connection, table_name: str) -> int:
    rows = _safe_fetchall(connection, f"SELECT COUNT(*) AS total FROM {table_name}")
    if not rows:
        return 0
    return rows[0]["total"]


def load_external_context(db_path: str) -> dict:
    empty_context = {
        "available": False,
        "tables": [],
        "productos": [],
        "categorias": [],
        "ventas_resumen": {},
    }

    connection = get_readonly_connection(db_path)
    if not connection:
        return empty_context

    try:
        # La conexión externa es estrictamente de lectura.
        # Este módulo NO debe modificar Nexar Comercio bajo ninguna circunstancia.
        # SQLite bloqueará cualquier intento de escritura por el uso de mode=ro.
        tables = _existing_tables(connection)
        context = {"available": True, "tables": sorted(tables)}

        productos = []
        if "productos" in tables:
            productos = _safe_fetchall(
                connection,
                """
                SELECT *
                FROM productos
                ORDER BY ROWID DESC
                LIMIT 8
                """,
            )

        categorias = []
        if "categorias" in tables:
            categorias = _safe_fetchall(
                connection,
                """
                SELECT *
                FROM categorias
                ORDER BY ROWID DESC
                LIMIT 8
                """,
            )

        ventas_total = 0
        if "ventas" in tables:
            ventas_total = _safe_count(connection, "ventas")

        detalle_total = 0
        if "detalle_ventas" in tables:
            detalle_total = _safe_count(connection, "detalle_ventas")

        context.update(
            {
                "productos": [dict(row) for row in productos],
                "categorias": [dict(row) for row in categorias],
                "ventas_resumen": {
                    "ventas_total": ventas_total,
                    "detalle_total": detalle_total,
                },
            }
        )
        return context
    except sqlite3.Error:
        return empty_context
    finally:
        connection.close()


def detect_common_tables(db_path: str) -> dict[str, bool]:
    context = load_external_context(db_path)
    table_set = set(context["tables"])
    return {table_name: table_name in table_set for table_name in COMMON_TABLES}
