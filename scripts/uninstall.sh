#!/bin/bash
# Removes only the owned VPN service and its secrets.
set -euo pipefail
cd "$(dirname "$0")/.."
[[ $EUID -eq 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
exec /usr/bin/python3 -c 'from pathlib import Path; from vpn.manager import Manager; Manager(Path.cwd()).uninstall()'
