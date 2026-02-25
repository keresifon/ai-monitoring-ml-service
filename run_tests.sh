#!/bin/bash
# Run tests with PYTHONNOUSERSITE=1 so Python uses only venv packages.
# This prevents ~/.local packages from overriding venv (e.g. httpx/starlette).
set -e
cd "$(dirname "$0")"
export PYTHONNOUSERSITE=1

if [ ! -d "venv" ]; then
    echo "Creating venv..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
pip install -q pytest

exec pytest tests/ -v "$@"
