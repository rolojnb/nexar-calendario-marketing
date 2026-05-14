from __future__ import annotations

import calendar
from datetime import date, datetime
from pathlib import Path

from database import get_connection
from services.fechas_especiales import obtener_fecha_especial
from services.generador_imagenes import generate_post_image
from services.generador_posts import generate_month_posts
from services.nexar_importer import load_external_context


def month_bounds(month_str: str) -> tuple[date, date]:
    start_date = datetime.strptime(f"{month_str}-01", "%Y-%m-%d").date()
    _, last_day = calendar.monthrange(start_date.year, start_date.month)
    return start_date, date(start_date.year, start_date.month, last_day)


def get_month_posts(db_path: str, month_str: str) -> list[dict]:
    start_date, end_date = month_bounds(month_str)
    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM marketing_posts
            WHERE fecha BETWEEN ? AND ?
            ORDER BY fecha, id
            """,
            (start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
        return [dict(row) for row in rows]


def get_post_by_id(db_path: str, post_id: int) -> dict | None:
    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM marketing_posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        return dict(row) if row else None


def _month_generated_dir(generated_dir: str, month_str: str) -> str:
    return str(Path(generated_dir) / month_str)


def regenerate_post_image(
    db_path: str,
    post_id: int,
    generated_dir: str,
    brand_settings: dict,
) -> str | None:
    post = get_post_by_id(db_path, post_id)
    if not post:
        return None

    month_str = datetime.fromisoformat(post["fecha"]).strftime("%Y-%m")
    image_path = generate_post_image(
        post,
        _month_generated_dir(generated_dir, month_str),
        brand_settings,
    )
    with get_connection(db_path) as connection:
        connection.execute(
            """
            UPDATE marketing_posts
            SET imagen_path = ?
            WHERE id = ?
            """,
            (image_path, post_id),
        )
        connection.commit()
    return image_path


def generate_month_images(
    db_path: str,
    month_str: str,
    generated_dir: str,
    brand_settings: dict,
    regenerate: bool = False,
) -> dict[str, int]:
    posts = get_month_posts(db_path, month_str)
    month_dir = _month_generated_dir(generated_dir, month_str)
    results = {"generated": 0, "skipped": 0, "errors": 0}

    print(f"[calendario] Inicio de generación masiva para {month_str}. regenerar={regenerate}")
    for post in posts:
        if post.get("imagen_path") and not regenerate:
            results["skipped"] += 1
            print(f"[calendario] Post omitido {post['id']}: ya tiene imagen.")
            continue

        try:
            image_path = generate_post_image(post, month_dir, brand_settings)
            with get_connection(db_path) as connection:
                connection.execute(
                    """
                    UPDATE marketing_posts
                    SET imagen_path = ?
                    WHERE id = ?
                    """,
                    (image_path, post["id"]),
                )
                connection.commit()
            results["generated"] += 1
            print(f"[calendario] Post generado {post['id']}: {image_path}")
        except Exception as error:
            results["errors"] += 1
            print(f"[calendario] Error en post {post.get('id')}: {error}")

    return results


def build_calendar_matrix(year: int, month: int, posts: list[dict]) -> list[list[dict]]:
    calendar_rows = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
    posts_by_day: dict[str, list[dict]] = {}

    for post in posts:
        posts_by_day.setdefault(post["fecha"], []).append(post)

    weeks: list[list[dict]] = []
    for week in calendar_rows:
        days: list[dict] = []
        for day in week:
            iso_day = day.isoformat()
            special_date = obtener_fecha_especial(day)
            days.append(
                {
                    "date": day,
                    "is_current_month": day.month == month,
                    "posts": posts_by_day.get(iso_day, []),
                    "special_date": special_date,
                }
            )
        weeks.append(days)
    return weeks


def generate_month_content(
    db_path: str,
    month_str: str,
    generated_dir: str,
    brand_settings: dict,
    external_db_path: str,
) -> int:
    start_date, end_date = month_bounds(month_str)
    external_context = load_external_context(external_db_path)
    posts = generate_month_posts(
        year=start_date.year,
        month=start_date.month,
        brand_name=brand_settings["name"],
        external_context=external_context,
    )

    created_at = datetime.utcnow().isoformat()
    with get_connection(db_path) as connection:
        connection.execute(
            """
            DELETE FROM marketing_posts
            WHERE fecha BETWEEN ? AND ?
            """,
            (start_date.isoformat(), end_date.isoformat()),
        )

        for post in posts:
            cursor = connection.execute(
                """
                INSERT INTO marketing_posts (
                    fecha, canal, tipo, titulo, texto, hashtags,
                    imagen_path, fecha_especial_nombre, prioridad, estado, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post["fecha"],
                    post["canal"],
                    post["tipo"],
                    post["titulo"],
                    post["texto"],
                    post["hashtags"],
                    "",
                    post.get("fecha_especial_nombre", ""),
                    post.get("prioridad", ""),
                    post["estado"],
                    created_at,
                ),
            )
            post_id = cursor.lastrowid
            post_with_id = {**post, "id": post_id}
            image_path = generate_post_image(
                post_with_id,
                _month_generated_dir(generated_dir, month_str),
                brand_settings,
            )
            connection.execute(
                """
                UPDATE marketing_posts
                SET imagen_path = ?
                WHERE id = ?
                """,
                (image_path, post_id),
            )
        connection.commit()

    return len(posts)
