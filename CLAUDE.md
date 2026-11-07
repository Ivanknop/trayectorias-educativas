# Proyecto: análisis de datasets educativos

## Forma de trabajo
- Por defecto, siempre plan primero (modo plan: explorar, preguntar, proponer pasos).
  No se escribe ni modifica código hasta que el desarrollador lo pida explícitamente.
- No se hacen commits ni push sin autorización explícita.
- Ante rediseños o pedidos ambiguos, preguntar antes: alcance, formato, ejes, cortes, medida.
- Para actualizar el proyecto a una versión nueva de la plantilla: skill `actualizar-plantilla`.

## Entorno
- Corre dentro de un devcontainer (Debian + Python 3.12). Las dependencias se gestionan con **uv**.
- Ejecutar siempre con `uv run python ...` / `uv run pytest`.
  Para agregar paquetes: `uv add <paquete>` (nunca `pip install`).
- El venv está en `/home/vscode/.venv`, fuera del workspace.

## Estructura
- `data/raw/` — datos originales tal como se descargaron. **No modificar nunca.** No se versionan.
- `data/processed/` — datos limpios derivados (preferir Parquet). No se versionan.
- `notebooks/` — exploración. Nombrar `NN_tema.ipynb`.
- `src/edu_data/` — código reutilizable (carga, limpieza, recodificación).
- `outputs/` — gráficos y tablas finales.

## Convenciones de trabajo con datos
- Dataset nuevo: seguir la skill `dataset-nuevo` y documentar fuente, fecha de descarga,
  período, unidad de análisis y diccionario en `data/README.md`.
  Si el diccionario no cubre todas las variables, pedir lo faltante en la primera respuesta.
- Todo paso raw → processed debe ser reproducible con un script en `src/`, no a mano.
- Los comandos de construcción regeneran desde `data/raw/`; no reutilizan intermedios viejos.
- Para archivos grandes usar DuckDB o Polars en lugar de cargar todo en pandas.
- Encodings: los archivos oficiales (p. ej. argentinos) suelen venir en `latin-1`/`cp1252`
  y con `;` como separador. Verificar antes de asumir UTF-8.
- Códigos de unidades territoriales o institucionales: tratarlos como texto
  (conservar ceros a la izquierda).
- Período de referencia: separar "año del archivo" de "período que informa". Verificarlo con
  un shock conocido (p. ej. pandemia 2020) antes de etiquetar años, y documentarlo.
- Vacío no es cero: un vacío que significa "no aplica / sin oferta" queda NA en todo el
  pipeline, también en tablas y gráficos (punto vacío o línea omitida, con nota).

## Rigor estadístico
- Si el dataset trae **ponderadores** (factores de expansión), usarlos en toda estimación
  poblacional y aclararlo.
- Evaluaciones tipo PISA/Aprender pueden traer **valores plausibles** y **pesos replicados**:
  no promediar un solo valor plausible; estimar con todos y combinar.
- Distinguir siempre unidad de análisis (estudiante, escuela, sección) y no mezclar niveles.
- Reportar n, casos faltantes y cómo se trataron.
- Verificar las identidades contables del dataset (total = suma de partes, flujos que cierran).

## Calidad de datos
- Todo análisis corre controles de pertinencia (skill `validar-calidad`) y reporta en la
  respuesta los datos que parezcan mal.
- Las alertas revisadas van a un único registro; las visualizaciones las marcan.
  No se ocultan ni corrigen en silencio.
- Si se corrige un dato, se conserva el original (`<columna>_informado`) y se documenta.

## Análisis y visualización
- De lo general a lo particular: primero el total y la evolución; los cortes, a pedido.
- No generar lotes de gráficos sin pedido. Preferir un visor interactivo on demand.
- Métricas derivadas o abstractas (brechas, índices) se proponen con un ejemplo de lectura
  antes de implementarlas.
- Cada número mostrado se contrasta con el cálculo en Python (tests).
- Los archivos generados en `outputs/` no se editan a mano: llevan la marca
  `GENERADO por <script> — editar en <origen>`. Al entregar, decir qué archivo editar.

## Publicación
- Antes de publicar, preguntar la visibilidad del repo y el destino (Pages, artifact, nada):
  skill `publicar`.

## Estilo
- Código y comentarios en español está bien; nombres de funciones en snake_case.
- Código autoexplicativo; comentar solo aclaraciones del negocio o de la parametría necesaria.
- Comentarios y docstrings: máximo 100 caracteres por línea (límite de ruff).
  Si una explicación pasa de 150 caracteres en total, va a `data/*.md`, no al código.
- Ruff para formato y lint (`uv run ruff check . && uv run ruff format .`).
