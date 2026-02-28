#!/bin/bash
# Pre-compact hook: preserve session state before context compression
# This runs automatically before every compaction

CONTEXT_FILE="CONTEXT.md"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')

# Backup current CONTEXT.md if it exists
if [ -f "$CONTEXT_FILE" ]; then
    cp "$CONTEXT_FILE" ".claude/context_backup_$(date '+%Y%m%d_%H%M%S').md"
fi

# Append git state to CONTEXT.md
{
    echo ""
    echo "## Auto-captured at Compaction ($TIMESTAMP)"
    echo ""
    echo "### Git State"
    echo "\`\`\`"
    echo "Branch: $(git branch --show-current)"
    echo "Last commit: $(git log --oneline -1)"
    echo ""
    echo "Recent commits:"
    git log --oneline -10
    echo ""
    echo "Uncommitted changes:"
    git status --short
    echo "\`\`\`"
} >> "$CONTEXT_FILE"

# Auto-commit the context file
git add "$CONTEXT_FILE" 2>/dev/null
git commit -m "auto-checkpoint: pre-compact context save" --no-verify 2>/dev/null

echo "Context preserved to $CONTEXT_FILE"
