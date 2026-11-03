"""Bounded root operations. No arbitrary command, URL, or file path RPC."""
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import threading
import time

from backend.commands import run
from backend.config_manager import atomic_write
from .config import DEFAULT, Store, public, validate

ROOT = Path("/var/lib/hysteria2-armada")
UNIT = Path("/etc/systemd/system/hysteria2-armada.service")
NAME = "hysteria2-armada.service"
TUN = Path("/sys/class/net/hy2armada")
OWNER = "# hysteria2-armada-managed-v1"
OLD_UNIT = Path("/etc/systemd/system/zapret2-armada.service")
OLD_MODULES = Path("/etc/modules-load.d/zapret2-armada.conf")
OLD_OWNER = "# zapret2-armada-managed-v1"


def endpoint(server, port, resolver=socket.getaddrinfo):
    """Resolve before installing a default TUN route, then pin the peer IP."""
    try:
        ip = ipaddress.ip_address(server)
    except ValueError:
        addresses = resolver(server, port, type=socket.SOCK_DGRAM)
        if not addresses:
            raise RuntimeError("Server DNS returned no addresses")
        # Prefer IPv4 to avoid selecting an IPv6 link that is not configured.
        addresses = sorted(addresses, key=lambda item: item[0] != socket.AF_INET)
        ip = ipaddress.ip_address(addresses[0][4][0])
    if ip.is_unspecified or ip.is_multicast or ip.is_loopback:
        raise ValueError("Server address is not a reachable endpoint")
    address = f"[{ip}]:{port}" if ip.version == 6 else f"{ip}:{port}"
    return ip, address


def client_config(c, ip, address):
    route = {"ipv4": ["0.0.0.0/0"], "ipv6": ["::/0"]}
    route["ipv4Exclude" if ip.version == 4 else "ipv6Exclude"] = [f"{ip}/{ip.max_prefixlen}"]
    tls = {"insecure": c["insecure"]}
    if c["sni"] or not _is_ip(c["server"]):
        tls["sni"] = c["sni"] or c["server"]
    data = {"server": address, "auth": c["auth"], "tls": tls,
            "tun": {"name": "hy2armada", "mtu": 1400,
                    "address": {"ipv4": "172.31.250.1/30", "ipv6": "fd7a:115c:a1e0::1/126"},
                    "route": route}}
    if c["obfs_password"]:
        data["obfs"] = {"type": "salamander", "salamander": {"password": c["obfs_password"]}}
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"  # JSON is YAML syntax.


def _is_ip(value):
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


