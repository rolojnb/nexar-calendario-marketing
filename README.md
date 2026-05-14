# nexar-calendario-marketing

Aplicación Flask independiente para generar un calendario mensual de contenido para WhatsApp Estados, Instagram Stories e Instagram Feed usando una base SQLite propia y lectura opcional desde una base externa de Nexar Comercio o Nexar Tienda.

## Características

- No modifica repositorios externos: solo lectura si la base existe.
- Nexar Comercio se abre estrictamente en modo `read-only` usando SQLite URI `mode=ro`.
- Genera publicaciones para un mes completo con plantillas simples sin IA.
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
- `NEXAR_COMERCIO_DB`: ruta al archivo SQLite externo en modo solo lectura.
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
- Ese módulo no hace `commit()` ni ejecuta escrituras sobre Nexar Comercio.
- Toda escritura de la app ocurre únicamente en `data/calendario.db`.

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

## Generación de imágenes

- Generación individual: desde cada preview podés usar `POST /post/<id>/generar-imagen`.
- Generación masiva: desde el calendario podés usar `POST /calendario/generar-imagenes-mes` para crear PNG solo en posts sin imagen.
- Regeneración masiva: la misma ruta acepta `regenerar=true` para rehacer todas las imágenes del mes.
- Los archivos se guardan por mes en `static/generated/YYYY-MM/`.
- El formato de nombre usa `post_<id>_<canal>_<tipo>.png` cuando el post ya existe en SQLite.

## Próximos pasos

- Integrar IA para enriquecer copies y variantes por canal.
- Conectar métricas reales de ventas y productos destacados.
- Agregar exportación por lote para diseño o publicación.
