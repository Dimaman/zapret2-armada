"""Owned, bounded SpoofDPI TUN lifecycle. No arbitrary shell commands from UI."""
import json
import os
from pathlib import Path
import shutil
import threading
import time

from backend.commands import run
from backend.config_manager import atomic_write

ROOT = Path("/var/lib/spoofdpi-armada")
UNIT = Path("/etc/systemd/system/spoofdpi-armada.service")
NAME = "spoofdpi-armada.service"
TUN = Path("/sys/class/net/tun-spoofdpi")
OWNER = "# spoofdpi-armada-managed-v1"
PROFILES = {"sni", "strong"}
DEFAULT = {"enabled": False, "profile": "sni"}


def validate(data):
    if not isinstance(data, dict) or set(data) != set(DEFAULT):
        raise ValueError("Invalid DPI settings")
    if type(data["enabled"]) is not bool or data["profile"] not in PROFILES:
        raise ValueError("Invalid DPI mode")
    return dict(data)


def config(profile):
    if profile not in PROFILES:
        raise ValueError("Invalid DPI profile")
    # UDP defaults to direct local forwarding: avoids fake packets in games.
    if profile == "sni":
        https = 'split-mode = "sni"\nfake-count = 2\n'
    else:
        https = 'split-mode = "chunk"\nchunk-size = 1\ndisorder = true\nfake-count = 5\n'
    return '[app]\nmode = "tun"\nno-tui = true\nlog-level = "info"\n\n[https]\n' + https + '\n[udp]\nfake-count = 0\n'


class DpiManager:
    def __init__(self, plugin, root=ROOT, unit=UNIT, tun=TUN, runner=run):
        self.plugin, self.root, self.unit, self.tun = map(Path, (plugin, root, unit, tun))
        self.run = runner
        self.lock = threading.RLock()
        self.path = self.root / "settings.json"
        self.error = ""
        if not self.path.exists():
            self.save(DEFAULT)

    def load(self):
        if self.path.stat().st_size > 4096:
            raise ValueError("DPI settings too large")
        return validate(json.loads(self.path.read_text()))

    def save(self, data):
        atomic_write(self.path, json.dumps(validate(data)) + "\n", 0o600)

    def ctl(self, action, check=True):
        return self.run(["/usr/bin/systemctl", action, NAME], check=check, timeout=30)

    def installed(self):
        return self.unit.exists() and self.unit.read_text().startswith(OWNER)

    def active(self):
        return self.installed() and self.ctl("is-active", check=False).stdout.strip() == "active" and self.tun.exists()

    def status(self):
        return {**self.load(), "active": self.active(), "error": self.error}

    def install(self):
        if os.geteuid() != 0:
            raise RuntimeError("Decky root flag is required")
        if self.unit.exists() and not self.installed():
            raise RuntimeError("Refusing to overwrite a foreign service")
        if not Path("/dev/net/tun").exists():
            raise RuntimeError("TUN device is unavailable in this kernel")
        binary = self.plugin / "bin/spoofdpi"
        if not binary.is_file():
            raise RuntimeError("ARM64 SpoofDPI executable is missing")
        with binary.open("rb") as f:
            header = f.read(20)
            if header[:6] != b"\x7fELF\x02\x01" or header[18:20] != b"\xb7\x00":
                raise RuntimeError("Expected ARM64 SpoofDPI executable")
        app = self.root / "app"
        app.mkdir(parents=True, exist_ok=True)
        shutil.copy2(binary, app / "spoofdpi")
        (app / "spoofdpi").chmod(0o755)
        atomic_write(self.unit, (self.plugin / "configs/spoofdpi-armada.service").read_text(), 0o644)
        self.run(["/usr/bin/systemctl", "daemon-reload"])

    def start(self, data):
        if not self.installed():
            self.install()
        atomic_write(self.root / "spoofdpi.toml", config(data["profile"]), 0o600)
        self.ctl("reset-failed", check=False)
        self.ctl("restart")
        for _ in range(100):
            if self.active():
                return
            time.sleep(0.1)
        self.ctl("stop", check=False)
        raise RuntimeError("SpoofDPI TUN did not start. Check the logs")

    def stop(self):
        if self.installed():
            self.ctl("stop")
            self.ctl("disable")
            if self.ctl("is-active", check=False).stdout.strip() == "active" or self.tun.exists():
                raise RuntimeError("SpoofDPI did not stop")

    def apply(self, new):
        new = validate(new)
        old = self.load()
        try:
            if new["enabled"]:
                self.start(new)
            else:
                self.stop()
            self.save(new)
        except Exception:
            if old["enabled"]:
                self.start(old)
            else:
                self.stop()
            raise
        self.error = ""
        return self.status()

    def dispatch(self, op, payload):
        if not isinstance(payload, dict):
            raise ValueError("Invalid DPI operation")
        with self.lock:
            data = self.load()
            if op == "set_enabled" and set(payload) == {"enabled"} and type(payload["enabled"]) is bool:
                data["enabled"] = payload["enabled"]
                return self.apply(data)
            if op == "set_profile" and set(payload) == {"profile"} and payload["profile"] in PROFILES:
                data["profile"] = payload["profile"]
                return self.apply(data)
            if op == "logs" and not payload:
                r = self.run(["/usr/bin/journalctl", "-u", NAME, "-n", "60", "--no-pager", "--output=cat"], check=False)
                return {"text": (r.stdout or r.stderr)[-12000:]}
            raise ValueError("Unknown DPI operation")

    def uninstall(self):
        with self.lock:
            self.stop()
            if self.installed():
                self.unit.unlink()
                self.run(["/usr/bin/systemctl", "daemon-reload"])
            if self.root.exists():
                shutil.rmtree(self.root)
