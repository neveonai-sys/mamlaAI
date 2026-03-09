#!/bin/bash

# Log Cleanup Script
# Removes log files older than 3 days to prevent disk space issues
# Run this script via cron: 0 2 * * * /path/to/cleanup_logs.sh

PROJECT_ROOT="/home/pronoys/products/sessioned_AiAdalat/Adalatai_ground_zero"
LOG_DIR="$PROJECT_ROOT/logs"
RETENTION_DAYS=3

echo "🧹 Cleaning up old log files..."
echo "================================================"
echo "Log directory: $LOG_DIR"
echo "Retention period: $RETENTION_DAYS days"
echo ""

# Check if log directory exists
if [ ! -d "$LOG_DIR" ]; then
    echo "❌ Error: Log directory does not exist: $LOG_DIR"
    exit 1
fi

# Count files before cleanup
BEFORE_COUNT=$(find "$LOG_DIR" -type f -name "*.log*" | wc -l)
BEFORE_SIZE=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)

echo "📊 Current status:"
echo "   - Total log files: $BEFORE_COUNT"
echo "   - Total size: $BEFORE_SIZE"
echo ""

# Remove log files older than retention period
echo "🗑️  Removing files older than $RETENTION_DAYS days..."

# Find and delete old log files
DELETED_COUNT=$(find "$LOG_DIR" -type f -name "*.log*" -mtime +$RETENTION_DAYS -print -delete 2>/dev/null | wc -l)

# Count files after cleanup
AFTER_COUNT=$(find "$LOG_DIR" -type f -name "*.log*" | wc -l)
AFTER_SIZE=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)

echo ""
echo "✅ Cleanup complete:"
echo "   - Files deleted: $DELETED_COUNT"
echo "   - Files remaining: $AFTER_COUNT"
echo "   - Current size: $AFTER_SIZE"
echo ""

# List current log files (for verification)
echo "📋 Current log files:"
find "$LOG_DIR" -type f -name "*.log*" -mtime -$RETENTION_DAYS -exec ls -lh {} \; | awk '{print "   - " $9 " (" $5 ")"}'

echo ""
echo "[$(date)] Log cleanup completed successfully"
