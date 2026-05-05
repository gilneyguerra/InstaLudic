#!/usr/bin/env bash
# Backup diario do SQLite. Rodado pelo cron em /etc/cron.d/casa-ludic-backup
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/casa-ludic-crm}"
DB="$APP_DIR/outputs/leads.db"
BACKUP_DIR="$APP_DIR/outputs/backups"
KEEP_DAYS=14

mkdir -p "$BACKUP_DIR"

if [[ ! -f "$DB" ]]; then
  echo "$(date -Iseconds) [backup] DB ainda nao existe ($DB) - skip"
  exit 0
fi

STAMP=$(date +%Y%m%d_%H%M%S)
DEST="$BACKUP_DIR/leads_$STAMP.db"

# Backup consistente mesmo com a aplicacao escrevendo
sqlite3 "$DB" ".backup '$DEST'" 2>/dev/null || cp -- "$DB" "$DEST"
gzip -9 "$DEST"

echo "$(date -Iseconds) [backup] criado: ${DEST}.gz"

# Retencao
find "$BACKUP_DIR" -type f -name 'leads_*.db.gz' -mtime +$KEEP_DAYS -delete
echo "$(date -Iseconds) [backup] retencao $KEEP_DAYS dias aplicada"
