from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

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
from services.manual_store import (
    build_brand_settings,
    create_catalog_item,
    delete_managed_file,
    empty_business_profile,
    get_business_profile,
    get_catalog_item,
    get_selected_data_source,
    list_catalog_items,
    manual_data_available,
    resolve_managed_path,
    set_selected_data_source,
    soft_delete_catalog_item,
    store_image_upload,
    toggle_catalog_item_active,
    update_catalog_item,
    upsert_business_profile,
)


def _base_brand_settings(app: Flask) -> dict[str, str]:
    return {
        "name": app.config["BRAND_NAME"],
        "primary": app.config["BRAND_PRIMARY"],
        "secondary": app.config["BRAND_SECONDARY"],
        "accent": app.config["BRAND_ACCENT"],
        "font_family": app.config["BRAND_FONT_FAMILY"],
        "instagram": app.config["BRAND_INSTAGRAM"],
        "url": app.config["BRAND_URL"],
        "logo_path": app.config["BRAND_LOGO_PATH"],
        "backgrounds_dir": app.config["BRAND_BACKGROUNDS_DIR"],
    }


def _profile_brand_settings(app: Flask) -> tuple[dict[str, str], dict[str, str]]:
    profile = get_business_profile(app.config["DATABASE_PATH"])
    return profile, build_brand_settings(_base_brand_settings(app), profile)


def _selected_source(app: Flask) -> str:
    return get_selected_data_source(app.config["DATABASE_PATH"], app.config["DATA_SOURCE"])


