#!/bin/bash
# Enhanced verification script for VISTA Probing Judge
# Provides comprehensive objective verification (syntax, structure, JSON checks)

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

log_result() {
    local status=$1
    local message=$2
    case $status in
        "PASS")
            echo -e "${GREEN}✅ PASS:${NC} $message"
            ((PASS_COUNT++))
            ;;
        "FAIL")
            echo -e "${RED}❌ FAIL:${NC} $message"
            ((FAIL_COUNT++))
            ;;
        "WARN")
            echo -e "${YELLOW}⚠️  WARN:${NC} $message"
            ((WARN_COUNT++))
            ;;
    esac
}

echo "🔍 PROBING JUDGE - Enhanced Verification"
echo "=========================================================="

# 1. Ensure runtime/baton.next.json exists
if [ ! -f "runtime/baton.next.json" ]; then
    log_result "FAIL" "runtime/baton.next.json is missing"
else
    log_result "PASS" "runtime/baton.next.json found"
fi

# 2. Validate JSON structure
if [ -f "runtime/baton.next.json" ]; then
    validation_output=$(python3 - <<'PYCODE'
import json, sys
from pathlib import Path

path = Path("runtime/baton.next.json")
try:
    data = json.loads(path.read_text())
except Exception as exc:
    print(f"JSON_ERROR: {exc}")
    sys.exit(1)

required_fields = ["task", "builder_output", "synopsis", "patch_bundle"]
missing = [f for f in required_fields if f not in data]
if missing:
    print(f"MISSING_FIELDS: {missing}")
    sys.exit(1)

task = data["task"]
if "goal" not in task or "constraints" not in task or "success_metrics" not in task:
    print("TASK_OBJECT_INVALID")
    sys.exit(1)

print("JSON_VALID")
PYCODE
)
    if [[ "$validation_output" == *"JSON_VALID"* ]]; then
        log_result "PASS" "Baton JSON structure valid"
    else
        log_result "FAIL" "Baton JSON validation failed: $validation_output"
    fi
fi

# 3. Patch bundle validation
if [ -f "runtime/baton.next.json" ]; then
    patch_output=$(python3 - <<'PYCODE'
import json, sys
from pathlib import Path

data = json.loads(Path("runtime/baton.next.json").read_text())
patches = data.get("patch_bundle", [])

if not isinstance(patches, list):
    print("PATCH_ERROR: patch_bundle must be a list")
    sys.exit(1)

valid = 0
for patch in patches:
    if not isinstance(patch, dict):
        continue
    file_path = patch.get("file")
    diff = patch.get("diff", "")
    if file_path and (diff.startswith("@@") or diff.strip() == ""):
        valid += 1

print(f"PATCH_VALID:{valid}/{len(patches)}")
PYCODE
)
    if [[ "$patch_output" == PATCH_VALID* ]]; then
        log_result "PASS" "Patch bundle format valid ($patch_output)"
    else
        log_result "WARN" "Patch bundle issues detected: $patch_output"
    fi
fi

# 4. Run lint/syntax checks (basic)
if command -v python3 >/dev/null 2>&1; then
    python_files=$(find . -name "*.py" -not -path "./.venv/*" -not -path "*/__pycache__/*" | head -10)
    if [ -n "$python_files" ]; then
        echo -e "${BLUE}🔍 Checking Python syntax (sample)...${NC}"
        for file in $python_files; do
            if python3 -m py_compile "$file" 2>/dev/null; then
                log_result "PASS" "Python syntax ok: $file"
            else
                log_result "WARN" "Python syntax issue: $file"
            fi
        done
    fi
fi

echo "=========================================================="
echo -e "📊 SUMMARY: ${GREEN}$PASS_COUNT pass${NC}, ${YELLOW}$WARN_COUNT warn${NC}, ${RED}$FAIL_COUNT fail${NC}"

if [ "$FAIL_COUNT" -eq 0 ]; then
    echo -e "${GREEN}🎉 PROBING JUDGE: PASS${NC}"
    exit 0
else
    echo -e "${RED}❌ PROBING JUDGE: FAIL${NC}"
    exit 1
fi
