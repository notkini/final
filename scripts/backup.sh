#!/usr/bin/env bash
#
# TODO (deferred per project decisions -- not wired into cron yet):
# Basic pg_dump backup of the weldomat_monitor Postgres database into
# ./backups/. When you're ready to turn this on:
#
#   1. chmod +x scripts/backup.sh
#   2. Test manually: ./scripts/backup.sh
#   3. Add to crontab, e.g. nightly at 03:00:
#        0 3 * * * /home/pi/weldomat_monitor/scripts/backup.sh >> /home/pi/weldomat_monitor/logs/backup.log 2>&1
#
# This intentionally keeps the last 14 daily dumps and deletes older ones.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

set -a
source "$PROJECT_DIR/.env"
set +a

mkdir -p "$BACKUP_DIR"

OUT_FILE="$BACKUP_DIR/weldomat_${TIMESTAMP}.sql.gz"

docker exec weldomat_postgres pg_dump -U "${POSTGRES_USER:-weldomat}" "${POSTGRES_DB:-weldomat_monitor}" \
  | gzip > "$OUT_FILE"

echo "Backup written to $OUT_FILE"

# Keep only the last 14 backups
find "$BACKUP_DIR" -name "weldomat_*.sql.gz" -type f | sort | head -n -14 | xargs -r rm --
