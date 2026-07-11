# nexar-calendario-marketing

Aplicación Flask independiente para generar un calendario mensual de contenido para WhatsApp Estados, Instagram Stories e Instagram Feed usando una base SQLite propia, un perfil persistente de negocio y un catálogo manual. También puede leer opcionalmente una base externa de Nexar Comercio en modo solo lectura.

## Características

- Funciona sin Nexar Comercio ni otra app externa.
- Guarda perfil, catálogo, publicaciones y configuración en una SQLite local de ejecución.
- Permite cargar manualmente productos o servicios con precio, stock e imagen opcionales.
- Mantiene las imágenes manuales dentro de uploads locales ignorados por Git.
- Nexar Comercio se abre estrictamente en modo `read-only` usando SQLite URI `mode=ro`.
- Genera publicaciones finales listas para publicar con un proveedor determinista local, sin red ni API key.
- Sigue funcionando aunque la base externa no esté configurada o no exista.

## Estructura

```text
app.py
config.py
database.py
requirements.txt
.env.example
services/
templates/
static/
data/
```

`data/` queda en el repositorio solo como estructura mediante `.gitkeep`. Los archivos reales de ejecución no se versionan.

## Instalación en Linux

```bash
cd nexar-calendario-marketing
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`NEXAR_COMERCIO_DB` es opcional. Los datos del negocio y del catálogo no se guardan en `.env`.

## Ejecutar

```bash
source venv/bin/activate
python3 app.py
```

La app queda disponible en `http://127.0.0.1:5000`.

## Variables de entorno

Estas variables siguen existiendo como fallback o integración opcional:

- `DATA_SOURCE`: fuente inicial por defecto, `manual` o `nexar_comercio`.
- `NEXAR_COMERCIO_PATH`: ruta opcional al repo externo.
- `NEXAR_COMERCIO_DB`: ruta al archivo SQLite externo de Nexar Comercio en modo solo lectura.
- `BRAND_NAME`, `BRAND_PRIMARY`, `BRAND_SECONDARY`, `BRAND_ACCENT`.
- `BRAND_INSTAGRAM`, `BRAND_URL`, `BRAND_FONT_FAMILY`.
- `BRAND_LOGO_PATH`, `BRAND_BACKGROUNDS_DIR`.

El perfil real del negocio, la fuente seleccionada y el catálogo persistente se administran desde la interfaz y se guardan en la SQLite propia.

## Datos locales de ejecución

La app mantiene la convención existente `data/` para no romper instalaciones previas. No migra automáticamente a `instance/` porque ya hay compatibilidad estable con:

- `data/calendario.db`
- `data/uploads/`

Al iniciar, la aplicación crea automáticamente los directorios configurados:

- `data/`
- `data/uploads/`
- `data/exports/`
- `data/backups/`
- `data/cache/`
- `data/logs/`
- `static/generated/`

Estos archivos y carpetas son datos locales de ejecución y están ignorados por Git: bases `.db`, `.sqlite`, `.sqlite3`, uploads, exports, backups, cachés, logs, temporales, ZIP, TXT e imágenes generadas. Solo deben versionarse código, templates, tests, documentación y archivos de estructura como `.gitkeep`.

Las rutas se centralizan en `config.py` y pueden cambiarse con variables de entorno:

- `DATA_DIR`
- `DATABASE_PATH`
- `UPLOADS_DIR`
- `EXPORTS_DIR`
- `BACKUPS_DIR`
- `CACHE_DIR`
- `LOGS_DIR`
- `GENERATED_DIR`

## Flujo manual

1. Abrí `Mi negocio` y completá nombre, rubro, público objetivo y objetivo comercial.
2. Elegí la fuente `manual` o `nexar_comercio`.
3. Cargá productos o servicios en `Productos/servicios`.
4. Abrí `/calendario?mes=YYYY-MM`.
5. Usá `Generar contenido del mes`.
6. Revisá el calendario, previews e imágenes generadas.

## Datos persistidos

La base local crea y mantiene estas tablas de forma idempotente:

- `marketing_posts`
- `business_profile`
- `catalog_items`
- `app_settings`

Las migraciones no borran publicaciones existentes y siguen siendo compatibles con bases ya creadas.

`marketing_posts` conserva `texto` por compatibilidad, pero las publicaciones nuevas guardan allí únicamente copy público final. También se persisten `caption`, `visual_headline`, `visual_subtitle`, `visual_cta`, `strategy_used`, `content_provider`, `content_model`, `generation_status` y `updated_at`.

## Seguridad de datos externos

- La base externa de Nexar Comercio se abre únicamente desde `services/nexar_importer.py`.
- La conexión usa SQLite en modo solo lectura con `sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)`.
- Ese módulo no hace `commit()` ni ejecuta `INSERT`, `UPDATE`, `DELETE`, `ALTER`, `DROP` ni ninguna escritura sobre Nexar Comercio.
- Toda escritura propia de la app ocurre únicamente en rutas locales configuradas, por defecto `data/calendario.db`, `data/uploads/` y `static/generated/`.

## Motor de marketing

El flujo de generación usa contratos tipados:

- `MarketingBrief`: brief interno con objetivo, estrategia, audiencia, hechos permitidos y dirección visual. No se guarda ni se muestra.
- `GeneratedContent`: contenido público con título, caption, CTA, hashtags y textos visuales breves.

`services/marketing_engine.py` arma el brief desde `BusinessDataContext` y `ProductData`, selecciona estrategia mediante reglas explícitas y llama a un proveedor de contenido. Esta fase implementa solo `services/ai/deterministic.py`, un proveedor local determinista preparado para reemplazarse o ampliarse luego con proveedores de IA remotos.

El validador `services/content_validator.py` rechaza instrucciones editoriales internas como "Mostrá", "Prepará", "Podés mencionar", "Usá un tono", "Agrupá el contenido", "Propuesta de valor:" y referencias a crear o diseñar una publicación. Si un resultado no valida, no se persiste y se intenta fallback determinista.

## Sistema visual

- Las imágenes se generan con Pillow y plantillas por tipo: promoción, tip, producto destacado, novedad y recordatorio.
- El render usa `visual_headline`, `visual_subtitle` y `visual_cta`; no inserta el caption completo en la pieza.
- Puede incorporar imagen de producto o servicio, logo y datos públicos del negocio.
- Si existe `static/branding/logo.png`, se incorpora automáticamente como fallback.
- Si existe un logo guardado desde `Mi negocio`, ese logo pasa a ser el branding activo.

## Fechas especiales

- El módulo `services/fechas_especiales.py` concentra fechas comerciales fijas y fechas configurables por año.
- Al generar un mes, si un día coincide con una fecha especial, el sistema prioriza esa publicación por sobre la lógica genérica.
- Las publicaciones especiales pueden usar los tipos `fecha_especial`, `campana` y `temporada`.

## Motor de contenido

`services/motor_contenido.py` resuelve el contenido en este orden general:

1. Fecha especial.
2. Catálogo manual y objetivo comercial si la fuente activa es `manual`.
3. Datos reales de Nexar Comercio si la fuente activa es `nexar_comercio`.
4. Fallbacks seguros si faltan datos.

Cada post guarda además:

- `cta`
- `producto_nombre`
- `producto_id`
- `categoria_nombre`
- `imagen_producto_path`
- `origen_contenido`

## Validación local

```bash
python3 -m unittest discover
python3 -m compileall app.py config.py database.py services tests
```
