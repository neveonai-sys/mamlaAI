#!/bin/bash

# Log Cleanup Script
# Active logs  (*.log)      — never touched.
# Previous run (*.prev.log) — never touched (one per type, always fresh).
# Gunicorn access rotations (gunicorn-access.log.YYYY-MM-DD) — deleted after RETENTION_DAYS.
# Legacy timestamp archives (*.YYYY-MM-DD_HHMM.log, DD-MM-YYYY_*.log) — deleted after RETENTION_DAYS.
# Run via cron: 0 2 * * * /path/to/cleanup_logs.sh

PROJECT_ROOT="/home/pronoys/products/sessioned_AiAdalat/Adalatai_ground_zero"
LOG_DIR="$PROJECT_ROOT/logs"
RETENTION_DAYS=3

echo "Cleaning up archived log files older than $RETENTION_DAYS days..."

if [ ! -d "$LOG_DIR" ]; then
    echo "Error: log directory not found: $LOG_DIR"
    exit 1
fi

BEFORE_SIZE=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)

# Delete old archives in logs/ and logs/dev/ (maxdepth 2 covers the dev/ subdir)
DELETED_COUNT=$(
    find "$LOG_DIR" -maxdepth 2 -type f \( \
        -name "gunicorn-access.log.????-??-??" \
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
find "$LOG_DIR" -maxdepth 2 -type f -name "*.log" ! -name "*.????-??-??_????.log" \
    ! -name "gunicorn-access.log.????-??-??" \
    ! -name "??-??-????_*.log" \
    | sort | while read -r f; do
        size=$(du -sh "$f" 2>/dev/null | cut -f1)
        echo "  $f ($size)"
    done
echo ""
echo "[$(date)] Cleanup complete"
