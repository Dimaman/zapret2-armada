#!/usr/bin/env python3
"""Deterministic Decky ZIP, pinned upstream binary and SHA256 checksums."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "release"
PREFIX = "zapret2-armada/"  # Preserve Decky's existing plugin directory on upgrade.
VERSION = "0.3.0"


def entries(names):
    for name in names:
        path = ROOT / name
        if not path.exists():
            raise FileNotFoundError(path)
        if path.is_file():
            yield path
        else:
            yield from sorted(p for p in path.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")


def write(z, path):
    name = PREFIX + str(path.relative_to(ROOT))
    info = zipfile.ZipInfo(name, (2026, 11, 3, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = ((0o100755 if path.name in ("hysteria", "spoofdpi") or path.suffix == ".sh" else 0o100644) << 16)
    z.writestr(info, path.read_bytes())


def validate_zip(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        names = z.namelist()
        assert len(names) == len(set(names))
        assert all(n.startswith(PREFIX) and ".." not in Path(n).parts for n in names)
        for name in ("plugin.json", "main.py", "vpn/config.py", "vpn/manager.py", "dpi/manager.py",
                     "configs/hysteria2-armada.service", "configs/spoofdpi-armada.service", "dist/index.js", "bin/hysteria", "bin/spoofdpi", "SPOOFDPI_LICENSE",
                     "LICENSE", "HYSTERIA_LICENSE.md", "THIRD_PARTY_NOTICES.md",
                     "build/frontend-licenses/decky-api-LICENSE",
                     "build/frontend-licenses/tslib-LICENSE.txt"):
            assert PREFIX + name in names, name
        assert not any("nfqws" in n or "zapret2-armada.service" in n for n in names)
        binary = z.read(PREFIX + "bin/hysteria")
        from build_hysteria import SHA256
        assert hashlib.sha256(binary).hexdigest() == SHA256
        assert binary[:6] == b"\x7fELF\x02\x01" and binary[18:20] == b"\xb7\x00"
        assert (z.getinfo(PREFIX + "bin/hysteria").external_attr >> 16) & 0o111
        assert json.loads(z.read(PREFIX + "plugin.json"))["flags"] == ["root"]
        spoof = z.read(PREFIX + "bin/spoofdpi")
        assert spoof[:6] == b"\x7fELF\x02\x01" and spoof[18:20] == b"\xb7\x00"
        assert (z.getinfo(PREFIX + "bin/spoofdpi").external_attr >> 16) & 0o111
        print(f"Package validated: {path.name}, {len(names)} entries")


def package():
    from subprocess import run
    run([sys.executable, str(ROOT / "scripts/validate-project.py")], check=True)
    OUT.mkdir(exist_ok=True)
    runtime = ["plugin.json", "main.py", "vpn", "dpi", "backend/commands.py", "backend/config_manager.py",
               "backend/__init__.py", "configs/hysteria2-armada.service", "configs/spoofdpi-armada.service", "dist/index.js",
               "bin/hysteria", "bin/spoofdpi", "SPOOFDPI_LICENSE", "LICENSE", "HYSTERIA_LICENSE.md", "THIRD_PARTY_NOTICES.md",
               "build/frontend-licenses", "scripts/uninstall.sh"]
    source = ["plugin.json", "main.py", "vpn", "dpi", "backend/commands.py", "backend/config_manager.py",
              "backend/__init__.py", "configs/hysteria2-armada.service", "configs/spoofdpi-armada.service", "src/index.tsx",
              "src/api.ts", "scripts/build_hysteria.py", "scripts/build_spoofdpi.py", "scripts/package.py",
              "scripts/validate-project.py", "scripts/uninstall.sh", "tests/test_vpn.py", "tests/test_dpi.py",
              ".github/workflows/ci.yml", ".github/workflows/release.yml",
              "package.json", "package-lock.json", "rollup.config.js", "tsconfig.json",
              "README.md", "CHANGELOG.md", "docs/INSTALL_RU.md", "docs/RELEASE_NOTES.md",
              "LICENSE", "HYSTERIA_LICENSE.md", "SPOOFDPI_LICENSE", "THIRD_PARTY_NOTICES.md"]
    archive = OUT / f"spoofdpi-armada-v{VERSION}-arm64.zip"
    with zipfile.ZipFile(archive, "w") as z:
        for path in entries(runtime):
            write(z, path)
    src = OUT / f"spoofdpi-armada-v{VERSION}-source.zip"
    with zipfile.ZipFile(src, "w") as z:
        for path in entries(source):
            write(z, path)
    validate_zip(archive)
    sums = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in (archive, src))
    (OUT / "SHA256SUMS").write_text(sums)
    print(sums)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        validate_zip(Path(sys.argv[1]))
    else:
        package()
