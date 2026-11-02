"""Bounded schemas and durable, atomic configuration storage."""
import copy
import ipaddress
import json
import os
from pathlib import Path
import re
import tempfile

DEFAULT_PROFILES = [
    {"id": "split-1", "name": "TLS split 1", "method": "multisplit", "position": 1, "repeats": 1},
    {"id": "disorder-1", "name": "TLS disorder 1", "method": "multidisorder", "position": 1, "repeats": 1},
    {"id": "split-2", "name": "TLS split 2", "method": "multisplit", "position": 2, "repeats": 1},
]
DEFAULT = {"schema": 1, "enabled": False, "autostart": False, "udp": False,
           "language": "ru", "active": "split-1", "profiles": DEFAULT_PROFILES,
           "domains": ["youtube.com", "googlevideo.com", "ytimg.com", "youtu.be", "discord.com", "discord.gg", "discordapp.com", "discordapp.net"],
           "exclude": [], "test_domains": []}


def domain(value):
    if not isinstance(value, str) or len(value) > 253:
        raise ValueError("Invalid domain")
    value = value.strip().rstrip(".").lower().encode("idna").decode("ascii")
    if "." not in value or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", p) for p in value.split(".")):
        raise ValueError("Only DNS names are allowed; no URLs, paths, IPs or wildcards")
    try:
        ipaddress.ip_address(value)
    except ValueError:
        pass
    else:
        raise ValueError("IP literals are not allowed")
    if value.endswith((".local", ".localhost", ".internal", ".home", ".lan", ".onion")):
        raise ValueError("Local names are excluded")
    return value


def domains(text):
    if not isinstance(text, str) or len(text.encode()) > 512_000:
        raise ValueError("Domain list exceeds 512 KB")
    result = sorted({domain(line.split("#", 1)[0].strip()) for line in text.splitlines() if line.split("#", 1)[0].strip()})
    if len(result) > 10000:
        raise ValueError("At most 10000 domains")
    return result


def profile(p):
    if not isinstance(p, dict) or set(p) != {"id", "name", "method", "position", "repeats"}:
        raise ValueError("Profile fields: id, name, method, position, repeats; executable Lua/arguments are forbidden")
    if not isinstance(p["id"], str) or not re.fullmatch(r"[a-z0-9-]{1,40}", p["id"]):
        raise ValueError("Invalid profile id")
    if not isinstance(p["name"], str) or not 1 <= len(p["name"]) <= 64 or any(ord(c) < 32 for c in p["name"]):
        raise ValueError("Invalid profile name")
    if p["method"] not in ("multisplit", "multidisorder"):
        raise ValueError("Only multisplit/multidisorder are allowed")
    for key, low, high in (("position", 1, 32), ("repeats", 1, 3)):
        if type(p[key]) is not int or not low <= p[key] <= high:
            raise ValueError(f"{key} must be {low}..{high}")
    return copy.deepcopy(p)


def validate(c):
    if not isinstance(c, dict) or set(c) != set(DEFAULT) or c["schema"] != 1:
        raise ValueError("Unsupported configuration schema")
    c = copy.deepcopy(c)
    for key in ("enabled", "autostart", "udp"):
        if type(c[key]) is not bool:
            raise ValueError(f"{key} must be boolean")
    if c["language"] not in ("ru", "en"):
        raise ValueError("Unsupported language")
    if not isinstance(c["profiles"], list) or not 1 <= len(c["profiles"]) <= 32:
        raise ValueError("1..32 profiles required")
    c["profiles"] = [profile(p) for p in c["profiles"]]
    ids = [p["id"] for p in c["profiles"]]
    if len(set(ids)) != len(ids) or c["active"] not in ids:
        raise ValueError("Duplicate profiles or missing active profile")
    for key in ("domains", "exclude", "test_domains"):
        if not isinstance(c[key], list) or any(not isinstance(x, str) for x in c[key]):
            raise ValueError("Domain lists must contain strings")
        c[key] = domains("\n".join(c[key]))
    if len(c["test_domains"]) > 3:
        raise ValueError("At most 3 custom test domains")
    return c


def atomic_write(path, content, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    fd, temp = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
        dfd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


class ConfigManager:
    def __init__(self, root):
        self.root = Path(root)
        self.path = self.root / "config.json"
        self.backup = self.root / "last-good.json"
        if not self.path.exists():
            self.save(copy.deepcopy(DEFAULT))

    def load(self):
        if self.path.stat().st_size > 1_000_000:
            raise ValueError("Configuration too large")
        return validate(json.loads(self.path.read_text()))

    def save(self, c):
        c = validate(c)
        atomic_write(self.path, json.dumps(c, ensure_ascii=False, indent=2) + "\n")

    def remember(self, c):
        atomic_write(self.backup, json.dumps(validate(c), ensure_ascii=False, indent=2) + "\n")

    def restore(self):
        return validate(json.loads(self.backup.read_text()))


def process_identity(pid=None):
    pid = os.getpid() if pid is None else pid
    stat = Path(f"/proc/{pid}/stat").read_text()
    return {"pid": pid, "boot": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
            "start": stat.rsplit(")", 1)[1].split()[19]}


def lease_alive(identity):
    try:
        return process_identity(identity["pid"]) == identity
    except (OSError, KeyError, ValueError):
        return False


def recover_test(store):
    journal = store.root / "autotune-recovery.json"
    if journal.exists():
        data = json.loads(journal.read_text())
        if not lease_alive(data["owner"]):
            store.save(data["original"])
            journal.unlink()
            return True
    return False
