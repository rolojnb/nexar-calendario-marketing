from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from pathlib import Path

from database import get_connection
from services.data_sources import load_business_context
from services.fechas_especiales import obtener_fecha_especial
from services.generador_imagenes import generate_post_image
from services.generador_posts import generate_month_posts
from services.marketing_engine import build_marketing_brief, generate_content_from_brief


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


def regenerate_post_content(
    db_path: str,
    post_id: int,
    generated_dir: str,
    brand_settings: dict,
    external_db_path: str,
    data_source: str = "manual",
    csv_path: str = "",
) -> bool:
    post = get_post_by_id(db_path, post_id)
    if not post:
        return False

    current_date = datetime.fromisoformat(post["fecha"]).date()
    business_context = load_business_context(
        source=data_source,
        nexar_comercio_db_path=external_db_path,
        manual_db_path=db_path,
        csv_path=csv_path,
    )
    brief, plan = build_marketing_brief(
        current_date=current_date,
        brand_name=brand_settings["name"],
        channel=post["canal"],
        context=business_context,
        slot_index=max(post_id - 1, 0),
    )
    generated = generate_content_from_brief(brief)
    updated_at = datetime.now(timezone.utc).isoformat()
    post_updates = {
        **post,
        "tipo": plan.content_type,
        "titulo": generated.title,
        "texto": generated.public_text(),
        "caption": generated.caption,
        "hashtags": generated.hashtags_text(),
        "cta": generated.cta,
        "visual_headline": generated.visual_headline,
        "visual_subtitle": generated.visual_subtitle,
        "visual_cta": generated.visual_cta,
        "strategy_used": generated.strategy_used,
        "content_provider": generated.provider,
        "content_model": generated.model,
        "generation_status": "generated",
        "producto_nombre": plan.product.nombre if plan.product else "",
        "producto_id": plan.product.producto_id if plan.product else "",
        "categoria_nombre": plan.product.categoria if plan.product else plan.category,
        "imagen_producto_path": plan.product.imagen_path if plan.product else "",
        "origen_contenido": plan.source,
        "fecha_especial_nombre": plan.special_date_name,
        "prioridad": plan.priority,
        "estado": "listo",
        "updated_at": updated_at,
    }
    image_path = generate_post_image(
        post_updates,
        _month_generated_dir(generated_dir, current_date.strftime("%Y-%m")),
        brand_settings,
    )

    with get_connection(db_path) as connection:
        connection.execute(
            """
            UPDATE marketing_posts
            SET tipo = ?, titulo = ?, texto = ?, caption = ?, hashtags = ?, cta = ?,
                visual_headline = ?, visual_subtitle = ?, visual_cta = ?,
                strategy_used = ?, content_provider = ?, content_model = ?,
                generation_status = ?, imagen_path = ?, producto_nombre = ?,
                producto_id = ?, categoria_nombre = ?, imagen_producto_path = ?,
                origen_contenido = ?, fecha_especial_nombre = ?, prioridad = ?,
                estado = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                post_updates["tipo"],
                post_updates["titulo"],
                post_updates["texto"],
                post_updates["caption"],
                post_updates["hashtags"],
                post_updates["cta"],
                post_updates["visual_headline"],
                post_updates["visual_subtitle"],
                post_updates["visual_cta"],
                post_updates["strategy_used"],
                post_updates["content_provider"],
                post_updates["content_model"],
                post_updates["generation_status"],
                image_path,
                post_updates["producto_nombre"],
                post_updates["producto_id"],
                post_updates["categoria_nombre"],
                post_updates["imagen_producto_path"],
                post_updates["origen_contenido"],
                post_updates["fecha_especial_nombre"],
                post_updates["prioridad"],
                post_updates["estado"],
                updated_at,
                post_id,
            ),
        )
        connection.commit()
    return True


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
    data_source: str = "manual",
    csv_path: str = "",
) -> int:
    start_date, end_date = month_bounds(month_str)
    business_context = load_business_context(
        source=data_source,
        nexar_comercio_db_path=external_db_path,
        manual_db_path=db_path,
        csv_path=csv_path,
    )
    posts = generate_month_posts(
        year=start_date.year,
        month=start_date.month,
        brand_name=brand_settings["name"],
        external_context=business_context,
    )

    created_at = datetime.now(timezone.utc).isoformat()
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
                    fecha, canal, tipo, titulo, texto, caption, hashtags, cta,
                    visual_headline, visual_subtitle, visual_cta, strategy_used,
                    content_provider, content_model, generation_status,
                    imagen_path, producto_nombre, producto_id, categoria_nombre,
                    imagen_producto_path, origen_contenido, fecha_especial_nombre,
                    prioridad, estado, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post["fecha"],
                    post["canal"],
                    post["tipo"],
                    post["titulo"],
                    post["texto"],
                    post.get("caption", post["texto"]),
                    post["hashtags"],
                    post.get("cta", ""),
                    post.get("visual_headline", post["titulo"]),
                    post.get("visual_subtitle", ""),
                    post.get("visual_cta", post.get("cta", "")),
                    post.get("strategy_used", ""),
                    post.get("content_provider", "deterministic"),
                    post.get("content_model", "local-rules-v1"),
                    post.get("generation_status", "generated"),
                    "",
                    post.get("producto_nombre", ""),
                    post.get("producto_id", ""),
                    post.get("categoria_nombre", ""),
                    post.get("imagen_producto_path", ""),
                    post.get("origen_contenido", "generico"),
                    post.get("fecha_especial_nombre", ""),
                    post.get("prioridad", ""),
                    post["estado"],
                    created_at,
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
