#!/bin/sh
#
# Installs governance pre-commit hook.
# Run this after cloning:
#   sh .codex/validators/install_hooks.sh
#

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$REPO_ROOT" ]; then
    echo "ERROR: Not in a git repository."
    exit 1
fi

HOOK_DIR="${REPO_ROOT}/.git/hooks"
HOOK_FILE="${HOOK_DIR}/pre-commit"

if [ -f "$HOOK_FILE" ]; then
    echo "Pre-commit hook already exists at ${HOOK_FILE}"
    echo "Overwrite? (y/N)"
    read -r answer
    if [ "$answer" != "y" ] && [ "$answer" != "Y" ]; then
        echo "Aborted."
        exit 0
    fi
fi

cat > "$HOOK_FILE" << 'HOOKEOF'
#!/bin/sh
echo ""
echo "Running governance gates..."
echo ""
REPO_ROOT="$(git rev-parse --show-toplevel)"
python3 "${REPO_ROOT}/.codex/validators/run_governance_gate.py"
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "COMMIT BLOCKED: Governance gates failed."
    echo "Fix the issues above, then try again."
    echo ""
    exit 1
fi
echo ""
exit 0
HOOKEOF

chmod +x "$HOOK_FILE"
echo "Governance pre-commit hook installed at ${HOOK_FILE}"
