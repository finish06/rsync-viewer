#!/usr/bin/env bash
# Install git hooks for development.
# Run once after cloning: ./scripts/install-hooks.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK_DIR="$REPO_ROOT/.git/hooks"

mkdir -p "$HOOK_DIR"

cat > "$HOOK_DIR/pre-commit" << 'HOOK'
#!/usr/bin/env bash
# Pre-commit hook: ruff format check, ruff lint, pytest
set -euo pipefail

# Use project venv if available (requires Python 3.11+)
REPO_ROOT="$(git rev-parse --show-toplevel)"
if [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
    # shellcheck source=/dev/null
    source "$REPO_ROOT/.venv/bin/activate"
fi

echo "[pre-commit] Running ruff format check..."
python3 -m ruff format --check . || {
    echo "[pre-commit] FAIL: Run 'python3 -m ruff format .' to fix formatting"
    exit 1
}

echo "[pre-commit] Running ruff lint..."
python3 -m ruff check . || {
    echo "[pre-commit] FAIL: Fix lint errors above"
    exit 1
}

echo "[pre-commit] Running pytest..."
python3 -m pytest --tb=short -q || {
    echo "[pre-commit] FAIL: Tests must pass before committing"
    exit 1
}

echo "[pre-commit] All checks passed"
HOOK

chmod +x "$HOOK_DIR/pre-commit"
echo "Pre-commit hook installed to $HOOK_DIR/pre-commit"
