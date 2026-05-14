from __future__ import annotations
from pathlib import Path
import re
from uuid import uuid4

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont

from services.template_styles import get_template_style


FORMATS = {
    "whatsapp_estado": ("story", (1080, 1920)),
    "instagram_story": ("story", (1080, 1920)),
    "instagram_feed": ("feed_vertical", (1080, 1350)),
    "instagram_feed_cuadrado": ("feed_cuadrado", (1080, 1080)),
}

FORMAT_SIZES = {
    "story": {
        "margin": 72,
        "panel_padding": 54,
        "eyebrow": 30,
        "title": 74,
        "body": 38,
        "meta": 26,
        "footer": 24,
        "logo": 108,
        "cta_height": 124,
    },
    "feed_vertical": {
        "margin": 58,
        "panel_padding": 44,
        "eyebrow": 24,
        "title": 58,
        "body": 32,
        "meta": 24,
        "footer": 22,
        "logo": 88,
        "cta_height": 104,
    },
    "feed_cuadrado": {
        "margin": 54,
        "panel_padding": 40,
        "eyebrow": 22,
        "title": 50,
        "body": 29,
        "meta": 22,
        "footer": 20,
        "logo": 82,
        "cta_height": 96,
    },
}


def _hex_color(value: str, fallback: str) -> tuple[int, int, int]:
    try:
        return ImageColor.getrgb(value)
    except ValueError:
        return ImageColor.getrgb(fallback)


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def _font_path(font_family: str, bold: bool) -> str:
    suffix = "-Bold.ttf" if bold else ".ttf"
    return f"{font_family}{suffix}"


def _load_font(font_family: str, size: int, bold: bool = True) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype(_font_path(font_family, bold), size=size)
    except OSError:
        try:
            fallback = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
            return ImageFont.truetype(fallback, size=size)
        except OSError:
            return ImageFont.load_default()


