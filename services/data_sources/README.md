# Fuentes de datos

Esta carpeta concentra los conectores de datos de Nexar Calendario.

El calendario debe pedir datos a traves de `load_business_context()` y no depender directamente de una integracion concreta. Cada fuente devuelve un `BusinessDataContext` normalizado; mientras el motor actual siga usando el formato historico, `BusinessDataContext.to_legacy_dict()` mantiene compatibilidad.

## Fuentes disponibles

- `nexar_comercio.py`: adapta el importador read-only existente de Nexar Comercio.
- `manual.py`: lee perfil de negocio y catalogo persistidos en la SQLite propia.
- `csv_importer.py`: punto de extension para CSV/Excel futuro.

## Configuracion

- `DATA_SOURCE=nexar_comercio|manual|csv`: valor por defecto inicial o fallback.
- `NEXAR_COMERCIO_DB=/ruta/a/base.sqlite`: conector externo opcional y read-only.
- `CSV_DATA_SOURCE_PATH=/ruta/a/productos.csv`: reservado para la fuente CSV futura.

La seleccion activa de `manual` o `nexar_comercio` puede persistirse en la propia SQLite mediante `app_settings`, sin guardar datos de negocio en variables de entorno.
