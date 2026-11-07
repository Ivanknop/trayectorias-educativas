---
name: publicar
description: Preparar el repo y una GitHub Action para construir y publicar resultados (GitHub
  Pages o artifact). Usar cuando el usuario quiere subir el proyecto a GitHub, publicar un visor
  o "verlo en Pages".
---

# Publicar resultados

## 1. Preguntar primero
- ¿El repo es público o privado?
- ¿El resultado va a GitHub Pages (sitio público), queda como artifact de la Action, o nada?
- Aclarar: lo publicado en Pages es público aunque el repo sea privado (salvo planes Enterprise
  con Pages privado). En un repo público, los artifacts los descarga cualquiera con sesión.

## 2. Qué se versiona
- Solo crudos que sean datos abiertos y livianos, si la CI los necesita: descomentar y ajustar
  el patrón `!data/raw/...` de `.gitignore`. Nada de `data/processed/` ni `outputs/`.
- `.gitattributes` ya trae `data/raw/** -text -eol`: los crudos se guardan byte a byte.
- Archivos de más de 100 MB no se pueden subir (límite de GitHub).
- Recursos derivados pequeños y estables pueden ir en `src/edu_data/recursos/`.
- `uv.lock` se versiona (la Action usa `uv sync --locked`).

## 3. Workflow
- Copiar `.github/workflows/publicar.yml.ejemplo` a `.github/workflows/publicar.yml`.
- Reemplazar el paso "Construir" por el comando real (raw → outputs) y ajustar `path` del sitio.
- Etapas: construir (uv, lint, tests, construcción) y publicar (`deploy-pages`).

## 4. Simular la CI antes del push
- Copiar a una carpeta limpia solo lo que se va a versionar:
  `git ls-files --cached --others --exclude-standard`.
- Ahí: `uv sync --locked`, `uv run pytest` y la construcción. Comparar los archivos generados
  con los locales: si falta un insumo, aparece acá y no en la Action.

## 5. Configuración en GitHub (la hace el usuario)
- Settings → Pages → Source: **GitHub Actions** (no "Deploy from a branch", que publica el
  README).
- About (engranaje) → "Use your GitHub Pages website".
- Diferencia: `github.com/<usuario>/<repo>` muestra el README;
  `<usuario>.github.io/<repo>/` muestra el sitio.

## 6. Verificar en vivo
- Pedir con `curl -I` la raíz, `index.html` y los archivos de datos del sitio.
- Las rutas del sitio deben ser relativas (Pages lo sirve en una subcarpeta `/<repo>/`).
