#!/usr/bin/env bash
set -euo pipefail

# Remove build artifacts so the tree reflects only tracked source files.
rm -rf dist build

# Remove Python cache directories and bytecode files that accumulate during development.
find . -name "__pycache__" -type d -prune -exec rm -rf {} +
find . -name "*.pyc" -delete

# Optionally purge transient market cache to force fresh data.
[ -d data/cache ] && rm -rf data/cache
