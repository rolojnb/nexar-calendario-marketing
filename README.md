# nexar-calendario-marketing

Aplicación Flask independiente para generar un calendario mensual de contenido para WhatsApp Estados, Instagram Stories e Instagram Feed usando una base SQLite propia y lectura opcional desde una base externa de Nexar Comercio.

## Características

- No modifica repositorios externos: solo lectura si la base existe.
- Nexar Comercio se abre estrictamente en modo `read-only` usando SQLite URI `mode=ro`.
- Genera publicaciones para un mes completo con plantillas simples sin IA.
- Puede basar parte del calendario en productos, categorías, stock y ventas reales si existen en la base externa.
- Crea imágenes automáticamente con Pillow.
- Guarda el contenido y el historial en `data/calendario.db`.
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

## Instalación en Linux

```bash
cd nexar-calendario-marketing
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Editá `.env` y completá `NEXAR_COMERCIO_DB` si querés leer datos reales desde una base externa.

## Ejecutar

```bash
source venv/bin/activate
python3 app.py
```

La app quedará disponible en `http://127.0.0.1:5000`.

## Variables de entorno

- `NEXAR_COMERCIO_PATH`: ruta opcional al repo externo.
- `NEXAR_COMERCIO_DB`: ruta al archivo SQLite externo de Nexar Comercio en modo solo lectura.
- `BRAND_NAME`: nombre comercial a usar en copies e imágenes.
- `BRAND_PRIMARY`: color principal hexadecimal.
- `BRAND_SECONDARY`: color secundario hexadecimal.
- `BRAND_ACCENT`: color de acento hexadecimal.
- `BRAND_INSTAGRAM`: usuario de Instagram o handle de marca para el footer.
- `BRAND_URL`: URL pública futura para el footer.
- `BRAND_FONT_FAMILY`: tipografía base para las piezas generadas con Pillow.
- `BRAND_LOGO_PATH`: logo PNG opcional, por defecto `static/branding/logo.png`.
- `BRAND_BACKGROUNDS_DIR`: carpeta opcional con fondos para plantillas, por defecto `static/branding/fondos`.

## Flujo del MVP

1. Abrí la pantalla `/calendario?mes=YYYY-MM`.
2. Elegí un mes.
3. Usá `POST /calendario/generar-mes` desde la interfaz para crear publicaciones.
4. Desde el calendario podés generar imágenes faltantes del mes o regenerarlas todas.
5. Revisá el calendario, abrí cada preview y regenerá la imagen individual si hace falta.

## Seguridad de datos externos

- La base externa de Nexar Comercio se abre únicamente desde `services/nexar_importer.py`.
- La conexión usa SQLite en modo solo lectura con `sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)`.
- Ese módulo no hace `commit()` ni ejecuta `INSERT`, `UPDATE`, `DELETE`, `ALTER`, `DROP` ni ninguna escritura sobre Nexar Comercio.
- Toda escritura de la app ocurre únicamente en `data/calendario.db`.
- Las migraciones de `marketing_posts` usan `ALTER TABLE` solo sobre `data/calendario.db`.

## Configurar `NEXAR_COMERCIO_DB`

1. Ubicá el archivo SQLite real de Nexar Comercio.
2. Definí la ruta en `.env`:

```bash
NEXAR_COMERCIO_DB=/ruta/completa/a/nexar_comercio.db
```

3. Reiniciá la app.

Si la ruta no existe, si la base no abre o si faltan tablas esperadas, la aplicación sigue funcionando con contenido genérico.

## Datos externos que intenta leer

El importador trabaja en modo tolerante al esquema. Si existen, intenta leer:

- `productos`
- `categorias`
- `ventas`
- `detalle_ventas`
- columnas de `stock`
- columnas de `precio`
- `imagen_path` o variantes comunes de ruta de imagen

Si alguna tabla o columna no existe, la app omite esa parte y sigue con fallbacks seguros.

## Sistema visual

- Las imágenes se generan con Pillow y plantillas por tipo: promoción, tip, producto destacado, novedad y recordatorio.
- El render usa degradados, overlays suaves, CTA visual y footer de marca.
- Si existe `static/branding/logo.png`, se incorpora automáticamente.
- Si existen fondos en `static/branding/fondos/`, se usan como apoyo visual sin romper la app si faltan.

## Fechas especiales

- El módulo `services/fechas_especiales.py` concentra fechas comerciales fijas y fechas configurables por año.
- Al generar un mes, si un día coincide con una fecha especial, el sistema prioriza esa publicación por sobre la lógica genérica.
- Las publicaciones especiales pueden usar los tipos `fecha_especial`, `campana` y `temporada`.
- El calendario marca visualmente esos días y muestra nombre y prioridad para facilitar la revisión.

## Motor de contenido comercial

`services/motor_contenido.py` decide qué publicación crear en este orden:

1. Fecha especial.
2. Producto más vendido.
3. Producto con stock alto.
4. Producto con bajo movimiento.
5. Categoría destacada.
6. Tip genérico.
7. Promoción genérica.

Cada post guarda además:

- `cta`
- `producto_nombre`
- `producto_id`
- `categoria_nombre`
- `imagen_producto_path`
- `origen_contenido`

Eso permite que el calendario y la preview distingan el contenido generado desde datos reales.

## Generación de imágenes

- Generación individual: desde cada preview podés usar `POST /post/<id>/generar-imagen`.
- Generación masiva: desde el calendario podés usar `POST /calendario/generar-imagenes-mes` para crear PNG solo en posts sin imagen.
- Regeneración masiva: la misma ruta acepta `regenerar=true` para rehacer todas las imágenes del mes.
- Los archivos se guardan por mes en `static/generated/YYYY-MM/`.
- El formato de nombre usa `post_<id>_<canal>_<tipo>.png` cuando el post ya existe en SQLite.
- Si `imagen_producto_path` existe y el archivo está disponible, se integra a la pieza visual sin deformarlo.
- Si la imagen no existe o no puede abrirse, el diseño sigue generándose de forma normal.

## Resultado esperado

Al generar un mes, parte de las publicaciones puede salir basada en productos y categorías reales de Nexar Comercio cuando la base externa tenga información suficiente. Si no la tiene, el calendario se completa igual con contenido genérico y fechas especiales.
