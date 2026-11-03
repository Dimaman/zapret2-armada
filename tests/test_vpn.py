import copy
import json
from pathlib import Path
import socket
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from vpn.config import DEFAULT, Store, public, validate
from vpn.manager import Manager, client_config, endpoint


class ConfigurationTests(unittest.TestCase):
    def test_secret_storage_and_public_status(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(d)
            c = {**DEFAULT, "server": "vpn.example.com", "auth": "private-auth",
                 "obfs_password": "private-obfs", "enabled": True}
            store.save(c)
            self.assertEqual(store.path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(store.load()["auth"], "private-auth")
            self.assertNotIn("private-auth", json.dumps(public(store.load())))
            self.assertNotIn("private-obfs", json.dumps(public(store.load())))

    def test_rejects_injection_and_unconfigured_enable(self):
        for bad in (
            {**DEFAULT, "server": "example.com\nmalicious"},
            {**DEFAULT, "port": True},
            {**DEFAULT, "auth": "secret\nother: data"},
            {**DEFAULT, "enabled": True},
            {**DEFAULT, "server": "https://example.com"},
            {**DEFAULT, "sni": "example.com; command"},
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate(bad)

    def test_resolve_before_route_and_exclude_exact_peer(self):
        def resolve(host, port, **kwargs):
            self.assertEqual((host, port), ("vpn.example.com", 8443))
            return [(socket.AF_INET, socket.SOCK_DGRAM, 0, "", ("203.0.113.42", 8443))]
        ip, address = endpoint("vpn.example.com", 8443, resolve)
        c = {**DEFAULT, "server": "vpn.example.com", "auth": "secret", "obfs_password": "obfs"}
        data = json.loads(client_config(c, ip, address))
        self.assertEqual(data["server"], "203.0.113.42:8443")
        self.assertEqual(data["tls"]["sni"], "vpn.example.com")
        self.assertEqual(data["tun"]["route"]["ipv4Exclude"], ["203.0.113.42/32"])
        self.assertEqual(data["tun"]["route"]["ipv6"], ["::/0"])
        self.assertEqual(data["obfs"]["salamander"]["password"], "obfs")

    def test_ipv6_server_exclusion(self):
        ip, address = endpoint("2001:db8::8", 8443)
        c = {**DEFAULT, "server": "2001:db8::8", "auth": "secret", "sni": "vpn.example.com"}
        data = json.loads(client_config(c, ip, address))
        self.assertEqual(data["server"], "[2001:db8::8]:8443")
        self.assertEqual(data["tun"]["route"]["ipv6Exclude"], ["2001:db8::8/128"])


class ManagerTests(unittest.TestCase):
    def test_toggle_starts_and_stops_only_owned_service(self):
        with tempfile.TemporaryDirectory() as d:
            calls = []
            def runner(argv, **kwargs):
                calls.append(argv)
                return SimpleNamespace(stdout="active", returncode=0)
            m = Manager(d, root=Path(d)/"root", unit=Path(d)/"unit", tun=Path(d)/"tun", runner=runner)
            def install():
                m.unit.write_text("# hysteria2-armada-managed-v1\n")
            m.install = install
            with patch("vpn.manager.endpoint", return_value=endpoint("203.0.113.42", 8443)):
                def fake_ctl(*args, **kwargs):
                    if args == ("restart",):
                        m.tun.mkdir(exist_ok=True)
                    if args == ("stop",):
                        m.tun.rmdir()
                    calls.append(args)
                    return SimpleNamespace(stdout="active" if m.tun.exists() else "inactive", returncode=0)
                m.ctl = fake_ctl
                m.dispatch("save_server", {"server":"203.0.113.42", "port":8443, "auth":"secret"})
                self.assertNotIn("secret", json.dumps(m.dispatch("status", {})))
                m.dispatch("set_enabled", {"enabled": True})
                self.assertTrue(m.status()["active"])
                self.assertEqual((m.root/"client.yaml").stat().st_mode & 0o777, 0o600)
                m.dispatch("set_enabled", {"enabled": False})
                self.assertFalse(m.status()["active"])
                self.assertIn(("stop",), calls)

    def test_failed_start_keeps_previous_disabled_state(self):
        with tempfile.TemporaryDirectory() as d:
            m = Manager(d, root=Path(d)/"root", unit=Path(d)/"unit")
            m.start = lambda config: (_ for _ in ()).throw(RuntimeError("connection failed"))
            m.stop = lambda: None
            m.dispatch("save_server", {"server":"example.com", "auth":"secret"})
            with self.assertRaisesRegex(RuntimeError, "connection failed"):
                m.dispatch("set_enabled", {"enabled": True})
            self.assertFalse(m.store.load()["enabled"])


if __name__ == "__main__":
    unittest.main()
