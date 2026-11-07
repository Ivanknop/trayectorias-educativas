# Catálogo de datasets

Una entrada por dataset en `data/raw/`. Cada archivo de trayectoria informa el **ciclo lectivo anterior**
al año de su nombre (ver `diccionario_trayectoria.md`, sección 1).

Fuente de los CSV: [datos abiertos de la Secretaría de Educación](https://www.argentina.gob.ar/educacion/evaluacion-e-informacion-educativa/datos-abiertos-de-la-secretaria-de-educacion).

| Archivo | Ciclo lectivo | Fuente / URL | Descargado | Unidad de análisis | Ponderador | Notas |
|---|---|---|---|---|---|---|
| `2011 Trayectoria - agregada(in).csv` | 2010 | RA, DiNIEE. Base usuaria 1.2 "Trayectoria" | *completar* | Agregado provincia × departamento × sector × ámbito | No (censal) | 268 columnas (sin sufijo `20`) |
| `2012 Trayectoria - agregada(in).csv` | 2011 | Ídem | *completar* | Ídem | No | 268 columnas (sin sufijo `20`) |
| `2013 Trayectoria - agregada(in).csv` | 2012 | Ídem | *completar* | Ídem | No | 268 columnas (sin sufijo `20`) |
| `2014 Trayectoria - agregada(in).csv` | 2013 | Ídem | *completar* | Ídem | No | 268 columnas (sin sufijo `20`) |
| `2015 Trayectoria - agregada(in).csv` | 2014 | Ídem | *completar* | Ídem | No | 268 columnas (sin sufijo `20`) |
| `2016 Trayectoria - agregada(in).csv` | 2015 | Ídem | *completar* | Ídem | No | 268 columnas (sin sufijo `20`) |
| `2017 Trayectoria - agregada(in).csv` | 2016 | Ídem | *completar* | Ídem | No | 268 columnas (sin sufijo `20`) |
| `2018 Trayectoria - agregada(in).csv` | 2017 | Ídem | *completar* | Ídem | No | 268 columnas (sin sufijo `20`) |
| `2019 Trayectoria - agregada(in).csv` | 2018 | Ídem | *completar* | Ídem | No | 268 columnas (sin sufijo `20`) |
| `2020 Trayectoria - agregada(in).csv` | 2019 | Ídem | *completar* | Ídem | No | 268 columnas (sin sufijo `20`) |
| `2021 Trayectoria - agregada(in).csv` | 2020 | Ídem | *completar* | Ídem | No | 268 columnas (sin sufijo `20`) |
| `2022 Trayectoria - agregada(in).csv` | 2021 | Ídem | *completar* | Ídem | No | 268 columnas (sin sufijo `20`) |
| `2023 Trayectoria - agregada(in).csv` | 2022 | Relevamiento Anual (RA), DiNIEE – Min. Educación. Base usuaria 1.2 "Trayectoria", Educación Común | *completar* (archivo del 2026-11-07) | Agregado provincia × departamento × sector × ámbito (1.205 filas) | No (relevamiento censal) | 288 columnas. latin-1, `;`, CRLF |
| `2024 Trayectoria - agregada(in).csv` | 2023 | Ídem | *completar* | Ídem (1.209 filas) | No | 288 columnas. Encabezado `Departamento` con mayúscula |
| `2025 Trayectoria - agregada(in).csv` | 2024 | Ídem | *completar* | Ídem (1.210 filas) | No | 316 columnas: suma el bloque `promovidos_mas_2mat` |
| `geo/provincias_ign.geojson` | — | IGN, WFS capa `ign:provincia` (`uv run python -m edu_data.geo descargar`) | ver `geo/FUENTE.txt` | Provincia | — | No se versiona (111 MB); genera `src/edu_data/recursos/provincias_svg.json` |
| `Diccionario de bases RA anonimizadas(Presentacion).csv` | — | DiNIEE | *completar* | — | — | Solo la pestaña índice; **falta la pestaña de la base Trayectoria** |

Diccionario de variables y descripción: [`diccionario_trayectoria.md`](diccionario_trayectoria.md).
Lectura reproducible: `src/edu_data/trayectoria.py` (`leer_trayectoria(anio)`).
Perfil por columna: `uv run python -m edu_data.trayectoria 2024` → `outputs/perfil_trayectoria_ciclo_2024.csv`.
Base larga y tabla provincial: `uv run python -m edu_data.agregados` (ver sección 9 del diccionario).
Controles de calidad: `uv run python -m edu_data.validacion` → `outputs/validacion_*.csv` (sección 10).
Visor: `uv run python -m edu_data.visor` → `outputs/visor/index.html` (sección 11).

## Qué se versiona y GitHub Actions

- **Se suben al repo solo los 15 CSV `YYYY Trayectoria - agregada(in).csv`** (13 MB, datos abiertos). Son el único
  insumo de datos. Se guardan byte a byte, sin convertir finales de línea (`.gitattributes`).
- **El mapa** usa `src/edu_data/recursos/provincias_svg.json`, que va versionado (82 KB). El GeoJSON del IGN (111 MB)
  supera el límite de GitHub y no se sube; solo hace falta para regenerar ese recurso
  (`uv run python -m edu_data.geo descargar`).
- **No se suben**: `data/processed/`, `outputs/`, el GeoJSON del IGN y el diccionario.
- **La Action** `.github/workflows/visor.yml` corre lint y tests, construye el visor y los controles de calidad, y
  los deja como *artifacts* (`visor-trayectorias` y `validacion`), que se borran a los 30 días. El repo es
  público: cualquier usuario con sesión en GitHub puede descargarlos mientras existan. No se publica en GitHub
  Pages.
- **Ojo**: el visor incluye los datos procesados (`datos.js`). Quien tenga el visor tiene los datos.
