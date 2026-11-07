# Proyecto: análisis de datasets educativos

## Entorno
- Corre dentro de un devcontainer (Debian + Python 3.12). Las dependencias se gestionan con **uv**.
- Ejecutar siempre con `uv run python ...` / `uv run pytest`. Para agregar paquetes: `uv add <paquete>` (nunca `pip install`).
- El venv está en `/home/vscode/.venv`, fuera del workspace.

## Estructura
- `data/raw/` — datos originales tal como se descargaron. **No modificar nunca.** No se versionan.
- `data/processed/` — datos limpios derivados (preferir Parquet). No se versionan.
- `notebooks/` — exploración. Nombrar `NN_tema.ipynb`.
- `src/edu_data/` — código reutilizable (carga, limpieza, recodificación).
- `outputs/` — gráficos y tablas finales.

## Convenciones de trabajo con datos
- Antes de analizar un dataset nuevo: documentar fuente, fecha de descarga, unidad de análisis y diccionario de variables en `data/README.md`.
- Todo paso raw → processed debe ser reproducible con un script en `src/`, no a mano.
- Para archivos grandes usar DuckDB o Polars en lugar de cargar todo en pandas.
- Encodings: los archivos oficiales argentinos suelen venir en `latin-1`/`cp1252` y con `;` como separador. Verificar antes de asumir UTF-8.
- Códigos de jurisdicción/departamento: tratarlos como texto (conservar ceros a la izquierda).

## Rigor estadístico (importante en encuestas educativas)
- Si el dataset trae **ponderadores** (factores de expansión), usarlos en toda estimación poblacional y aclararlo.
- Evaluaciones tipo PISA/Aprender pueden traer **valores plausibles** y **pesos replicados**: no promediar un solo valor plausible; estimar con todos y combinar.
- Distinguir siempre unidad de análisis (estudiante, escuela, sección) y no mezclar niveles sin decirlo.
- Reportar n, casos faltantes y cómo se trataron.

## Estilo
- Código y comentarios en español está bien; nombres de funciones en snake_case.
- Código autoexplicativo, solo comentar cuando es una aclaración del problema del negocio o de la parametría necesaria.
- Ningún comentario ni docstring con más de 150 caracteres, consultar en caso de ser necesario más.
- Ruff para formato y lint (`uv run ruff check . && uv run ruff format .`).
