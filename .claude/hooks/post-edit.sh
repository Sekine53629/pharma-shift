#!/bin/bash
# PostToolUse hook for Edit|Write
# Runs Django tests or TypeScript checks based on modified file

INPUT=$(cat)

# Extract file_path from tool input JSON using Python
FILE_PATH=$(echo "$INPUT" | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    fp = data.get('tool_input', data).get('file_path', '')
    print(fp)
except Exception:
    print('')
" 2>/dev/null) || FILE_PATH=""

# Normalize path separators (Windows backslash to Unix forward slash)
FILE_PATH=$(echo "$FILE_PATH" | tr '\\' '/')

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Django test for backend Python files in apps/
if echo "$FILE_PATH" | grep -qE 'backend/apps/[^/]+/.*\.py$'; then
    APP_NAME=$(echo "$FILE_PATH" | sed -E 's|.*backend/apps/([^/]+)/.*|\1|')
    if [ -n "$APP_NAME" ]; then
        echo "[hook] Running Django tests: apps.${APP_NAME}"
        TEST_OUTPUT=$(cd "$PROJECT_ROOT/backend" && python manage.py test "apps.${APP_NAME}" --failfast -v1 2>&1) || true
        echo "$TEST_OUTPUT" | tail -8
        if echo "$TEST_OUTPUT" | grep -q "^OK"; then
            echo "[hook] PASSED: apps.${APP_NAME}"
        elif echo "$TEST_OUTPUT" | grep -q "FAILED"; then
            echo "[hook] FAILED: apps.${APP_NAME}"
        fi
    fi
fi

# TypeScript check for frontend files
if echo "$FILE_PATH" | grep -qE 'frontend/.*\.tsx?$'; then
    echo "[hook] Running TypeScript type check..."
    TSC_OUTPUT=$(cd "$PROJECT_ROOT/frontend" && npx tsc --noEmit 2>&1) || true
    ERRORS=$(echo "$TSC_OUTPUT" | grep -c "error TS" || true)
    if [ "$ERRORS" -eq 0 ]; then
        echo "[hook] TypeScript: PASSED"
    else
        echo "$TSC_OUTPUT" | grep "error TS" | tail -10
        echo "[hook] TypeScript: ${ERRORS} error(s) found"
    fi
fi

exit 0
