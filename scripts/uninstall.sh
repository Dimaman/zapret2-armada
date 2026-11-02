#!/bin/bash
# Removes only owned service/modules file/firewall table; retains settings/logs.
set -euo pipefail
cd "$(dirname "$0")/.."
[[ $EUID -eq 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
exec /usr/bin/python3 -c 'from pathlib import Path; from backend.zapret_manager import ZapretManager; ZapretManager(Path.cwd()).uninstall()'
