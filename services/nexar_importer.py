from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path


COMMON_TABLES = ("productos", "categorias", "ventas", "detalle_ventas", "stock")
FORBIDDEN_SQL_TERMS = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "REPLACE")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

PRODUCT_NAME_COLUMNS = ("nombre", "titulo", "descripcion", "producto")
CATEGORY_NAME_COLUMNS = ("nombre", "titulo", "descripcion", "categoria")
PRODUCT_ID_COLUMNS = ("id", "producto_id", "id_producto", "codigo", "sku")
CATEGORY_ID_COLUMNS = ("categoria_id", "id_categoria", "rubro_id", "categoria")
CATEGORY_REF_COLUMNS = ("categoria", "rubro", "linea")
PRICE_COLUMNS = ("precio", "precio_venta", "precio_publico", "precio_final", "importe")
STOCK_COLUMNS = ("stock", "cantidad", "existencia", "disponible")
IMAGE_COLUMNS = ("imagen_path", "imagen", "foto", "image_path", "ruta_imagen", "imagen_url")
SALES_QTY_COLUMNS = ("cantidad", "cantidad_vendida", "unidades", "cant")
SALES_PRODUCT_COLUMNS = ("producto_id", "id_producto", "producto", "codigo_producto")
SALES_TABLES = ("detalle_ventas", "ventas")


def get_readonly_connection(db_path: str) -> sqlite3.Connection | None:
    """Open the external Nexar Comercio database in strict read-only mode."""
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


def _safe_fetchall(
    connection: sqlite3.Connection,
    query: str,
    params: tuple | list | None = None,
) -> list[sqlite3.Row]:
    if not _is_safe_select_query(query):
        print("Consulta rechazada: solo se permiten SELECT en modo read-only.")
        return []

    try:
        return connection.execute(query, params or ()).fetchall()
    except sqlite3.Error as error:
        print(f"Error ejecutando SELECT read-only: {error}")
        return []


def _safe_identifier(name: str) -> str | None:
    if not name or not IDENTIFIER_RE.fullmatch(name):
        return None
    return f'"{name}"'


def _existing_tables(connection: sqlite3.Connection) -> set[str]:
    rows = _safe_fetchall(
        connection,
        "SELECT name FROM sqlite_master WHERE type = 'table'",
    )
    return {row["name"] for row in rows}


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    safe_table = _safe_identifier(table_name)
    if not safe_table:
        return set()

    try:
        rows = connection.execute(f"PRAGMA table_info({safe_table})").fetchall()
    except sqlite3.Error as error:
        print(f"Error leyendo columnas de {table_name}: {error}")
        return set()
    return {row["name"] for row in rows}


def _safe_count(connection: sqlite3.Connection, table_name: str) -> int:
    safe_table = _safe_identifier(table_name)
    if not safe_table:
        return 0
    rows = _safe_fetchall(connection, f"SELECT COUNT(*) AS total FROM {safe_table}")
    if not rows:
        return 0
    return rows[0]["total"]


def table_exists(db_path: str, nombre: str) -> bool:
    connection = get_readonly_connection(db_path)
    if not connection:
        return False
    try:
        return nombre in _existing_tables(connection)
    finally:
        connection.close()


def column_exists(db_path: str, tabla: str, columna: str) -> bool:
    connection = get_readonly_connection(db_path)
    if not connection:
        return False
    try:
        return columna in _table_columns(connection, tabla)
    finally:
        connection.close()


