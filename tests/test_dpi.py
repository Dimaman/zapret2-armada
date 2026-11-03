import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from dpi.manager import DEFAULT, DpiManager, config, validate
from main import Plugin


class DpiTests(unittest.TestCase):
    def test_profiles_and_reject_bad_settings(self):
        self.assertIn('mode = "tun"', config("sni"))
        self.assertIn('auto-configure-network = true', config("sni"))
        self.assertIn('fake-count = 0', config("strong").split("[udp]")[1])
        with self.assertRaises(ValueError):
            validate({**DEFAULT, "profile": "--exec"})

    def test_owned_toggle_and_root_only_config(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "root"
            unit = Path(d) / "unit"
            tun = Path(d) / "tun"
            calls = []
            def runner(argv, **kwargs):
                calls.append(argv)
                if argv[0] == "/usr/sbin/ip":
                    return SimpleNamespace(stdout="0.0.0.0/1 dev tun-spoofdpi\n" if tun.exists() else "", returncode=0)
                return SimpleNamespace(stdout="active" if tun.exists() else "inactive", returncode=0)
            manager = DpiManager(d, root=root, unit=unit, tun=tun, runner=runner)
            def install():
                unit.write_text("# spoofdpi-armada-managed-v1\n")
            manager.install = install
            def ctl(action, check=True):
                calls.append(action)
                if action == "restart": tun.mkdir(exist_ok=True)
                if action == "stop" and tun.exists(): tun.rmdir()
                return SimpleNamespace(stdout="active" if tun.exists() else "inactive", returncode=0)
            manager.ctl = ctl
            manager.dispatch("set_enabled", {"enabled": True})
            self.assertTrue(manager.status()["active"])
            self.assertEqual((root / "spoofdpi.toml").stat().st_mode & 0o777, 0o600)
            manager.dispatch("set_enabled", {"enabled": False})
            self.assertFalse(manager.status()["active"])
            self.assertIn("stop", calls)

    def test_switch_from_vpn_rolls_back_when_dpi_fails(self):
        class FakeVPN:
            def __init__(self):
                self.enabled = True
                self.store = SimpleNamespace(load=lambda: {"enabled": self.enabled})
            def dispatch(self, operation, payload):
                self.enabled = payload["enabled"]
            def status(self): return {"config": {"enabled": self.enabled}}
        class FakeDPI:
            def __init__(self): self.enabled = False
            def load(self): return {"enabled": self.enabled}
            def dispatch(self, operation, payload):
                if payload["enabled"]: raise RuntimeError("TUN unavailable")
                self.enabled = False
            def status(self): return {"enabled": self.enabled}
        plugin = Plugin()
        plugin.manager = FakeVPN()
        plugin.dpi = FakeDPI()
        with self.assertRaisesRegex(RuntimeError, "TUN unavailable"):
            plugin.set_mode("dpi")
        self.assertTrue(plugin.manager.enabled)
        self.assertFalse(plugin.dpi.enabled)


if __name__ == "__main__": unittest.main()
