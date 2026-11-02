"""systemd supervisor; no network polling; listener readiness before firewall."""
import fcntl
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.commands import ENV, run
from backend.config_manager import ConfigManager, recover_test
from backend.nftables_manager import NftablesManager
from backend.strategy_manager import QUEUE, check_engine

ROOT = Path("/var/lib/zapret2-armada")


def queue_ready(pid, path=Path("/proc/net/netfilter/nfnetlink_queue")):
    if not path.exists():
        return False
    # Columns: queue, netlink peer port-id, queued packets, copy mode/range,
    # kernel/user drops, id sequence, refcount. Peer id normally equals PID.
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) >= 2 and int(fields[0]) == QUEUE and int(fields[1]) == pid:
            return True
    return False


def supervise():
    ROOT.mkdir(parents=True, exist_ok=True)
    lock = open(ROOT / "supervisor.lock", "w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    logdir = Path("/var/log/zapret2-armada")
    logdir.mkdir(mode=0o750, parents=True, exist_ok=True)
    handler = RotatingFileHandler(logdir / "engine.log", maxBytes=512000, backupCount=3)
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    log = logging.getLogger("engine")
    log.setLevel(logging.INFO)
    log.addHandler(handler)
    store = ConfigManager(ROOT)
    recover_test(store)
    config = store.load()
    nft = NftablesManager()
    child = None

    def stop(_sig, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        nft.remove()  # own stale rules only
        if not config["enabled"]:
            return
        # Load only necessary kernel modules, using fixed names.
        for module in ("nf_conntrack", "nfnetlink_queue", "nft_queue"):
            run(["/usr/sbin/modprobe", module], check=False)
        args = check_engine(ROOT / "app", ROOT, config)
        with open("/proc/net/netfilter/nfnetlink_queue") as queues:
            if any(line.split() and int(line.split()[0]) == QUEUE for line in queues):
                raise RuntimeError("NFQUEUE number is already occupied")
        child = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=ENV)
        # Bounded startup readiness polling, never continuous network checks.
        for _ in range(100):
            if child.poll() is not None:
                raise RuntimeError("nfqws2 exited before listener readiness: " + child.stdout.read(4096))
            if queue_ready(child.pid):
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("NFQUEUE listener did not become ready")
        nft.apply(config["udp"])
        log.info("nfqws2 started, pid=%s, profile=%s", child.pid, config["active"])
        for line in child.stdout:
            log.info(line.rstrip()[:4096])
        raise RuntimeError(f"nfqws2 exited: {child.wait()}")
    except KeyboardInterrupt:
        log.info("Service stopped")
    except Exception:
        log.exception("Supervisor failed")
        raise
    finally:
        try:
            nft.remove()
        finally:
            if child is not None and child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()


if __name__ == "__main__":
    supervise()
