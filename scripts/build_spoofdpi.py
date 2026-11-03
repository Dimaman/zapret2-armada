#!/usr/bin/env python3
"""Pin and extract the upstream Linux ARM64 SpoofDPI release."""
import hashlib
import io
from pathlib import Path
import tarfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.5.5"
URL = "https://github.com/xvzc/spoofdpi/releases/download/v1.5.5/spoofdpi_1.5.5_linux_arm64.tar.gz"
SHA256 = "b8b389314c5906247a6ab209a81599c27a4766c400ba30af7de29fd1becd5c24"
LICENSE_URL = "https://raw.githubusercontent.com/xvzc/spoofdpi/v1.5.5/LICENSE"


def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "spoofdpi-armada-build"}), timeout=120) as response:
                return response.read()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def main():
    archive = get(URL)
    if hashlib.sha256(archive).hexdigest() != SHA256:
        raise ValueError("SpoofDPI release checksum mismatch")
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        binaries = [m for m in tar.getmembers() if m.isfile() and Path(m.name).name == "spoofdpi"]
        if len(binaries) != 1 or binaries[0].size > 100_000_000:
            raise ValueError("Unexpected SpoofDPI archive contents")
        binary = tar.extractfile(binaries[0]).read()
    if binary[:6] != b"\x7fELF\x02\x01" or binary[18:20] != b"\xb7\x00":
        raise ValueError("Expected ARM64 ELF")
    path = ROOT / "bin/spoofdpi"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(binary)
    path.chmod(0o755)
    license_text = get(LICENSE_URL).decode()
    if "Apache License" not in license_text:
        raise ValueError("SpoofDPI license missing")
    (ROOT / "SPOOFDPI_LICENSE").write_text(license_text)
    print(f"SpoofDPI {VERSION} ARM64, release sha256 {SHA256}")


if __name__ == "__main__":
    main()
