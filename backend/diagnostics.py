"""On-demand probes with verified TLS, no redirects/proxies, public IPs only."""
import ipaddress
import json
import platform
from pathlib import Path
import time
from .commands import run
from .config_manager import domain
from .kernel_modules import REQUIRED, inspect_module
from .strategy_manager import elf_machine


def probe(host, runner=run):
    host = domain(host)
    start = time.monotonic()
    result = {"domain": host, "dns": False, "https": False, "http": "", "error": ""}
    try:
        r = runner(["/usr/bin/getent", "ahosts", host], timeout=6)
        ips = sorted({line.split()[0] for line in r.stdout.splitlines() if line.split()})
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
            raise ValueError("DNS returned no addresses or a non-public address")
        result["dns"] = True
        address = next((ip for ip in ips if ":" not in ip), ips[0])
        address = f"[{address}]" if ":" in address else address
        r = runner(["/usr/bin/curl", "-q", "--noproxy", "*", "--silent", "--show-error",
                    "--head", "--output", "/dev/null", "--write-out", "%{http_code}",
                    "--connect-timeout", "4", "--max-time", "8", "--resolve", f"{host}:443:{address}",
                    f"https://{host}/"], timeout=10)
        result["http"] = r.stdout.strip()
        result["https"] = result["http"].isdigit() and 200 <= int(result["http"]) < 400
        if not result["https"]:
            result["error"] = "HTTPS reached but HTTP status did not indicate availability"
    except Exception as e:
        result["error"] = str(e)[-600:]
    result["ms"] = round((time.monotonic() - start) * 1000)
    return result


def network(hosts=(), runner=run):
    control = probe("example.com", runner)
    targets = [probe(h, runner) for h in dict.fromkeys(["www.youtube.com", "discord.com", *hosts])]
    return {"control": control, "targets": targets,
            "possible_dpi": control["https"] and any(t["dns"] and not t["https"] for t in targets),
            "note": "HTTPS probes cannot establish DPI causation, video playback, WebSocket or voice availability."}


def system(app, runner=run):
    checks = []
    def check(name, fn):
        try:
            value = fn()
            checks.append({"name": name, "ok": True, "detail": str(value)[:3000]})
        except Exception as e:
            checks.append({"name": name, "ok": False, "detail": str(e)[:3000]})
    check("architecture", lambda: f"{platform.machine()}; ELF machine={elf_machine(Path(app) / 'bin/nfqws2')}")
    check("engine and shared libraries", lambda: runner([str(Path(app) / "bin/nfqws2"), "--version"]).stdout)
    check("nftables", lambda: runner(["/usr/sbin/nft", "--version"]).stdout)
    check("systemd", lambda: runner(["/usr/bin/systemctl", "--version"]).stdout.splitlines()[0])
    check("NFQUEUE kernel interface", lambda: Path("/proc/net/netfilter/nfnetlink_queue").read_text())
    for module in REQUIRED:
        check(f"{module} module or built-in", lambda name=module: inspect_module(name, runner))
    os_release = Path("/etc/os-release").read_text()
    return {"checks": checks, "os_release": os_release, "kernel": platform.release(), "hardware_tested": False}
