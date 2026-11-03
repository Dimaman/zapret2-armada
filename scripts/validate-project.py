#!/usr/bin/env python3
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
plugin = json.loads((root / "plugin.json").read_text())
package = json.loads((root / "package.json").read_text())
assert plugin["api_version"] == 1 and plugin["flags"] == ["root"]
assert package["name"] == "hysteria2-armada" and package["version"] == "0.2.0"
assert "GNU GENERAL PUBLIC LICENSE" in (root / "LICENSE").read_text()
for name in ("main.py", "vpn/config.py", "vpn/manager.py",
             "configs/hysteria2-armada.service", "src/index.tsx",
             "docs/INSTALL_RU.md", "HYSTERIA_LICENSE.md"):
    assert (root / name).stat().st_size > 30, name
print("Decky metadata, Hysteria2 pin, license and required files validated")