def _source_status(app: Flask, selected_source: str) -> str:
    manual_ready = manual_data_available(app.config["DATABASE_PATH"])
    external_ready = bool(
        app.config["NEXAR_COMERCIO_DB"] and Path(app.config["NEXAR_COMERCIO_DB"]).exists()
    )
    if selected_source == "manual":
        if manual_ready:
            return "Fuente manual activa"
        return "Fuente manual sin datos: cargá tu negocio o el catálogo"
    if external_ready:
        return "Nexar Comercio configurado en modo solo lectura"
    if manual_ready:
        return "Nexar Comercio no disponible: se usará fallback manual"
    return "Nexar Comercio no encontrado o no configurado"


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    init_db(app.config["DATABASE_PATH"])

    @app.context_processor
    def inject_layout_context() -> dict[str, object]:
        _, brand_settings = _profile_brand_settings(app)
        selected_source = _selected_source(app)
        return {
            "brand_name": brand_settings["name"],
            "selected_source": selected_source,
            "source_status": _source_status(app, selected_source),
        }

    @app.route("/")
    def index():
        return redirect(url_for("calendar_view"))

    @app.route("/calendario")
    def calendar_view():
        month_str = request.args.get("mes") or request.args.get("month") or date.today().strftime("%Y-%m")
        start_date, _ = month_bounds(month_str)
        posts = get_month_posts(app.config["DATABASE_PATH"], month_str)
        calendar_weeks = build_calendar_matrix(start_date.year, start_date.month, posts)
        _, brand_settings = _profile_brand_settings(app)
        selected_source = _selected_source(app)

        return render_template(
            "calendario.html",
            selected_month=month_str,
            calendar_weeks=calendar_weeks,
            brand_name=brand_settings["name"],
            external_status=_source_status(app, selected_source),
        )

    @app.route("/mi-negocio", methods=["GET", "POST"])
    def business_view():
        db_path = app.config["DATABASE_PATH"]
        current_profile = get_business_profile(db_path)
        selected_source = _selected_source(app)

        if request.method == "POST":
            next_source = request.form.get("data_source", selected_source)
            uploaded_logo = request.files.get("logo")
            remove_logo = request.form.get("remove_logo") == "1"
            next_logo_path = current_profile.get("logo_path", "")
            new_logo_path = ""

            try:
                if uploaded_logo and uploaded_logo.filename:
                    new_logo_path = store_image_upload(
                        db_path,
                        uploaded_logo,
                        bucket="logos",
                        prefix="logo",
                    )
                    next_logo_path = new_logo_path
                profile = upsert_business_profile(
                    db_path,
                    {
                        **request.form,
                        "logo_path": next_logo_path,
                        "remove_logo": remove_logo,
                    },
                )
                set_selected_data_source(db_path, next_source, app.config["DATA_SOURCE"])
                if remove_logo and current_profile.get("logo_path"):
                    delete_managed_file(db_path, current_profile["logo_path"])
                if new_logo_path and current_profile.get("logo_path") and current_profile["logo_path"] != new_logo_path:
                    delete_managed_file(db_path, current_profile["logo_path"])
                flash("Los datos del negocio se guardaron correctamente.", "success")
                return redirect(url_for("business_view"))
            except ValueError as error:
                if new_logo_path:
                    delete_managed_file(db_path, new_logo_path)
                for message in str(error).splitlines():
                    flash(message, "error")
                current_profile = empty_business_profile()
                current_profile.update({key: value for key, value in request.form.items() if key in current_profile})
                current_profile["logo_path"] = current_profile.get("logo_path") or current_profile.get("logo_path", "")
                selected_source = next_source

        return render_template(
            "business.html",
            profile=current_profile,
            selected_source=selected_source,
            external_db_configured=bool(
                app.config["NEXAR_COMERCIO_DB"] and Path(app.config["NEXAR_COMERCIO_DB"]).exists()
            ),
        )

    @app.route("/mi-negocio/logo")
    def business_logo():
        profile = get_business_profile(app.config["DATABASE_PATH"])
        logo_path = resolve_managed_path(app.config["DATABASE_PATH"], profile.get("logo_path", ""))
        if not logo_path:
            abort(404)
        return send_file(logo_path)

    @app.route("/productos-servicios")
    def catalog_view():
        editing_item = None
        edit_id = request.args.get("edit", type=int)
        if edit_id:
            editing_item = get_catalog_item(app.config["DATABASE_PATH"], edit_id)
        return render_template(
            "catalog.html",
            items=list_catalog_items(app.config["DATABASE_PATH"]),
            editing_item=editing_item,
            empty_item={
                "nombre": "",
                "descripcion": "",
                "categoria": "",
                "precio": "",
                "stock": "",
                "item_type": "producto",
                "featured": False,
                "active": True,
                "image_path": "",
            },
        )

    @app.post("/productos-servicios")
    def catalog_create():
        db_path = app.config["DATABASE_PATH"]
        new_image_path = ""
        try:
            uploaded_image = request.files.get("image")
            if uploaded_image and uploaded_image.filename:
                new_image_path = store_image_upload(
                    db_path,
                    uploaded_image,
                    bucket="catalog",
                    prefix="catalogo",
                )
            create_catalog_item(db_path, request.form, image_path=new_image_path)
            flash("Producto o servicio creado correctamente.", "success")
        except ValueError as error:
            if new_image_path:
                delete_managed_file(db_path, new_image_path)
            for message in str(error).splitlines():
                flash(message, "error")
        return redirect(url_for("catalog_view"))

    @app.post("/productos-servicios/<int:item_id>/editar")
    def catalog_update(item_id: int):
        db_path = app.config["DATABASE_PATH"]
        current_item = get_catalog_item(db_path, item_id)
        if not current_item:
            flash("El producto o servicio no existe.", "error")
            return redirect(url_for("catalog_view"))

        new_image_path = ""
        try:
            uploaded_image = request.files.get("image")
            if uploaded_image and uploaded_image.filename:
                new_image_path = store_image_upload(
                    db_path,
                    uploaded_image,
                    bucket="catalog",
                    prefix="catalogo",
                )
            update_catalog_item(
                db_path,
                item_id,
                request.form,
                image_path=new_image_path or None,
                remove_image=request.form.get("remove_image") == "1",
            )
            if request.form.get("remove_image") == "1" and current_item.get("image_path"):
                delete_managed_file(db_path, current_item["image_path"])
            if new_image_path and current_item.get("image_path") and current_item["image_path"] != new_image_path:
                delete_managed_file(db_path, current_item["image_path"])
            flash("Producto o servicio actualizado correctamente.", "success")
        except ValueError as error:
            if new_image_path:
                delete_managed_file(db_path, new_image_path)
            for message in str(error).splitlines():
                flash(message, "error")
        return redirect(url_for("catalog_view", edit=item_id))

    @app.post("/productos-servicios/<int:item_id>/toggle-activo")
    def catalog_toggle_active(item_id: int):
        try:
            active = toggle_catalog_item_active(app.config["DATABASE_PATH"], item_id)
            flash(
                "Producto o servicio activado." if active else "Producto o servicio desactivado.",
                "success",
            )
        except ValueError as error:
            flash(str(error), "error")
        return redirect(url_for("catalog_view"))

    @app.post("/productos-servicios/<int:item_id>/eliminar")
    def catalog_delete(item_id: int):
        try:
            soft_delete_catalog_item(app.config["DATABASE_PATH"], item_id)
            flash("Producto o servicio eliminado de forma segura.", "success")
        except ValueError as error:
            flash(str(error), "error")
        return redirect(url_for("catalog_view"))

    @app.route("/productos-servicios/<int:item_id>/imagen")
    def catalog_image(item_id: int):
        item = get_catalog_item(app.config["DATABASE_PATH"], item_id)
        if not item:
            abort(404)
        image_path = resolve_managed_path(app.config["DATABASE_PATH"], item.get("image_path", ""))
        if not image_path:
            abort(404)
        return send_file(image_path)

    @app.post("/calendario/generar-mes")
    def generate_calendar():
        month_str = request.form.get("mes") or request.form.get("month") or date.today().strftime("%Y-%m")
        selected_source = _selected_source(app)
        _, brand_settings = _profile_brand_settings(app)
        generated = generate_month_content(
            db_path=app.config["DATABASE_PATH"],
            month_str=month_str,
            generated_dir=app.config["GENERATED_DIR"],
            brand_settings=brand_settings,
            external_db_path=app.config["NEXAR_COMERCIO_DB"],
            data_source=selected_source,
            csv_path=app.config["CSV_DATA_SOURCE_PATH"],
        )
        flash(f"Se generaron {generated} publicaciones para {month_str}.", "success")
        return redirect(url_for("calendar_view", mes=month_str))

    @app.post("/calendario/generar-imagenes-mes")
    def generate_month_images_route():
        month_str = request.form.get("mes") or date.today().strftime("%Y-%m")
        regenerate = request.form.get("regenerar", "false").lower() == "true"
        _, brand_settings = _profile_brand_settings(app)
        results = generate_month_images(
            db_path=app.config["DATABASE_PATH"],
            month_str=month_str,
            generated_dir=app.config["GENERATED_DIR"],
            brand_settings=brand_settings,
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
        _, brand_settings = _profile_brand_settings(app)
        return render_template(
            "preview_post.html",
            post=post,
            brand_name=brand_settings["name"],
            selected_month=datetime.fromisoformat(post["fecha"]).strftime("%Y-%m"),
        )

    @app.route("/post/<int:post_id>/imagen-producto")
    def preview_product_image(post_id: int):
        post = get_post_by_id(app.config["DATABASE_PATH"], post_id)
        if not post or not post.get("imagen_producto_path"):
            abort(404)
        image_path = Path(post["imagen_producto_path"])
        if not image_path.is_absolute():
            image_path = Path.cwd() / image_path
        try:
            return send_file(image_path)
        except FileNotFoundError:
            abort(404)

    @app.post("/post/<int:post_id>/generar-imagen")
    def generate_post_image_route(post_id: int):
        _, brand_settings = _profile_brand_settings(app)
        image_path = regenerate_post_image(
            db_path=app.config["DATABASE_PATH"],
            post_id=post_id,
            generated_dir=app.config["GENERATED_DIR"],
            brand_settings=brand_settings,
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
