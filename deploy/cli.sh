#!/usr/bin/env bash
# Abre a CLI interativa dentro do container em execucao.
# Uso: bash deploy/cli.sh
set -euo pipefail

if ! docker ps --format '{{.Names}}' | grep -q '^casa-ludic-crm$'; then
  echo "[cli] Container 'casa-ludic-crm' nao esta rodando."
  echo "      Suba com: docker compose up -d"
  exit 1
fi

docker exec -it casa-ludic-crm python cli_interface.py