def _mix(color_a: tuple[int, int, int], color_b: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(
        int(color_a[index] + (color_b[index] - color_a[index]) * factor)
        for index in range(3)
    )


def _with_alpha(color: tuple[int, int, int], alpha: int) -> tuple[int, int, int, int]:
    return color + (alpha,)


def _background_with_gradient(size: tuple[int, int], top_color: tuple[int, int, int], bottom_color: tuple[int, int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGBA", size)
    pixels = image.load()
    for y in range(height):
        factor = y / max(height - 1, 1)
        row_color = _mix(top_color, bottom_color, factor)
        for x in range(width):
            pixels[x, y] = row_color + (255,)
    return image


def _draw_radial_glow(base: Image.Image, center: tuple[int, int], radius: int, color: tuple[int, int, int], alpha: int) -> None:
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    x, y = center
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=_with_alpha(color, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=radius // 3))
    base.alpha_composite(glow)


def _maybe_apply_background_asset(base: Image.Image, backgrounds_dir: str, post_type: str) -> None:
    backgrounds_path = Path(backgrounds_dir)
    if not backgrounds_path.exists():
        return

    candidates = []
    for extension in ("png", "jpg", "jpeg", "webp"):
        candidates.extend(backgrounds_path.glob(f"{post_type}*.{extension}"))
        candidates.extend(backgrounds_path.glob(f"generic*.{extension}"))

    if not candidates:
        return

    asset = Image.open(candidates[0]).convert("RGBA")
    asset = asset.resize(base.size)
    asset.putalpha(76)
    base.alpha_composite(asset)


def _wrap_text_to_width(
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    draw: ImageDraw.ImageDraw,
    max_lines: int,
) -> str:
    words = text.split()
    if not words:
        return ""

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1].rstrip(". ")
        while last:
            candidate = f"{last}..."
            bbox = draw.textbbox((0, 0), candidate, font=font)
            if (bbox[2] - bbox[0]) <= max_width:
                lines[-1] = candidate
                break
            last = " ".join(last.split(" ")[:-1])
        if not last:
            lines[-1] = "..."
    return "\n".join(lines)


def _fit_text(
    text: str,
    font_family: str,
    initial_size: int,
    min_size: int,
    max_width: int,
    max_lines: int,
    draw: ImageDraw.ImageDraw,
    bold: bool = True,
) -> tuple[ImageFont.ImageFont, str]:
    font_size = initial_size
    while font_size >= min_size:
        font = _load_font(font_family, font_size, bold=bold)
        wrapped = _wrap_text_to_width(text, font, max_width, draw, max_lines)
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=max(10, font_size // 4))
        if (bbox[2] - bbox[0]) <= max_width and wrapped.count("\n") + 1 <= max_lines:
            return font, wrapped
        font_size -= 2
    fallback = _load_font(font_family, min_size, bold=bold)
    return fallback, _wrap_text_to_width(text, fallback, max_width, draw, max_lines)


def _draw_logo(base: Image.Image, logo_path: str, x: int, y: int, logo_size: int) -> None:
    if not logo_path:
        return
    path = Path(logo_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        return

    try:
        logo = Image.open(path).convert("RGBA")
    except OSError:
        return

    logo.thumbnail((logo_size, logo_size))
    holder = Image.new("RGBA", (logo_size, logo_size), (0, 0, 0, 0))
    offset_x = (logo_size - logo.width) // 2
    offset_y = (logo_size - logo.height) // 2
    holder.alpha_composite(logo, (offset_x, offset_y))
    base.alpha_composite(holder, (x, y))


def _channel_to_format(channel: str) -> tuple[str, tuple[int, int]]:
    return FORMATS.get(channel, FORMATS["instagram_story"])


def _resolve_output_dir(generated_dir: str) -> Path:
    output_dir = Path(generated_dir).resolve()
    allowed_root = (Path.cwd() / "static" / "generated").resolve()
    if output_dir != allowed_root:
        try:
            output_dir.relative_to(allowed_root)
        except ValueError:
            output_dir = allowed_root
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _slugify(value: str) -> str:
    sanitized = re.sub(r"[^a-z0-9_]+", "_", value.lower())
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized or "post"


def _build_output_name(post: dict) -> str:
    post_id = post.get("id")
    if post_id:
        channel = _slugify(str(post.get("canal", "canal")))
        post_type = _slugify(str(post.get("tipo", "post")))
        return f"post_{post_id}_{channel}_{post_type}.png"
    return f"{post['fecha']}_{post['canal']}_{uuid4().hex[:8]}.png"


def generate_post_image(post: dict, generated_dir: str, brand_settings: dict) -> str:
    channel = post["canal"]
    format_name, size = _channel_to_format(channel)
    width, height = size
    metrics = FORMAT_SIZES[format_name]
    style = get_template_style(post.get("tipo", "novedad"))

    primary = _hex_color(brand_settings["primary"], "#1D4ED8")
    accent = _hex_color(brand_settings["accent"], "#F59E0B")
    secondary = _hex_color(brand_settings["secondary"], "#0F172A")
    white = (248, 250, 252)
    soft_ink = (15, 23, 42)
    soft_muted = (203, 213, 225)
    font_family = brand_settings.get("font_family", "DejaVuSans")

    if style.accent_mode == "minimal":
        gradient_top = _mix(secondary, white, 0.78)
        gradient_bottom = _mix(primary, white, 0.88)
        panel_fill = _with_alpha((255, 255, 255), 218)
        body_color = soft_ink
        meta_color = (71, 85, 105)
    elif style.accent_mode == "clean":
        gradient_top = _mix(secondary, white, 0.7)
        gradient_bottom = _mix(accent, white, 0.87)
        panel_fill = _with_alpha((255, 255, 255), 228)
        body_color = soft_ink
        meta_color = (51, 65, 85)
    elif style.accent_mode == "bold":
        gradient_top = _mix(secondary, primary, 0.25)
        gradient_bottom = _mix(primary, accent, 0.2)
        panel_fill = _with_alpha((10, 18, 36), 170)
        body_color = white
        meta_color = soft_muted
    elif style.accent_mode == "spotlight":
        gradient_top = _mix(secondary, accent, 0.16)
        gradient_bottom = _mix(secondary, primary, 0.3)
        panel_fill = _with_alpha((255, 255, 255), 208)
        body_color = soft_ink
        meta_color = (71, 85, 105)
    else:
        gradient_top = _mix(secondary, primary, 0.28)
        gradient_bottom = _mix(primary, accent, 0.12)
        panel_fill = _with_alpha((255, 255, 255), 198)
        body_color = white
        meta_color = soft_muted

    base = _background_with_gradient(size, gradient_top, gradient_bottom)
    _draw_radial_glow(base, (width - width // 4, height // 5), width // 4, accent, 90)
    _draw_radial_glow(base, (width // 6, height - height // 5), width // 3, primary, 68)
    _maybe_apply_background_asset(base, brand_settings.get("backgrounds_dir", ""), post.get("tipo", ""))

    overlay = Image.new("RGBA", size, _with_alpha((255, 255, 255), style.overlay_opacity))
    base.alpha_composite(overlay)

    panel = Image.new("RGBA", size, (0, 0, 0, 0))
    panel_draw = ImageDraw.Draw(panel)
    margin = metrics["margin"]
    radius = max(28, margin // 2)
    panel_draw.rounded_rectangle(
        (margin, margin, width - margin, height - margin),
        radius=radius,
        fill=panel_fill,
        outline=_with_alpha(_mix(primary, white, 0.25), 220),
        width=3,
    )
    base.alpha_composite(panel)

    draw = ImageDraw.Draw(base)
    inner_left = margin + metrics["panel_padding"]
    inner_right = width - margin - metrics["panel_padding"]
    max_text_width = inner_right - inner_left
    y = margin + metrics["panel_padding"]

    logo_size = metrics["logo"]
    _draw_logo(base, brand_settings.get("logo_path", ""), inner_right - logo_size, y, logo_size)

    eyebrow_font = _load_font(font_family, metrics["eyebrow"], bold=True)
    eyebrow_fill = accent if style.accent_mode in {"minimal", "clean", "spotlight"} else white
    draw.text((inner_left, y), style.eyebrow, font=eyebrow_font, fill=eyebrow_fill)
    eyebrow_bbox = draw.textbbox((inner_left, y), style.eyebrow, font=eyebrow_font)

    icon_font = _load_font(font_family, max(18, metrics["meta"] - 2), bold=True)
    icon_text = style.icon_text
    icon_bbox = draw.textbbox((0, 0), icon_text, font=icon_font)
    pill_width = (icon_bbox[2] - icon_bbox[0]) + 32
    pill_height = (icon_bbox[3] - icon_bbox[1]) + 18
    pill_left = inner_right - pill_width
    pill_top = y
    draw.rounded_rectangle(
        (pill_left, pill_top, pill_left + pill_width, pill_top + pill_height),
        radius=pill_height // 2,
        fill=_with_alpha(_mix(accent, white, 0.16), 220),
    )
    draw.text((pill_left + 16, pill_top + 7), icon_text, font=icon_font, fill=soft_ink)
    y = eyebrow_bbox[3] + max(22, metrics["panel_padding"] // 2)

    title_text = post["titulo"].upper() if style.title_case == "upper" else post["titulo"]
    title_font, wrapped_title = _fit_text(
        title_text,
        font_family,
        metrics["title"],
        max(32, metrics["title"] - 18),
        max_text_width,
        3 if format_name == "story" else 2,
        draw,
        bold=True,
    )
    draw.multiline_text((inner_left, y), wrapped_title, font=title_font, fill=body_color, spacing=max(12, title_font.size // 5))
    title_bbox = draw.multiline_textbbox((inner_left, y), wrapped_title, font=title_font, spacing=max(12, title_font.size // 5))
    y = title_bbox[3] + max(28, metrics["panel_padding"] // 2)

    body_font, wrapped_body = _fit_text(
        post["texto"],
        font_family,
        metrics["body"],
        max(24, metrics["body"] - 10),
        max_text_width,
        8 if format_name == "story" else 6,
        draw,
        bold=False,
    )
    draw.multiline_text((inner_left, y), wrapped_body, font=body_font, fill=body_color, spacing=max(12, body_font.size // 3))
    body_bbox = draw.multiline_textbbox((inner_left, y), wrapped_body, font=body_font, spacing=max(12, body_font.size // 3))
    y = body_bbox[3] + max(26, metrics["panel_padding"] // 2)

    hashtag_line = post.get("hashtags", "").strip() or "#contenido #marketing"
    hashtag_font, wrapped_hashtags = _fit_text(
        hashtag_line,
        font_family,
        metrics["meta"],
        max(18, metrics["meta"] - 4),
        max_text_width,
        2,
        draw,
        bold=False,
    )
    draw.multiline_text((inner_left, y), wrapped_hashtags, font=hashtag_font, fill=meta_color, spacing=8)
    hashtags_bbox = draw.multiline_textbbox((inner_left, y), wrapped_hashtags, font=hashtag_font, spacing=8)

    cta_height = metrics["cta_height"]
    footer_block_height = max(90, metrics["panel_padding"] + 30)
    cta_top = min(max(hashtags_bbox[3] + 34, y + 34), height - margin - footer_block_height - cta_height - 24)
    cta_bottom = cta_top + cta_height

    cta_fill = accent if style.accent_mode in {"minimal", "clean"} else _mix(accent, white, 0.08)
    cta_text_fill = soft_ink if style.accent_mode in {"minimal", "clean", "spotlight"} else white
    draw.rounded_rectangle(
        (inner_left, cta_top, inner_right, cta_bottom),
        radius=cta_height // 2,
        fill=cta_fill,
    )
    cta_font = _load_font(font_family, metrics["meta"] + 2, bold=True)
    cta_text = style.cta
    cta_bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
    cta_text_x = inner_left + 32
    cta_text_y = cta_top + (cta_height - (cta_bbox[3] - cta_bbox[1])) // 2 - 2
    draw.text((cta_text_x, cta_text_y), cta_text, font=cta_font, fill=cta_text_fill)

    arrow_radius = max(22, metrics["meta"] + 4)
    arrow_center_x = inner_right - 34 - arrow_radius
    arrow_center_y = cta_top + cta_height // 2
    draw.ellipse(
        (
            arrow_center_x - arrow_radius,
            arrow_center_y - arrow_radius,
            arrow_center_x + arrow_radius,
            arrow_center_y + arrow_radius,
        ),
        fill=_mix(primary, white, 0.12) if style.accent_mode in {"minimal", "clean"} else _with_alpha(white, 40),
    )
    draw.line(
        (
            arrow_center_x - 10,
            arrow_center_y,
            arrow_center_x + 8,
            arrow_center_y,
        ),
        fill=cta_text_fill,
        width=5,
    )
    draw.line(
        (
            arrow_center_x + 2,
            arrow_center_y - 8,
            arrow_center_x + 12,
            arrow_center_y,
            arrow_center_x + 2,
            arrow_center_y + 8,
        ),
        fill=cta_text_fill,
        width=5,
        joint="curve",
    )

    footer_y = height - margin - metrics["panel_padding"] - 36
    footer_text = (
        f"{brand_settings['name']}   "
        f"{brand_settings.get('instagram', '@usuario')}   "
        f"{brand_settings.get('url', 'www.tumarca.com')}"
    )
    footer_font, wrapped_footer = _fit_text(
        footer_text,
        font_family,
        metrics["footer"],
        max(16, metrics["footer"] - 4),
        max_text_width,
        2,
        draw,
        bold=False,
    )
    draw.line((inner_left, footer_y - 18, inner_right, footer_y - 18), fill=_with_alpha(_mix(primary, white, 0.45), 160), width=2)
    draw.multiline_text((inner_left, footer_y), wrapped_footer, font=footer_font, fill=meta_color, spacing=6)
    tone_font = _load_font(font_family, max(16, metrics["footer"] - 2), bold=False)
    tone_text = f"Tono visual: {style.visual_tone}"
    tone_bbox = draw.textbbox((0, 0), tone_text, font=tone_font)
    draw.text((inner_right - (tone_bbox[2] - tone_bbox[0]), footer_y - 44), tone_text, font=tone_font, fill=meta_color)

    output_dir = _resolve_output_dir(generated_dir)
    filename = _build_output_name(post)
    file_path = output_dir / filename
    base.convert("RGB").save(file_path)

    if output_dir.name == "generated":
        return f"generated/{filename}"
    return f"generated/{output_dir.name}/{filename}"
