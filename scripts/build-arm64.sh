#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ $(uname -m) == aarch64 ]]; then
  python3 scripts/build-engine.py
else
  export TARGET=aarch64-linux-gnu
  export CC=aarch64-linux-gnu-gcc
  export AR=aarch64-linux-gnu-ar
  export RANLIB=aarch64-linux-gnu-ranlib
  python3 scripts/build-engine.py
fi
