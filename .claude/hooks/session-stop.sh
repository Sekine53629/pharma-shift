#!/bin/bash
# Stop hook: auto-checkpoint CONTEXT.md before session ends

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTEXT_FILE="$PROJECT_ROOT/CONTEXT.md"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')

# Backup existing CONTEXT.md (keep last 5 backups)
if [ -f "$CONTEXT_FILE" ]; then
    cp "$CONTEXT_FILE" "$PROJECT_ROOT/.claude/context_backup_$(date '+%Y%m%d_%H%M%S').md"
    # Clean old backups (keep most recent 5)
    ls -t "$PROJECT_ROOT/.claude/context_backup_"*.md 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
fi

# Append git state snapshot to CONTEXT.md
{
    echo ""
    echo "## Auto-checkpoint at Session End ($TIMESTAMP)"
    echo ""
    echo "### Git State"
    echo '```'
    echo "Branch: $(git -C "$PROJECT_ROOT" branch --show-current 2>/dev/null)"
    echo "Last commit: $(git -C "$PROJECT_ROOT" log --oneline -1 2>/dev/null)"
    echo ""
    echo "Uncommitted changes:"
    git -C "$PROJECT_ROOT" status --short 2>/dev/null
    echo '```'
} >> "$CONTEXT_FILE"

# Auto-commit the context file
git -C "$PROJECT_ROOT" add "$CONTEXT_FILE" 2>/dev/null
git -C "$PROJECT_ROOT" commit -m "auto-checkpoint: session end context save" --no-verify 2>/dev/null || true

echo "[hook] Session context saved to CONTEXT.md"

exit 0
