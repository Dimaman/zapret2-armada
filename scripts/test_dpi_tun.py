#!/usr/bin/env python3
"""ARM64 smoke test of real TUN creation and route cleanup in an isolated netns."""
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def ip(*args):
    return subprocess.run(["/usr/sbin/ip", *args], check=True, capture_output=True, text=True).stdout


def main():
    ip("link", "set", "lo", "up")
    ip("link", "add", "di-v0", "type", "veth", "peer", "name", "di-v1")
    ip("addr", "add", "10.237.11.2/24", "dev", "di-v0")
    ip("addr", "add", "10.237.11.1/24", "dev", "di-v1")
    ip("link", "set", "di-v0", "up")
    ip("link", "set", "di-v1", "up")
    ip("route", "add", "default", "via", "10.237.11.1", "dev", "di-v0")
    with tempfile.TemporaryDirectory() as tmp:
        conf = Path(tmp) / "config.toml"
        conf.write_text('[app]\nmode = "tun"\nauto-configure-network = true\nno-tui = true\n[https]\nsplit-mode = "sni"\n')
        proc = subprocess.Popen([str(ROOT / "bin/spoofdpi"), "--config", str(conf)],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        output = ""
        try:
            for _ in range(100):
                if proc.poll() is not None:
                    raise RuntimeError(f"SpoofDPI exited early: {proc.stdout.read()[-3000:]}")
                if "tun-spoofdpi" in ip("link", "show") and "tun-spoofdpi" in ip("route", "show", "0.0.0.0/1"):
                    break
                time.sleep(.1)
            else:
                raise RuntimeError("SpoofDPI did not create TUN and route")
        finally:
            proc.terminate()
            try:
                output, _ = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                output, _ = proc.communicate(timeout=5)
            print(output[-3000:])
        if "tun-spoofdpi" in ip("route", "show") or "tun-spoofdpi" in ip("link", "show"):
            raise RuntimeError("SpoofDPI routes or interface remain after stop")
        if "lookup 200" in ip("rule", "show"):
            raise RuntimeError("SpoofDPI policy rule remains after stop")
        print("SpoofDPI ARM64 TUN lifecycle and route cleanup passed in netns")


if __name__ == "__main__":
    main()
