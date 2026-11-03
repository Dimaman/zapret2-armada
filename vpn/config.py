"""Strict configuration and root-only storage for the Hysteria2 client."""
import copy
import ipaddress
import json
from pathlib import Path
import re

from backend.config_manager import atomic_write

DEFAULT = {
    "schema": 1, "enabled": False, "autostart": False,
    "server": "", "port": 8443, "auth": "", "obfs_password": "",
    "sni": "", "insecure": False,
}


def validate(value):
    if not isinstance(value, dict) or set(value) != set(DEFAULT) or value["schema"] != 1:
        raise ValueError("Unsupported VPN configuration")
    c = copy.deepcopy(value)
    for key in ("enabled", "autostart", "insecure"):
        if type(c[key]) is not bool:
            raise ValueError(f"{key} must be boolean")
    if type(c["port"]) is not int or not 1 <= c["port"] <= 65535:
        raise ValueError("Port must be 1..65535")
    for key, limit in (("server", 253), ("sni", 253), ("auth", 1024), ("obfs_password", 1024)):
        if not isinstance(c[key], str) or len(c[key].encode()) > limit or any(ord(ch) < 32 for ch in c[key]):
            raise ValueError(f"Invalid {key}")
    if c["server"]:
        try:
            ipaddress.ip_address(c["server"])
        except ValueError:
            if not re.fullmatch(r"(?=.{1,253}$)[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+", c["server"]):
                raise ValueError("Server must be an IP address or DNS name")
    if c["sni"] and not re.fullmatch(r"(?=.{1,253}$)[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+", c["sni"]):
        raise ValueError("SNI must be a DNS name")
    if c["enabled"] and not (c["server"] and c["auth"]):
        raise ValueError("Server and authentication are required")
    return c


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.path = self.root / "settings.json"
        if not self.path.exists():
            self.save(DEFAULT)

    def load(self):
        if self.path.stat().st_size > 8192:
            raise ValueError("VPN settings are too large")
        return validate(json.loads(self.path.read_text()))

    def save(self, c):
        atomic_write(self.path, json.dumps(validate(c), ensure_ascii=False, indent=2) + "\n", 0o600)


def public(c):
    return {"enabled": c["enabled"], "autostart": c["autostart"],
            "server": c["server"], "port": c["port"], "sni": c["sni"],
            "insecure": c["insecure"], "auth_set": bool(c["auth"]),
            "obfs_set": bool(c["obfs_password"]),
            "configured": bool(c["server"] and c["auth"])}
