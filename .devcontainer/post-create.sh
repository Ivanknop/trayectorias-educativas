#!/usr/bin/env bash
set -euo pipefail

# Por si el volumen ya existía de antes con otro dueño
sudo chown -R vscode:vscode /home/vscode/.claude /home/vscode/.cache/uv /home/vscode/.venv

echo ">> Instalando dependencias Python con uv..."
uv sync

echo ">> Registrando kernel de Jupyter..."
uv run python -m ipykernel install --user --name edu-data --display-name "Python (edu-data)"

echo ">> Listo."
echo "   Python:      $(uv run python --version)"
echo "   Claude Code: $(claude --version 2>/dev/null || echo 'no encontrado')"
echo "   Primera vez en esta máquina: ejecutá 'claude' y logueate."
