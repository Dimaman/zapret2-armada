#!/usr/bin/env python3
"""Fetch a pinned upstream ARM64 binary and license; never trust a moving URL."""
import hashlib
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
VERSION = "2.13.0"
URL = "https://github.com/HyNetworks/hysteria/releases/download/app/v2.13.0/hysteria-linux-arm64"
SHA256 = "a68a61a84452ca250ce0368202521965ca9cc9d801a404f1dc9008ac6cf677a7"
LICENSE_URL = "https://raw.githubusercontent.com/HyNetworks/hysteria/ca8fbd874fd6ca82413948de6dc5924405e103e1/LICENSE.md"


def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "hysteria2-armada-build"}), timeout=120) as response:
                return response.read()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def main():
    binary = get(URL)
    assert hashlib.sha256(binary).hexdigest() == SHA256, "Hysteria binary digest mismatch"
    assert binary[:6] == b"\x7fELF\x02\x01" and binary[18:20] == b"\xb7\x00", "Expected ARM64 ELF"
    path = ROOT / "bin/hysteria"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(binary)
    path.chmod(0o755)
    license_text = get(LICENSE_URL).decode("utf-8")
    assert "Permission is hereby granted" in license_text
    (ROOT / "HYSTERIA_LICENSE.md").write_text(license_text)
    print(f"Hysteria2 {VERSION}, ARM64, sha256 {SHA256}")


if __name__ == "__main__":
    main()
