#!/bin/bash

# Log Cleanup Script
# Active logs  (*.log)      — never touched (e.g. django.log, gunicorn-access.log).
# Previous run (*.prev.log) — never touched (one per type, always fresh).
# Dated archives (NAME.YYYY-MM-DD.log)  — deleted after RETENTION_DAYS (current format).
# Old dated archives (NAME.log.YYYY-MM-DD) — deleted after RETENTION_DAYS (pre-rename format).
# Legacy timestamp archives (*.YYYY-MM-DD_HHMM.log, DD-MM-YYYY_*.log) — deleted after RETENTION_DAYS.
# Run via cron: 0 2 * * * /path/to/cleanup_logs.sh

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
REDIS_LOG="$PROJECT_ROOT/Legalv1/logs/redis/redis-monitor.log"
RETENTION_DAYS=90

echo "Cleaning up archived log files older than $RETENTION_DAYS days..."

if [ ! -d "$LOG_DIR" ]; then
    echo "Error: log directory not found: $LOG_DIR"
    exit 1
fi

BEFORE_SIZE=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)

# Delete old archives in logs/ and logs/dev/ (maxdepth 2 covers the dev/ subdir)
DELETED_COUNT=$(
    find "$LOG_DIR" -maxdepth 2 -type f \( \
        -name "*.????-??-??.log" \
        -o -name "*.log.????-??-??" \
        -o -name "*.????-??-??_????.log" \
        -o -name "??-??-????_*.log" \
    \) -mtime +$RETENTION_DAYS -print -delete 2>/dev/null | wc -l
)

# Delete empty .log files (but not .prev.log)
EMPTY_DELETED=$(find "$LOG_DIR" -maxdepth 2 -type f -name "*.log" ! -name "*.prev.log" -empty -print -delete 2>/dev/null | wc -l)

AFTER_SIZE=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)

echo "  Archived logs deleted:  $DELETED_COUNT"
echo "  Empty logs deleted:     $EMPTY_DELETED"
echo "  Size before: $BEFORE_SIZE  ->  after: $AFTER_SIZE"
echo ""
echo "Active log files:"
find "$LOG_DIR" -maxdepth 2 -type f -name "*.log" ! -name "*.????-??-??.log" \
    ! -name "*.????-??-??_????.log" \
    ! -name "*.log.????-??-??" \
    ! -name "??-??-????_*.log" \
    | sort | while read -r f; do
        size=$(du -sh "$f" 2>/dev/null | cut -f1)
        echo "  $f ($size)"
    done
echo ""
echo "[$(date)] Cleanup complete"

# ── OpenSearch cleanup ──────────────────────────────────────────────────────
echo ""
echo "Cleaning up OpenSearch indices..."

# Delete top_queries indices older than 30 days
CUTOFF=$(date -d '30 days ago' +%Y.%m.%d)
DELETED_OS=0
if curl -s "http://localhost:9200/_cat/indices/top_queries-*?h=index" 2>/dev/null | while read idx; do
    DATE=$(echo "$idx" | grep -oP '\d{4}\.\d{2}\.\d{2}')
    if [[ "$DATE" < "$CUTOFF" ]]; then
        curl -s -X DELETE "http://localhost:9200/$idx" >/dev/null 2>&1
        ((DELETED_OS++))
    fi
done; then
    echo "  Deleted top_queries indices older than 30 days"
fi

# Rotate redis-monitor.log if it exceeds 50 MB
if [ -f "$REDIS_LOG" ] && [ $(stat -f%z "$REDIS_LOG" 2>/dev/null || stat -c%s "$REDIS_LOG" 2>/dev/null || echo 0) -gt 52428800 ]; then
    mv "$REDIS_LOG" "$REDIS_LOG.$(date +%Y-%m-%d-%H%M%S)"
    echo "  Rotated redis-monitor.log (exceeded 50 MB)"
fi

echo "[$(date)] OpenSearch cleanup complete"
