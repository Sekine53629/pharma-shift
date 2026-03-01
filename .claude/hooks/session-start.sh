#!/bin/bash
# SessionStart hook: restore context from previous session

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "========================================"
echo "  pharma-shift Session Recovery"
echo "========================================"

# Show CONTEXT.md if exists
if [ -f "$PROJECT_ROOT/CONTEXT.md" ]; then
    echo ""
    echo "--- CONTEXT.md (last session state) ---"
    head -60 "$PROJECT_ROOT/CONTEXT.md"
    LINES=$(wc -l < "$PROJECT_ROOT/CONTEXT.md")
    if [ "$LINES" -gt 60 ]; then
        echo "... (truncated, $LINES total lines)"
    fi
    echo "--- End CONTEXT.md ---"
else
    echo ""
    echo "No CONTEXT.md found (fresh start)"
fi

echo ""
echo "Branch: $(git -C "$PROJECT_ROOT" branch --show-current 2>/dev/null || echo 'unknown')"
echo ""
echo "Uncommitted changes:"
git -C "$PROJECT_ROOT" status --short 2>/dev/null || echo "  (none)"
echo ""
echo "Recent commits:"
git -C "$PROJECT_ROOT" log --oneline -5 2>/dev/null || echo "  (none)"
echo "========================================"

exit 0
