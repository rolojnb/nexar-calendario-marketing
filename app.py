from __future__ import annotations

from datetime import date, datetime

from flask import Flask, abort, flash, redirect, render_template, request, send_file, url_for

from config import Config
from database import init_db
from services.calendario import (
    build_calendar_matrix,
    generate_month_content,
    generate_month_images,
    get_month_posts,
    get_post_by_id,
    month_bounds,
    regenerate_post_image,
)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    init_db(app.config["DATABASE_PATH"])

    @app.route("/")
    def index():
        return redirect(url_for("calendar_view"))

    @app.route("/calendario")
    def calendar_view():
        month_str = request.args.get("mes") or request.args.get("month") or date.today().strftime("%Y-%m")
        start_date, _ = month_bounds(month_str)
        posts = get_month_posts(app.config["DATABASE_PATH"], month_str)
        calendar_weeks = build_calendar_matrix(start_date.year, start_date.month, posts)

        return render_template(
            "calendario.html",
            selected_month=month_str,
            calendar_weeks=calendar_weeks,
            brand_name=app.config["BRAND_NAME"],
            external_status=app.config["EXTERNAL_SOURCE_STATUS"],
        )

    @app.post("/calendario/generar-mes")
    def generate_calendar():
        month_str = request.form.get("mes") or request.form.get("month") or date.today().strftime("%Y-%m")
        generated = generate_month_content(
            db_path=app.config["DATABASE_PATH"],
            month_str=month_str,
            generated_dir=app.config["GENERATED_DIR"],
            brand_settings={
                "name": app.config["BRAND_NAME"],
                "primary": app.config["BRAND_PRIMARY"],
                "secondary": app.config["BRAND_SECONDARY"],
                "accent": app.config["BRAND_ACCENT"],
                "font_family": app.config["BRAND_FONT_FAMILY"],
                "instagram": app.config["BRAND_INSTAGRAM"],
                "url": app.config["BRAND_URL"],
                "logo_path": app.config["BRAND_LOGO_PATH"],
                "backgrounds_dir": app.config["BRAND_BACKGROUNDS_DIR"],
            },
            external_db_path=app.config["NEXAR_COMERCIO_DB"],
            data_source=app.config["DATA_SOURCE"],
            csv_path=app.config["CSV_DATA_SOURCE_PATH"],
        )
        flash(f"Se generaron {generated} publicaciones para {month_str}.", "success")
        return redirect(url_for("calendar_view", mes=month_str))

    @app.post("/calendario/generar-imagenes-mes")
    def generate_month_images_route():
        month_str = request.form.get("mes") or date.today().strftime("%Y-%m")
        regenerate = (request.form.get("regenerar", "false").lower() == "true")
        results = generate_month_images(
            db_path=app.config["DATABASE_PATH"],
            month_str=month_str,
            generated_dir=app.config["GENERATED_DIR"],
            brand_settings={
                "name": app.config["BRAND_NAME"],
                "primary": app.config["BRAND_PRIMARY"],
                "secondary": app.config["BRAND_SECONDARY"],
                "accent": app.config["BRAND_ACCENT"],
                "font_family": app.config["BRAND_FONT_FAMILY"],
                "instagram": app.config["BRAND_INSTAGRAM"],
                "url": app.config["BRAND_URL"],
                "logo_path": app.config["BRAND_LOGO_PATH"],
                "backgrounds_dir": app.config["BRAND_BACKGROUNDS_DIR"],
            },
            regenerate=regenerate,
        )
        flash(
            (
                f"Imágenes del mes {month_str}: "
                f"{results['generated']} generadas, "
                f"{results['skipped']} omitidas, "
                f"{results['errors']} con error."
            ),
            "success" if results["errors"] == 0 else "error",
        )
        return redirect(url_for("calendar_view", mes=month_str))

    @app.route("/post/<int:post_id>")
    def preview_post(post_id: int):
        post = get_post_by_id(app.config["DATABASE_PATH"], post_id)
        if not post:
            flash("La publicación no existe.", "error")
            return redirect(url_for("calendar_view"))
        return render_template(
            "preview_post.html",
            post=post,
            brand_name=app.config["BRAND_NAME"],
            selected_month=datetime.fromisoformat(post["fecha"]).strftime("%Y-%m"),
        )

    @app.route("/post/<int:post_id>/imagen-producto")
    def preview_product_image(post_id: int):
        post = get_post_by_id(app.config["DATABASE_PATH"], post_id)
        if not post or not post.get("imagen_producto_path"):
            abort(404)
        image_path = post["imagen_producto_path"]
        if not image_path:
            abort(404)
        try:
            return send_file(image_path)
        except FileNotFoundError:
            abort(404)

    @app.post("/post/<int:post_id>/generar-imagen")
    def generate_post_image_route(post_id: int):
        image_path = regenerate_post_image(
            db_path=app.config["DATABASE_PATH"],
            post_id=post_id,
            generated_dir=app.config["GENERATED_DIR"],
            brand_settings={
                "name": app.config["BRAND_NAME"],
                "primary": app.config["BRAND_PRIMARY"],
                "secondary": app.config["BRAND_SECONDARY"],
                "accent": app.config["BRAND_ACCENT"],
                "font_family": app.config["BRAND_FONT_FAMILY"],
                "instagram": app.config["BRAND_INSTAGRAM"],
                "url": app.config["BRAND_URL"],
                "logo_path": app.config["BRAND_LOGO_PATH"],
                "backgrounds_dir": app.config["BRAND_BACKGROUNDS_DIR"],
            },
        )
        if not image_path:
            flash("No se pudo generar la imagen para la publicación.", "error")
            return redirect(url_for("calendar_view"))

        flash("Imagen generada correctamente.", "success")
        return redirect(url_for("preview_post", post_id=post_id))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
