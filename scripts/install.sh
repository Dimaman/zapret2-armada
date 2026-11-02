#!/bin/bash
# Optional desktop terminal setup; Decky also exposes this same fixed operation.
set -euo pipefail
cd "$(dirname "$0")/.."
[[ $EUID -eq 0 ]] || { echo 'Run with sudo after inspecting the release.' >&2; exit 1; }
exec /usr/bin/python3 -c 'from pathlib import Path; from backend.zapret_manager import ZapretManager; ZapretManager(Path.cwd()).install()'
