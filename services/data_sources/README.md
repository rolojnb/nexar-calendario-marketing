# Fuentes de datos

Esta carpeta concentra los conectores de datos de Nexar Calendario.

El calendario debe pedir datos a traves de `load_business_context()` y no depender directamente de una integracion concreta. Cada fuente devuelve un `BusinessDataContext` normalizado; mientras el motor actual siga usando el formato historico, `BusinessDataContext.to_legacy_dict()` mantiene compatibilidad.

## Fuentes iniciales

- `nexar_comercio.py`: adapta el importador read-only existente de Nexar Comercio.
- `manual.py`: fuente vacia segura para funcionar sin integracion externa.
- `csv_importer.py`: punto de extension para CSV/Excel futuro.

## Configuracion

- `DATA_SOURCE=nexar_comercio|manual|csv`
- `NEXAR_COMERCIO_DB=/ruta/a/base.sqlite`
- `CSV_DATA_SOURCE_PATH=/ruta/a/productos.csv`
