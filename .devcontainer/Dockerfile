FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

# uv: gestor de dependencias/entornos (binario estático, sin depender de pip)
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /usr/local/bin/

# Certificados corporativos opcionales (inspección SSL en la red del trabajo).
# Poné tus .crt en .devcontainer/certs/; si la carpeta está vacía no pasa nada.
COPY certs/ /usr/local/share/ca-certificates/corp/
RUN update-ca-certificates

# Utilidades de línea de comandos útiles para explorar datasets
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends \
       jq csvkit unzip p7zip-full less \
    && rm -rf /var/lib/apt/lists/*

# Pre-crear los puntos de montaje con el dueño correcto: así los volúmenes
# nombrados nacen propiedad de vscode y no de root.
RUN mkdir -p /home/vscode/.claude /home/vscode/.cache/uv /home/vscode/.venv \
    && chown -R vscode:vscode /home/vscode/.claude /home/vscode/.cache /home/vscode/.venv
