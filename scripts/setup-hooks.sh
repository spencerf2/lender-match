#!/bin/sh

mkdir -p .git/hooks

echo "Checking for ruff in backend/.venv..."
if [ ! -x backend/.venv/bin/ruff ]; then
  echo "Missing: backend/.venv/bin/ruff"
  echo "Run: make install"
  exit 1
fi

if [ -f .git/hooks/pre-commit ]; then
  echo "Removing existing pre-commit hook..."
  rm .git/hooks/pre-commit
fi

echo "Creating new pre-commit hook..."
cat >.git/hooks/pre-commit <<'EOF'
#!/bin/sh

# The formatter re-add below stages whole files, which would silently
# commit a partially staged file's unstaged hunks -- refuse instead
partial=$(git status --porcelain | grep -E '^[MARC]M ' | cut -c4-)
if [ -n "$partial" ]; then
  echo "pre-commit: these files are only partially staged:" >&2
  echo "$partial" >&2
  echo "Stage them fully (or stash the unstaged hunks) and retry." >&2
  exit 1
fi

echo "Running formatters on project files..."
make fmt || exit 1

# Deletions excluded: a staged deletion has nothing to re-add
git diff --name-only --staged --diff-filter=d | xargs git add --
EOF
chmod +x .git/hooks/pre-commit
echo "Git hooks installed successfully!"