def _pick_first(columns: set[str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def _best_product_name(product: dict, fallback: str = "Producto") -> str:
    for candidate in PRODUCT_NAME_COLUMNS:
        value = product.get(candidate)
        if value:
            return str(value)
    return fallback


def _best_category_name(category: dict, fallback: str = "Categoria") -> str:
    for candidate in CATEGORY_NAME_COLUMNS:
        value = category.get(candidate)
        if value:
            return str(value)
    return fallback


def _best_product_id(product: dict, fallback: str = "") -> str:
    for candidate in PRODUCT_ID_COLUMNS:
        value = product.get(candidate)
        if value is not None and str(value).strip():
            return str(value)
    return fallback


def _resolve_image_path(
    image_value: str | None,
    db_path: str,
) -> str:
    if not image_value:
        return ""

    raw_path = Path(str(image_value)).expanduser()
    candidates = [raw_path]
    if not raw_path.is_absolute():
        db_dir = Path(db_path).resolve().parent
        candidates.append(db_dir / raw_path)

    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())
    return ""


def _load_product_rows(connection: sqlite3.Connection, db_path: str, limit: int) -> list[dict]:
    if "productos" not in _existing_tables(connection):
        return []

    columns = _table_columns(connection, "productos")
    safe_table = _safe_identifier("productos")
    if not safe_table:
        return []

    select_parts = ["*"]
    price_column = _pick_first(columns, PRICE_COLUMNS)
    stock_column = _pick_first(columns, STOCK_COLUMNS)
    image_column = _pick_first(columns, IMAGE_COLUMNS)

    order_parts = []
    if stock_column:
        order_parts.append(f'"{stock_column}" DESC')
    if price_column:
        order_parts.append(f'"{price_column}" DESC')
    order_parts.append("ROWID DESC")

    rows = _safe_fetchall(
        connection,
        f"""
        SELECT {", ".join(select_parts)}
        FROM {safe_table}
        ORDER BY {", ".join(order_parts)}
        LIMIT ?
        """,
        (limit,),
    )

    products: list[dict] = []
    for row in rows:
        item = dict(row)
        item["producto_nombre"] = _best_product_name(item, fallback="Producto")
        item["producto_id"] = _best_product_id(item)
        item["categoria_nombre"] = ""
        category_name_column = _pick_first(columns, CATEGORY_REF_COLUMNS)
        if category_name_column and item.get(category_name_column):
            item["categoria_nombre"] = str(item.get(category_name_column))
        item["precio_valor"] = item.get(price_column) if price_column else None
        item["stock_valor"] = item.get(stock_column) if stock_column else None
        item["imagen_producto_path"] = _resolve_image_path(
            str(item.get(image_column, "") or ""),
            db_path,
        )
        products.append(item)
    return products


def _load_categories_map(connection: sqlite3.Connection) -> dict[str, str]:
    if "categorias" not in _existing_tables(connection):
        return {}

    columns = _table_columns(connection, "categorias")
    safe_table = _safe_identifier("categorias")
    if not safe_table:
        return {}

    id_column = _pick_first(columns, ("id", "categoria_id", "id_categoria"))
    name_column = _pick_first(columns, CATEGORY_NAME_COLUMNS)
    if not id_column or not name_column:
        return {}

    rows = _safe_fetchall(
        connection,
        f'SELECT "{id_column}" AS category_id, "{name_column}" AS category_name FROM {safe_table}',
    )
    return {
        str(row["category_id"]): str(row["category_name"])
        for row in rows
        if row["category_id"] is not None and row["category_name"]
    }


def _attach_category_names(connection: sqlite3.Connection, products: list[dict]) -> list[dict]:
    if not products:
        return []

    categories_map = _load_categories_map(connection)
    if not categories_map:
        return products

    for product in products:
        if product.get("categoria_nombre"):
            continue
        for candidate in CATEGORY_ID_COLUMNS:
            value = product.get(candidate)
            if value is None:
                continue
            category_name = categories_map.get(str(value))
            if category_name:
                product["categoria_nombre"] = category_name
                break
    return products


def _get_products_by_numeric_column(
    db_path: str,
    candidate_columns: tuple[str, ...],
    limit: int,
    descending: bool,
) -> list[dict]:
    connection = get_readonly_connection(db_path)
    if not connection:
        return []

    try:
        if "productos" not in _existing_tables(connection):
            return []

        columns = _table_columns(connection, "productos")
        target_column = _pick_first(columns, candidate_columns)
        safe_table = _safe_identifier("productos")
        if not target_column or not safe_table:
            return []

        direction = "DESC" if descending else "ASC"
        rows = _safe_fetchall(
            connection,
            f"""
            SELECT *
            FROM {safe_table}
            WHERE "{target_column}" IS NOT NULL
            ORDER BY CAST("{target_column}" AS REAL) {direction}, ROWID DESC
            LIMIT ?
            """,
            (limit,),
        )
        products = _load_product_rows_from_rows(connection, db_path, rows)
        return _attach_category_names(connection, products)
    finally:
        connection.close()


def _load_product_rows_from_rows(
    connection: sqlite3.Connection,
    db_path: str,
    rows: list[sqlite3.Row],
) -> list[dict]:
    columns = _table_columns(connection, "productos")
    price_column = _pick_first(columns, PRICE_COLUMNS)
    stock_column = _pick_first(columns, STOCK_COLUMNS)
    image_column = _pick_first(columns, IMAGE_COLUMNS)

    products: list[dict] = []
    for row in rows:
        item = dict(row)
        item["producto_nombre"] = _best_product_name(item, fallback="Producto")
        item["producto_id"] = _best_product_id(item)
        item["categoria_nombre"] = ""
        category_name_column = _pick_first(columns, CATEGORY_REF_COLUMNS)
        if category_name_column and item.get(category_name_column):
            item["categoria_nombre"] = str(item.get(category_name_column))
        item["precio_valor"] = item.get(price_column) if price_column else None
        item["stock_valor"] = item.get(stock_column) if stock_column else None
        item["imagen_producto_path"] = _resolve_image_path(
            str(item.get(image_column, "") or ""),
            db_path,
        )
        products.append(item)
    return products


def get_productos_destacados(db_path: str, limit: int = 10) -> list[dict]:
    connection = get_readonly_connection(db_path)
    if not connection:
        return []

    try:
        products = _load_product_rows(connection, db_path, limit)
        return _attach_category_names(connection, products)
    finally:
        connection.close()


def get_productos_con_stock_alto(db_path: str, limit: int = 10) -> list[dict]:
    return _get_products_by_numeric_column(db_path, STOCK_COLUMNS, limit, descending=True)


def get_categorias(db_path: str, limit: int = 10) -> list[dict]:
    connection = get_readonly_connection(db_path)
    if not connection:
        return []

    try:
        if "categorias" not in _existing_tables(connection):
            return []

        columns = _table_columns(connection, "categorias")
        safe_table = _safe_identifier("categorias")
        if not safe_table:
            return []

        name_column = _pick_first(columns, CATEGORY_NAME_COLUMNS)
        if not name_column:
            return []

        rows = _safe_fetchall(
            connection,
            f"""
            SELECT *
            FROM {safe_table}
            ORDER BY ROWID DESC
            LIMIT ?
            """,
            (limit,),
        )
        categories: list[dict] = []
        for row in rows:
            item = dict(row)
            item["categoria_nombre"] = _best_category_name(item, fallback="Categoria")
            categories.append(item)
        return categories
    finally:
        connection.close()


def _ventas_from_detail(
    connection: sqlite3.Connection,
    db_path: str,
    limit: int,
    descending: bool,
) -> list[dict]:
    if "detalle_ventas" not in _existing_tables(connection):
        return []

    detail_columns = _table_columns(connection, "detalle_ventas")
    product_ref = _pick_first(detail_columns, SALES_PRODUCT_COLUMNS)
    qty_column = _pick_first(detail_columns, SALES_QTY_COLUMNS)
    if not product_ref or not qty_column:
        return []

    product_columns = _table_columns(connection, "productos")
    safe_detail = _safe_identifier("detalle_ventas")
    safe_products = _safe_identifier("productos")
    if not safe_detail or not safe_products:
        return []

    product_id_column = _pick_first(product_columns, PRODUCT_ID_COLUMNS)
    product_name_column = _pick_first(product_columns, PRODUCT_NAME_COLUMNS)
    price_column = _pick_first(product_columns, PRICE_COLUMNS)
    stock_column = _pick_first(product_columns, STOCK_COLUMNS)
    image_column = _pick_first(product_columns, IMAGE_COLUMNS)
    category_name_column = _pick_first(product_columns, CATEGORY_REF_COLUMNS)

    order_direction = "DESC" if descending else "ASC"

    if product_id_column and product_name_column:
        rows = _safe_fetchall(
            connection,
            f"""
            SELECT
                p.*,
                SUM(CAST(d."{qty_column}" AS REAL)) AS total_vendido
            FROM {safe_detail} d
            JOIN {safe_products} p
                ON p."{product_id_column}" = d."{product_ref}"
            GROUP BY p."{product_id_column}"
            ORDER BY total_vendido {order_direction}
            LIMIT ?
            """,
            (limit,),
        )
        products = []
        for row in rows:
            item = dict(row)
            item["producto_nombre"] = _best_product_name(item, fallback="Producto")
            item["producto_id"] = _best_product_id(item)
            item["categoria_nombre"] = str(item.get(category_name_column) or "")
            item["precio_valor"] = item.get(price_column) if price_column else None
            item["stock_valor"] = item.get(stock_column) if stock_column else None
            item["imagen_producto_path"] = _resolve_image_path(
                str(item.get(image_column, "") or ""),
                db_path,
            )
            products.append(item)
        return _attach_category_names(connection, products)

    rows = _safe_fetchall(
        connection,
        f"""
        SELECT
            d."{product_ref}" AS producto_referencia,
            SUM(CAST(d."{qty_column}" AS REAL)) AS total_vendido
        FROM {safe_detail} d
        GROUP BY d."{product_ref}"
        ORDER BY total_vendido {order_direction}
        LIMIT ?
        """,
        (limit,),
    )
    return [
        {
            "producto_id": str(row["producto_referencia"]),
            "producto_nombre": f"Producto {row['producto_referencia']}",
            "categoria_nombre": "",
            "precio_valor": None,
            "stock_valor": None,
            "imagen_producto_path": "",
            "total_vendido": row["total_vendido"],
        }
        for row in rows
        if row["producto_referencia"] is not None
    ]


def _ventas_from_products(
    connection: sqlite3.Connection,
    db_path: str,
    limit: int,
    descending: bool,
) -> list[dict]:
    if "productos" not in _existing_tables(connection):
        return []

    columns = _table_columns(connection, "productos")
    qty_column = _pick_first(columns, SALES_QTY_COLUMNS)
    safe_table = _safe_identifier("productos")
    if not qty_column or not safe_table:
        return []

    order_direction = "DESC" if descending else "ASC"
    rows = _safe_fetchall(
        connection,
        f"""
        SELECT *
        FROM {safe_table}
        WHERE "{qty_column}" IS NOT NULL
        ORDER BY CAST("{qty_column}" AS REAL) {order_direction}, ROWID DESC
        LIMIT ?
        """,
        (limit,),
    )
    products = _load_product_rows_from_rows(connection, db_path, rows)
    for product in products:
        product["total_vendido"] = product.get(qty_column)
    return _attach_category_names(connection, products)


def get_productos_mas_vendidos(db_path: str, limit: int = 10) -> list[dict]:
    connection = get_readonly_connection(db_path)
    if not connection:
        return []

    try:
        products = _ventas_from_detail(connection, db_path, limit, descending=True)
        if products:
            return products
        return _ventas_from_products(connection, db_path, limit, descending=True)
    finally:
        connection.close()


def get_productos_bajo_movimiento(db_path: str, limit: int = 10) -> list[dict]:
    connection = get_readonly_connection(db_path)
    if not connection:
        return []

    try:
        products = _ventas_from_detail(connection, db_path, limit, descending=False)
        if products:
            return products
        return _ventas_from_products(connection, db_path, limit, descending=False)
    finally:
        connection.close()


def load_external_context(db_path: str) -> dict:
    empty_context = {
        "available": False,
        "tables": [],
        "productos": [],
        "categorias": [],
        "ventas_resumen": {},
        "productos_destacados": [],
        "productos_stock_alto": [],
        "productos_bajo_movimiento": [],
        "productos_mas_vendidos": [],
    }

    connection = get_readonly_connection(db_path)
    if not connection:
        return empty_context

    try:
        tables = _existing_tables(connection)
        context = {
            "available": True,
            "tables": sorted(tables),
            "productos": [],
            "categorias": [],
            "ventas_resumen": {},
            "productos_destacados": [],
            "productos_stock_alto": [],
            "productos_bajo_movimiento": [],
            "productos_mas_vendidos": [],
        }

        context["productos_destacados"] = _attach_category_names(
            connection,
            _load_product_rows(connection, db_path, 10),
        )
        context["productos"] = context["productos_destacados"]
        context["categorias"] = get_categorias(db_path, limit=10)
        context["productos_stock_alto"] = get_productos_con_stock_alto(db_path, limit=10)
        context["productos_bajo_movimiento"] = get_productos_bajo_movimiento(db_path, limit=10)
        context["productos_mas_vendidos"] = get_productos_mas_vendidos(db_path, limit=10)
        context["ventas_resumen"] = {
            "ventas_total": _safe_count(connection, "ventas") if "ventas" in tables else 0,
            "detalle_total": _safe_count(connection, "detalle_ventas") if "detalle_ventas" in tables else 0,
        }
        return context
    except sqlite3.Error:
        return empty_context
    finally:
        connection.close()


def detect_common_tables(db_path: str) -> dict[str, bool]:
    context = load_external_context(db_path)
    table_set = set(context["tables"])
    return {table_name: table_name in table_set for table_name in COMMON_TABLES}
