# Trayectorias escolares en Argentina

**👉 Ver el visor: <https://ivanknop.github.io/trayectorias-educativas/index.html>**

Análisis de las bases de **Trayectoria** del Relevamiento Anual (RA) de la DiNIEE (Ministerio de Educación),
educación común, **ciclos lectivos 2010 a 2024**. Incluye un visor interactivo para explorar repitencia, abandono,
promoción, matrícula, egreso, pérdida entre años y desplazamiento estatal → privado, por provincia, nivel, sector,
ámbito y sexo.

Fuente: [datos abiertos de la Secretaría de Educación](https://www.argentina.gob.ar/educacion/evaluacion-e-informacion-educativa/datos-abiertos-de-la-secretaria-de-educacion).

> **Importante:** cada archivo informa el **ciclo lectivo anterior** al año de su nombre (el archivo 2025 es el
> ciclo 2024). Todo el proyecto trabaja por ciclo.

## Qué hay en el proyecto

| Ruta | Contenido |
|---|---|
| `data/raw/` | Los 15 CSV `YYYY Trayectoria - agregada(in).csv` (archivos 2011–2025). Único insumo de datos. |
| `data/README.md` | Catálogo de fuentes, qué se versiona y cómo funciona la Action. |
| `data/diccionario_trayectoria.md` | Diccionario de variables, criterios, indicadores y alertas de calidad. |
| `src/edu_data/trayectoria.py` | Lectura de los CSV y esquema común a todos los años. |
| `src/edu_data/agregados.py` | Base larga por ciclo, `resumir()` para cualquier combinación de cortes y `continuidad()`. |
| `src/edu_data/validacion.py` | Controles de calidad y registro de alertas (`ALERTAS`). |
| `src/edu_data/geo.py` | Cartografía de provincias (IGN) simplificada para el mapa. |
| `src/edu_data/visor.py` y `plantillas/` | Construcción del visor estático (guía + mapa + panel por provincia). |
| `tests/` | Tests de lectura, agregación, continuidad y datos del visor. |
| `.github/workflows/visor.yml` | Construye el visor en GitHub Actions y lo publica en GitHub Pages. |

El detalle está en `data/diccionario_trayectoria.md`.

## Cómo correrlo

```bash
uv run python -m edu_data.visor        # construye base, datos y visor → outputs/visor/index.html
uv run python -m edu_data.validacion   # controles de calidad → outputs/validacion_*.csv
uv run pytest                          # tests
uv run ruff check . && uv run ruff format .
```

Consultas desde Python:

```python
from edu_data.agregados import cargar_largo, resumir

L = cargar_largo()
resumir(L, provincia="Salta", nivel="secundaria", por=["sector", "sexo"])
```

## Entorno

El proyecto se generó a partir de la plantilla [edu-data-template](https://github.com/Ivanknop/edu-data-template): devcontainer con Python 3.12
y uv, y las convenciones de trabajo de `CLAUDE.md`.
