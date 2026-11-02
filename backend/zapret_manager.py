"""Fixed privileged operations and rollback of desired state + systemd state."""
import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
from .commands import run
from .config_manager import ConfigManager, DEFAULT, atomic_write, domains, profile, validate, process_identity, recover_test
from .diagnostics import network, probe, system
from .nftables_manager import NftablesManager, OWNER
from .strategy_manager import check_engine, copy_runtime, QUEUE

ROOT = Path("/var/lib/zapret2-armada")
LOG = Path("/var/log/zapret2-armada")
UNIT = Path("/etc/systemd/system/zapret2-armada.service")
MODULES = Path("/etc/modules-load.d/zapret2-armada.conf")
NAME = "zapret2-armada.service"


class ZapretManager:
    def __init__(self, plugin, root=ROOT, runner=run):
        self.plugin, self.root, self.run = Path(plugin), Path(root), runner
        self.config = ConfigManager(root)
        self.nft = NftablesManager(runner)
        self.lock = threading.RLock()
        self.tuning = False
        self.cancel = threading.Event()
        self.tune_result = None
        self.progress = ""
        self.error = ""
        self.tune_thread = None

    def recover(self):
        if recover_test(self.config) and self.installed():
            self._sync(self.config.load())

    def ctl(self, *args, check=True):
        return self.run(["/usr/bin/systemctl", *args, NAME], timeout=25, check=check)

    def installed(self):
        return UNIT.exists() and UNIT.read_text().startswith("# " + OWNER)

    def active(self):
        return self.ctl("is-active", check=False).stdout.strip() == "active"

    def status(self):
        c = self.config.load()
        try:
            active = self.active() if self.installed() else False
        except Exception:
            active = False
        engine = False
        q = Path("/proc/net/netfilter/nfnetlink_queue")
        if active and q.exists():
            engine = any(line.split() and int(line.split()[0]) == QUEUE for line in q.read_text().splitlines())
        info = self.plugin / "bin/build-info.json"
        version = json.loads(info.read_text()) if info.exists() else {"version": "not built"}
        return {"config": c, "installed": self.installed(), "service_active": active, "engine_running": engine,
                "plugin_version": "0.1.0", "engine_version": version["version"],
                "os": Path("/etc/os-release").read_text(), "error": self.error,
                "tuning": self.tuning, "progress": self.progress, "tune_result": self.tune_result}

    def install(self):
        if os.geteuid() != 0:
            raise RuntimeError("Decky root flag is required")
        for path in (UNIT, MODULES):
            if path.exists() and not path.read_text().startswith("# " + OWNER):
                raise RuntimeError(f"Refusing to overwrite foreign file: {path}")
        for module in ("nf_conntrack", "nfnetlink_queue", "nft_queue"):
            self.run(["/usr/sbin/modprobe", module])
        self.run(["/usr/sbin/nft", "--version"])
        self.plugin.joinpath("bin/nfqws2").chmod(0o755)
        LOG.mkdir(parents=True, exist_ok=True, mode=0o750)
        stage = self.root / "app.new"
        if stage.exists():
            shutil.rmtree(stage)
        previous = {p: p.read_text() if p.exists() else None for p in (UNIT, MODULES)}
        replaced = False
        try:
            copy_runtime(self.plugin, stage)
            with tempfile.TemporaryDirectory(dir=self.root) as tmp:
                check_engine(stage, tmp, self.config.load(), self.run)
            self.ctl("stop", check=False)
            old = self.root / "app.old"
            if old.exists():
                shutil.rmtree(old)
            app = self.root / "app"
            if app.exists():
                app.rename(old)
            stage.rename(app)
            replaced = True
            atomic_write(UNIT, (self.plugin / "configs/zapret2-armada.service").read_text(), 0o644)
            atomic_write(MODULES, "# " + OWNER + "\nnf_conntrack\nnfnetlink_queue\nnft_queue\n", 0o644)
            self.run(["/usr/bin/systemctl", "daemon-reload"])
            self._sync(self.config.load())
        except Exception:
            # Restore the previous runtime on an interrupted/failed upgrade.
            old = self.root / "app.old"
            if replaced:
                self.ctl("stop", check=False)
                app = self.root / "app"
                if app.exists():
                    shutil.rmtree(app)
                if old.exists():
                    old.rename(app)
                for path, content in previous.items():
                    if content is None:
                        path.unlink(missing_ok=True)
                    else:
                        atomic_write(path, content, 0o644)
                self.run(["/usr/bin/systemctl", "daemon-reload"])
                if self.installed():
                    self._sync(self.config.load())
            raise
        finally:
            if stage.exists():
                shutil.rmtree(stage)

    def _sync(self, c):
        self.ctl("enable" if c["autostart"] else "disable")
        if c["enabled"]:
            self.ctl("reset-failed")
            self.ctl("restart")
            # systemctl start for Type=simple alone is not readiness.
            import time
            for _ in range(100):
                if self.status()["engine_running"] and self.nft.owned():
                    return
                time.sleep(0.1)
            raise RuntimeError("Service started but nfqws2 listener did not become ready; inspect diagnostics/logs")
        self.ctl("stop")
        self.nft.remove()

    def apply(self, desired):
        desired = validate(desired)
        old = self.config.load()
        if desired["enabled"] and not self.installed():
            self.install()
        if desired["enabled"]:
            with tempfile.TemporaryDirectory(dir=self.root) as tmp:
                check_engine(self.root / "app", tmp, desired, self.run)
        self.config.save(desired)
        try:
            if self.installed():
                self._sync(desired)
            self.config.remember(old)
        except Exception as e:
            self.config.save(old)
            try:
                self._sync(old)
            except Exception as rollback:
                raise RuntimeError(f"Apply failed: {e}; rollback service failed: {rollback}; queue bypass keeps traffic open") from e
            raise RuntimeError(f"Apply failed; previous configuration restored: {e}") from e

    def uninstall(self):
        if self.installed():
            self.ctl("disable", "--now")
        self.nft.remove()
        for path in (UNIT, MODULES):
            if path.exists():
                if not path.read_text().startswith("# " + OWNER):
                    raise RuntimeError("Refusing foreign file removal")
                path.unlink()
        self.run(["/usr/bin/systemctl", "daemon-reload"])
        app = self.root / "app"
        if app.exists():
            shutil.rmtree(app)
        # Profiles and logs intentionally retained. Never recursively delete /var.

    def autotune(self):
        with self.lock:
            old = self.config.load()
            journal = self.root / "autotune-recovery.json"
            result = {"baseline": None, "candidates": [], "suggestion": None, "error": ""}
            try:
                atomic_write(journal, json.dumps({"owner": process_identity(), "original": old}))
                if self.cancel.is_set():
                    raise RuntimeError("Testing cancelled")
                def probe_runner(*args, **kwargs):
                    if self.cancel.is_set():
                        raise RuntimeError("Testing cancelled")
                    return self.run(*args, **kwargs)
                self.progress = "Baseline: DNS and HTTPS"
                baseline_cfg = copy.deepcopy(old)
                baseline_cfg["enabled"] = False
                self.apply(baseline_cfg)
                baseline = network(old["test_domains"], probe_runner)
                result["baseline"] = baseline
                if not baseline["control"]["https"]:
                    raise RuntimeError("Control HTTPS failed. Resolve connectivity/DNS before testing strategies")
                base_score = sum(t["https"] for t in baseline["targets"])
                best_score, best_ms = base_score, float("inf")
                for p in old["profiles"]:
                    if self.cancel.is_set():
                        raise RuntimeError("Testing cancelled")
                    self.progress = p["name"]
                    candidate = copy.deepcopy(old)
                    candidate["enabled"] = True
                    candidate["active"] = p["id"]
                    # Ensure custom test hosts are actually included in testing.
                    candidate["domains"] = sorted(set(candidate["domains"] + ["www.youtube.com", "discord.com"] + old["test_domains"]))
                    try:
                        self.apply(candidate)
                        test = network(old["test_domains"], probe_runner)
                        score = sum(t["https"] for t in test["targets"])
                        ms = sum(t["ms"] for t in test["targets"])
                        result["candidates"].append({"profile": p["id"], "score": score, "test": test})
                        if score > base_score and (score > best_score or (score == best_score and ms < best_ms)):
                            best_score, best_ms = score, ms
                            result["suggestion"] = p["id"]
                    except Exception as e:
                        result["candidates"].append({"profile": p["id"], "error": str(e)})
            except Exception as e:
                result["error"] = str(e)
            finally:
                try:
                    self.apply(old)
                    self.config.remember(old)
                    journal.unlink(missing_ok=True)
                except Exception as e:
                    result["error"] += f" Restore failed: {e}"
                self.tune_result = result
                self.progress = ""
                self.tuning = False

    def dispatch(self, operation, payload):
        if not isinstance(operation, str) or not isinstance(payload, dict):
            raise ValueError("Expected operation and object payload")
        if operation == "status":
            return self.status()
        if operation == "cancel_tune":
            self.cancel.set()
            return {"cancel_requested": True}
        if self.tuning:
            raise RuntimeError("Strategy test in progress; wait or cancel")
        with self.lock:
            if self.tuning:
                raise RuntimeError("Strategy test in progress; wait or cancel")
            c = self.config.load()
            if operation == "install":
                self.install()
            elif operation == "configure":
                allowed = {"enabled", "autostart", "udp", "active", "language", "test_domains"}
                if set(payload) - allowed:
                    raise ValueError("Unknown setting")
                c.update(payload)
                self.apply(c)
            elif operation == "save_domains":
                if set(payload) != {"domains", "exclude"}:
                    raise ValueError("Expected domain and exclusion text")
                c["domains"], c["exclude"] = domains(payload["domains"]), domains(payload["exclude"])
                self.apply(c)
            elif operation == "save_profile":
                p = profile(payload)
                c["profiles"] = [v for v in c["profiles"] if v["id"] != p["id"]] + [p]
                self.apply(c)
            elif operation == "restore":
                self.apply(self.config.restore())
            elif operation == "reset":
                self.apply(copy.deepcopy(DEFAULT))
            elif operation == "restart":
                self.apply(c)
            elif operation == "recover_firewall":
                # Stop listener first, then remove only ownership-marked rules.
                c["enabled"] = False
                self.apply(c)
                self.nft.remove()
            elif operation == "diagnose":
                report = {"system": system(self.plugin, self.run), "network": network(c["test_domains"], self.run), "status": self.status(), "logs": self.logs()}
                atomic_write(self.root / "diagnostic-report.json", json.dumps(report, ensure_ascii=False, indent=2))
                return report
            elif operation == "logs":
                return {"text": self.logs()}
            elif operation == "export":
                return {"domains": "\n".join(c["domains"]), "exclude": "\n".join(c["exclude"]), "profiles": c["profiles"]}
            elif operation == "update_domains":
                # Auditable source: bundled list from this signed-off plugin version.
                source = json.loads((self.plugin / "configs/default-domains.json").read_text())
                c["domains"] = sorted(set(c["domains"] + domains("\n".join(source["domains"]))))
                self.apply(c)
            elif operation == "start_tune":
                self.cancel.clear()
                self.tune_result = None
                self.tuning = True
                self.tune_thread = threading.Thread(target=self.autotune, name="zapret2-strategy-test", daemon=True)
                self.tune_thread.start()
            elif operation == "apply_suggestion":
                suggestion = self.tune_result and self.tune_result.get("suggestion")
                if not suggestion or self.tune_result.get("error"):
                    raise ValueError("No successful suggestion")
                c["active"] = suggestion
                # Restore the user's previous enabled/disabled choice.
                self.apply(c)
            else:
                raise ValueError("Unknown operation")
            self.error = ""
            return self.status()

    def logs(self):
        path = LOG / "engine.log"
        if not path.exists():
            return "No engine logs yet"
        with open(path, "rb") as f:
            f.seek(max(0, path.stat().st_size - 16000))
            return f.read().decode("utf-8", errors="replace")
