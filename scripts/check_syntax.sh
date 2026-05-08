#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile server_postgres.py
node --check static/app.js

echo "Syntax checks passed (Python + JavaScript)."