class Manager:
    def __init__(self, plugin, root=ROOT, runner=run, unit=UNIT, tun=TUN):
        self.plugin, self.root, self.run = Path(plugin), Path(root), runner
        self.unit, self.tun = Path(unit), Path(tun)
        self.lock = threading.RLock()
        self.store = Store(self.root)
        self.error = ""

    def ctl(self, *args, check=True):
        return self.run(["/usr/bin/systemctl", *args, NAME], check=check, timeout=30)

    def installed(self):
        return self.unit.exists() and self.unit.read_text().startswith(OWNER)

    def active(self):
        return self.installed() and self.ctl("is-active", check=False).stdout.strip() == "active" and self.tun.exists()

    def status(self):
        c = self.store.load()
        return {"config": public(c), "active": self.active(), "installed": self.installed(),
                "version": "0.3.0", "error": self.error}

    def retire_old_service(self):
        # Upgrade from the prior plugin: never touch files with another owner.
        if OLD_UNIT.exists():
            if not OLD_UNIT.read_text().startswith(OLD_OWNER):
                raise RuntimeError("Refusing to replace a foreign Zapret service")
            self.run(["/usr/bin/systemctl", "disable", "--now", "zapret2-armada.service"], check=False)
            OLD_UNIT.unlink()
        if OLD_MODULES.exists():
            if not OLD_MODULES.read_text().startswith(OLD_OWNER):
                raise RuntimeError("Refusing to remove a foreign modules file")
            OLD_MODULES.unlink()
        # Old queue bypasses packets without a listener. Remove only our own table.
        if Path("/usr/sbin/nft").exists():
            result = self.run(["/usr/sbin/nft", "-j", "list", "table", "inet", "zapret2_armada"], check=False)
            if result.returncode == 0:
                tables = json.loads(result.stdout).get("nftables", [])
                if any(x.get("table", {}).get("comment") == "zapret2-armada-managed-v1" for x in tables):
                    self.run(["/usr/sbin/nft", "delete", "table", "inet", "zapret2_armada"])
        self.run(["/usr/bin/systemctl", "daemon-reload"])

    def install(self):
        if os.geteuid() != 0:
            raise RuntimeError("Decky root flag is required")
        if self.unit.exists() and not self.installed():
            raise RuntimeError("Refusing to overwrite a foreign service")
        binary = self.plugin / "bin/hysteria"
        if not binary.is_file():
            raise RuntimeError("ARM64 Hysteria2 executable is missing")
        with binary.open("rb") as f:
            header = f.read(20)
        if header[:6] != b"\x7fELF\x02\x01" or header[18:20] != b"\xb7\x00":
            raise RuntimeError("ARM64 Hysteria2 executable is missing")
        if not Path("/dev/net/tun").exists():
            raise RuntimeError("TUN device is unavailable in this kernel")
        self.retire_old_service()
        app = self.root / "app"
        app.mkdir(parents=True, exist_ok=True)
        shutil.copy2(binary, app / "hysteria")
        (app / "hysteria").chmod(0o755)
        atomic_write(self.unit, (self.plugin / "configs/hysteria2-armada.service").read_text(), 0o644)
        self.run(["/usr/bin/systemctl", "daemon-reload"])

    def start(self, c):
        if not self.installed():
            self.install()
        ip, address = endpoint(c["server"], c["port"])
        atomic_write(self.root / "client.yaml", client_config(c, ip, address), 0o600)
        self.ctl("enable" if c["autostart"] else "disable")
        self.ctl("reset-failed", check=False)
        self.ctl("restart")
        for _ in range(100):
            if self.active():
                return
            time.sleep(0.1)
        self.ctl("stop", check=False)
        raise RuntimeError("VPN did not establish a TUN interface. Check the server, credentials and logs")

    def stop(self):
        if self.installed():
            self.ctl("stop")
            self.ctl("disable")
            if self.ctl("is-active", check=False).stdout.strip() == "active" or self.tun.exists():
                raise RuntimeError("VPN did not stop; check the service logs")

    def apply(self, candidate):
        candidate = validate(candidate)
        previous = self.store.load()
        try:
            if candidate["enabled"]:
                self.start(candidate)
            else:
                self.stop()
        except Exception:
            if previous["enabled"]:
                self.start(previous)
            else:
                self.stop()
            raise
        try:
            self.store.save(candidate)
        except Exception:
            if previous["enabled"]:
                self.start(previous)
            else:
                self.stop()
            raise

    def dispatch(self, operation, payload):
        if not isinstance(operation, str) or not isinstance(payload, dict):
            raise ValueError("Invalid operation")
        if operation == "status":
            return self.status()
        with self.lock:
            c = self.store.load()
            if operation == "save_server":
                allowed = {"server", "port", "auth", "obfs_password", "sni", "insecure"}
                if not set(payload) <= allowed or not payload:
                    raise ValueError("Invalid server fields")
                c.update(payload)
                self.apply(c)
            elif operation == "set_enabled":
                if set(payload) != {"enabled"} or type(payload["enabled"]) is not bool:
                    raise ValueError("Expected VPN switch")
                c["enabled"] = payload["enabled"]
                self.apply(c)
            elif operation == "set_autostart":
                if set(payload) != {"autostart"} or type(payload["autostart"]) is not bool:
                    raise ValueError("Expected autostart switch")
                c["autostart"] = payload["autostart"]
                self.apply(c)
            elif operation == "logs":
                if payload:
                    raise ValueError("No parameters expected")
                r = self.run(["/usr/bin/journalctl", "-u", NAME, "-n", "60", "--no-pager", "--output=cat"], check=False)
                contents = (r.stdout or r.stderr)[-12000:]
                for secret in (c["auth"], c["obfs_password"]):
                    if secret:
                        contents = contents.replace(secret, "[redacted]")
                return {"text": contents}
            else:
                raise ValueError("Unknown operation")
            self.error = ""
            return self.status()

    def uninstall(self):
        with self.lock:
            self.stop()
            if self.installed():
                self.unit.unlink()
                self.run(["/usr/bin/systemctl", "daemon-reload"])
            if self.root.exists():
                shutil.rmtree(self.root)
