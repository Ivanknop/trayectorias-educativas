---
name: actualizar-plantilla
description: Actualizar un proyecto generado a una versión nueva de la plantilla edu-data-template
  (merge de tres vías con lo propio del proyecto). Usar cuando el usuario pide actualizar,
  sincronizar o traer cambios de la plantilla.
---

# Actualizar el proyecto desde la plantilla

Variables usadas abajo: `P` raíz del proyecto, `C` clon de la plantilla, `B` versión base
(la del proyecto), `D` versión destino. Nunca se commitea: el resultado queda para revisión.

## a. Precondiciones
- `git -C "$P" rev-parse --is-inside-work-tree` y `git -C "$P" status --porcelain` vacío.
  Si no es un repo git o hay cambios sin commitear (incluidos archivos nuevos), **frenar** y
  pedir al usuario que commitee o guarde sus cambios: el árbol limpio es lo que permite revisar
  y deshacer la actualización.

## b. Versiones
- Leer `.plantilla.json`: `plantilla` (URL), `version` (tag o hash = `B`), `so`.
  Si no existe (proyecto generado antes de v0.1.0), pedir al usuario el commit de la plantilla
  desde el que se generó y crear el archivo con esos datos.
- `D`: la versión que pida el usuario o, si no pide, el último tag
  (`git -C "$C" tag --sort=-v:refname | head -1`, después de clonar). Si la plantilla no tiene
  tags, proponer el último commit de la rama principal y confirmar.

## c. Clonar y resumir
```bash
C="$(mktemp -d /tmp/plantilla.XXXXXX)"
git clone --quiet "<plantilla>" "$C"
git -C "$C" cat-file -e "$B^{commit}" && git -C "$C" cat-file -e "$D^{commit}"
```
- Si el clon falla (p. ej. URL SSH sin clave en el contenedor), pedir una URL HTTPS o una ruta
  local. Si `B` o `D` no existen en el clon, frenar y avisar.
- Si `B` y `D` apuntan al mismo commit, no hay nada que actualizar.
- CHANGELOG: leer `git -C "$C" show "$D:CHANGELOG.md"` y tomar las entradas posteriores a `B`
  hasta `D` inclusive. Si `B` es un hash, su versión es
  `git -C "$C" describe --tags --abbrev=0 "$B"` (sin tag previo: todas las entradas hasta `D`).
  Complementar con `git -C "$C" log --oneline "$B..$D"`.
- Hacer la clasificación del paso d **sin aplicar nada** y mostrar al usuario:
  resumen de cambios del CHANGELOG, pasos manuales, y la lista de archivos por acción
  (merge, nuevo, borrar, a decidir). **Esperar confirmación** antes de seguir.

## d. Aplicar los cambios de archivos
Archivos cambiados, sin los excluidos por `.plantilla/excluir_actualizacion.txt` de `D`
(sintaxis `.gitignore`; se evalúa en un repo vacío para no mezclar con otros ignores):
```bash
T="$(mktemp -d)"; git init -q "$T"
git -C "$C" show "$D:.plantilla/excluir_actualizacion.txt" > "$T/excluir.txt"
git -C "$C" diff --no-renames --name-status "$B" "$D" > "$T/cambios.tsv"
cut -f2 "$T/cambios.tsv" \
  | git -C "$T" -c core.excludesFile="$T/excluir.txt" check-ignore --no-index --stdin \
  > "$T/excluidos.txt" || true
grep -vFxf "$T/excluidos.txt" <(cut -f2 "$T/cambios.tsv") > "$T/a_aplicar.txt" || true
```
Para cada archivo `f` de `a_aplicar.txt`, según su estado en `cambios.tsv`:
- **M (modificado)**: merge de tres vías sobre el archivo del proyecto.
  ```bash
  git -C "$C" show "$B:$f" > "$T/base"; git -C "$C" show "$D:$f" > "$T/destino"
  git merge-file -L proyecto -L "plantilla $B" -L "plantilla $D" "$P/$f" "$T/base" "$T/destino"
  ```
  Código de salida: 0 = limpio; > 0 = cantidad de conflictos (quedan marcados en el archivo);
  < 0 = error (p. ej. binario) → preguntar. Si el archivo no existe en el proyecto (lo borró),
  preguntar si se recrea con la versión de `D` o se deja borrado.
- **A (nuevo)**: si no existe en el proyecto, copiarlo (`git -C "$C" show "$D:$f" > "$P/$f"`,
  creando el directorio) y aplicar el modo de `git -C "$C" ls-tree "$D" -- "$f"`
  (`100755` → `chmod +x`). Si ya existe igual, nada; si existe distinto, preguntar.
- **D (borrado)**: si el archivo del proyecto es idéntico a `B:$f` (`cmp`), borrarlo
  (`rm -- "${P:?}/${f:?}"`). Si cambió respecto de la base, mostrar la diferencia y preguntar. Si ya no existe, nada.
- **T u otro estado**: mostrar y preguntar.
- Si cambió el modo de un archivo (`git -C "$C" diff --summary "$B" "$D"`), aplicarlo.

## e. Conflictos
- Listar los archivos con conflictos (`grep -ln '^<<<<<<< proyecto' ...`) y mostrar cada bloque:
  lado `proyecto`, lado `plantilla D`, y qué cambió la plantilla entre `B` y `D`.
- Resolver **con el usuario**, bloque por bloque: quedarse con un lado o combinar. Nunca elegir
  solo, aunque la resolución parezca obvia.
- Al terminar, verificar que no quedan marcas: `git -C "$P" grep -nE '^(<<<<<<<|>>>>>>>) '`.

## f. Cierre
- Aplicar los **pasos manuales** del CHANGELOG (los que requieran decisión, consultarlos).
- Actualizar `version` en `.plantilla.json` a `D` (el tag si lo tiene, si no el hash),
  conservando `plantilla` y `so`.
- Correr y reportar: `uv sync`, `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run pytest`. Si algo falla, reportarlo; no corregir código del proyecto sin consultar.
  Si falla algo que ya fallaba antes de actualizar, aclararlo.
- Si `uv sync` modifica o crea `uv.lock`, incluirlo en el resumen (se versiona en el proyecto).
- Borrar los temporales: `rm -rf -- "${C:?}" "${T:?}"`.

## g. Entrega (sin commit)
- `git -C "$P" status` y `git -C "$P" diff --stat`.
- Resumir: versión `B` → `D`, archivos mergeados, nuevos, borrados, conflictos y cómo se
  resolvieron, pasos manuales aplicados, resultado de ruff y pytest.
- Dejar todo sin commitear para que el usuario revise (`git diff`). Para deshacer:
  `git restore . && git clean -fd` (mostrar antes qué borraría `git clean -nd`).
