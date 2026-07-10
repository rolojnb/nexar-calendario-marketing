# Fuentes de datos

Esta carpeta concentra los conectores de datos de Nexar Calendario.

La meta es que el motor de marketing no dependa directamente de una aplicación concreta. Los productos, categorías, ventas, stock e imágenes pueden venir desde distintas fuentes, pero siempre deben convertirse a un contexto común.

## Flujo conceptual

```text
Nexar Comercio / CSV / carga manual / APIs futuras
        ↓
Fuente de datos concreta
        ↓
BusinessDataContext normalizado
        ↓
Motor de estrategia y calendario
```

## Archivos

- `base.py`: contrato común de datos normalizados.
- `registry.py`: punto único para cargar una fuente.
- `nexar_comercio.py`: adaptador de Nexar Comercio local usando el importador read-only existente.
- `manual.py`: fuente manual inicial, preparada para futura carga desde UI.
- `csv_importer.py`: fuente CSV/Excel inicial, preparada para futura importación de archivos.

## Regla principal

El resto de la aplicación debería pedir datos a través de:

```python
from services.data_sources import load_business_context

context = load_business_context(source="nexar_comercio", nexar_comercio_db_path="...")
```

Y no llamar directamente a conectores concretos desde el calendario o el motor de marketing.
