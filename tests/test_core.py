import asyncio
import copy
import importlib
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from backend.config_manager import ConfigManager, DEFAULT, atomic_write, domain, domains, profile, validate
from backend.diagnostics import probe
from backend.nftables_manager import NftablesManager, OWNER, rules
from backend.strategy_manager import arguments, elf_machine
from backend.zapret_manager import ZapretManager


class ConfigTests(unittest.TestCase):
    def test_interrupted_test_recovered_only_after_owner_dies(self):
        from backend.config_manager import recover_test
        with tempfile.TemporaryDirectory() as d:
            m=ConfigManager(d)
            original=m.load()
            m.save({**original,"active":"split-2"})
            journal=Path(d)/"autotune-recovery.json"
            journal.write_text(json.dumps({"owner":{"pid":1},"original":original}))
            with patch("backend.config_manager.lease_alive",return_value=True):
                self.assertFalse(recover_test(m))
                self.assertEqual(m.load()["active"],"split-2")
            with patch("backend.config_manager.lease_alive",return_value=False):
                self.assertTrue(recover_test(m))
                self.assertEqual(m.load(),original)
                self.assertFalse(journal.exists())

    def test_roundtrip_and_backup(self):
        with tempfile.TemporaryDirectory() as d:
            m = ConfigManager(d)
            original = m.load()
            m.remember(original)
            changed = copy.deepcopy(original)
            changed["active"] = "split-2"
            m.save(changed)
            self.assertEqual(m.load(), changed)
            self.assertEqual(m.restore(), original)
            self.assertEqual(m.path.stat().st_mode & 0o777, 0o600)

    def test_atomic_replace_failure_preserves_old_file(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "config"
            atomic_write(f, "old")
            with patch("backend.config_manager.os.replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    atomic_write(f, "new")
            self.assertEqual(f.read_text(), "old")
            self.assertEqual(len(list(Path(d).iterdir())), 1)

    def test_host_normalization(self):
        self.assertEqual(domain(" EXAMPLE.COM. "), "example.com")
        self.assertEqual(domain("пример.рф"), "xn--e1afmkfd.xn--p1ai")
        self.assertEqual(domains("example.com # note\nExample.COM\nyoutube.com\n"), ["example.com", "youtube.com"])

    def test_unsafe_domains(self):
        for h in ["https://example.com", "127.0.0.1", "10.1.2.3", "foo.local", "foo.lan", "a..com", "a.com;id", "$(id).com", "--a.com", "*.example.com", "foo.com/path", "a\n.com"]:
            with self.subTest(host=h), self.assertRaises(ValueError):
                domain(h)

    def test_unknown_config_and_types(self):
        for key, value in [("enabled", "true"), ("active", "missing"), ("profiles", []), ("test_domains", ["a.com"]*4), ("udp", 1), ("domains", "x.com")]:
            c = copy.deepcopy(DEFAULT)
            c[key] = value
            # Duplicate domain input is normalized; use distinct names for bound.
            if key == "test_domains":
                c[key] = ["a.com", "b.com", "c.com", "d.com"]
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(c)
        with self.assertRaises(ValueError):
            validate({**DEFAULT, "command": "id"})

    def test_profiles_reject_executable_options(self):
        original = DEFAULT["profiles"][0]
        for item in [{**original, "lua": "os.execute('id')"}, {**original, "method": "luaexec"}, {**original, "position": "1;id"}, {**original, "repeats": True}, {**original, "id": "../evil"}]:
            with self.subTest(item=item), self.assertRaises(ValueError):
                profile(item)

    def test_oversize_import(self):
        with self.assertRaises(ValueError):
            domains("x" * 512001)


class StrategyTests(unittest.TestCase):
    def test_arguments_are_nfqws2_and_lua(self):
        with tempfile.TemporaryDirectory() as d:
            args = arguments("/app", d, copy.deepcopy(DEFAULT))
            self.assertEqual(args[0], "/app/bin/nfqws2")
            self.assertIn("--lua-desync=multisplit:pos=1:repeats=1", args)
            self.assertEqual(sum(a.startswith("--lua-init=@") for a in args), 2)
            self.assertNotIn("--filter-udp=443", args)
            self.assertTrue(all("--dpi-desync=" not in a for a in args))

    def test_udp_is_explicit_and_limited(self):
        c = copy.deepcopy(DEFAULT)
        c["udp"] = True
        with tempfile.TemporaryDirectory() as d:
            args = arguments("/app", d, c)
            self.assertIn("--filter-udp=443", args)
            self.assertIn("--filter-l7=quic", args)
            self.assertIn("--out-range=-d3", args)
            self.assertIn("--new", args)

    def test_no_empty_hostlist_global_mode(self):
        c = copy.deepcopy(DEFAULT)
        c["domains"] = []
        with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError):
            arguments("/app", d, c)

    def test_elf_rejects_wrong_format(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d)/"elf"
            f.write_bytes(b"not ELF")
            with self.assertRaises(ValueError): elf_machine(f)
            header = bytearray(64)
            header[:6] = b"\x7fELF\x02\x01"
            struct.pack_into("<H", header, 18, 183)
            f.write_bytes(header)
            self.assertEqual(elf_machine(f), 183)


class FakeNft:
    def __init__(self, exists=False, owner=OWNER):
        self.exists, self.owner, self.calls = exists, owner, []
    def __call__(self, args, **kw):
        self.calls.append((args, kw))
        if args[-2:] == ["list", "tables"]:
            data = {"nftables": [{"table": {"family": "inet", "name": "zapret2_armada"}}] if self.exists else []}
        else:
            data = {"nftables": [{"table": {"family": "inet", "name": "zapret2_armada", "comment": self.owner}}]}
        return SimpleNamespace(returncode=0, stdout=json.dumps(data), stderr="")


class NftTests(unittest.TestCase):
    def test_foreign_table_never_changed(self):
        for op in ("apply", "remove"):
            fake = FakeNft(True, "other-owner")
            with self.assertRaises(RuntimeError): getattr(NftablesManager(fake), op)()
            self.assertFalse(any("--file" in args for args, _ in fake.calls))

    def test_atomic_replacement_and_check_first(self):
        fake = FakeNft(True)
        NftablesManager(fake).apply()
        writes = [(a,k["text"]) for a,k in fake.calls if "text" in k]
        self.assertEqual(len(writes),2)
        self.assertIn("--check",writes[0][0])
        self.assertEqual(writes[0][1],writes[1][1])
        self.assertTrue(writes[1][1].startswith("delete table inet zapret2_armada\nadd table"))
        self.assertNotIn("flush ruleset",writes[1][1])

    def test_missing_table_remove_is_noop(self):
        fake = FakeNft()
        NftablesManager(fake).remove()
        self.assertEqual(len(fake.calls),1)

    def test_check_failure_never_commits(self):
        fake = FakeNft()
        def runner(a,**k):
            if "--check" in a: raise RuntimeError("bad syntax")
            return fake(a,**k)
        with self.assertRaises(RuntimeError): NftablesManager(runner).apply()
        self.assertFalse(any("--file" in a for a,_ in fake.calls))

    def test_scope_and_bypass(self):
        r = rules()
        self.assertIn('oifname != "wl*" return',r)
        self.assertIn("meta mark != 0 return",r)
        self.assertIn("192.168.0.0/16",r)
        self.assertIn("fc00::/7",r)
        self.assertIn("queue num 20073 bypass",r)
        self.assertNotIn("udp dport",r)
        self.assertIn("udp dport 443 ct original packets 1-3",rules(True))


class ProbeTests(unittest.TestCase):
    def test_domain_updates_pin_snapshot_and_reject_commands(self):
        from backend.domain_sources import update
        calls=[]
        def fetch(url,limit):
            calls.append((url,limit))
            if len(calls)==1:return json.dumps({'object':{'sha':'a'*40,'type':'commit'}}).encode()
            return b'Example.COM\nyoutube.com\n'
        names,source=update(fetch)
        self.assertEqual(names,['example.com','youtube.com'])
        self.assertEqual(len(source),2)
        self.assertTrue(all('/'+'a'*40+'/lists/' in u for u,_ in calls[1:]))
        def bad(url,limit):
            if 'api.github.com' in url:return json.dumps({'object':{'sha':'a'*40,'type':'commit'}}).encode()
            return b'example.com\n$(touch /root/evil)\n'
        with self.assertRaises(ValueError):update(bad)

    def test_private_dns_is_rejected_before_connect(self):
        calls = []
        def runner(args,**kw):
            calls.append(args)
            return SimpleNamespace(stdout="127.0.0.1 STREAM example.com\n")
        r = probe("example.com",runner)
        self.assertFalse(r["https"])
        self.assertEqual(len(calls),1)

    def test_tls_dns_pin_no_redirect_and_no_proxy(self):
        calls=[]
        def runner(args,**kw):
            calls.append(args)
            return SimpleNamespace(stdout="1.1.1.1 STREAM example.com\n" if len(calls)==1 else "200")
        self.assertTrue(probe("example.com",runner)["https"])
        curl=calls[-1]
        self.assertIn("example.com:443:1.1.1.1",curl)
        self.assertIn("--noproxy",curl)
        for forbidden in ("-k","--insecure","-L","--location"):
            self.assertNotIn(forbidden,curl)

    def test_probe_failure_not_definite_dpi(self):
        with patch("backend.diagnostics.probe",return_value={"https":False,"dns":True}):
            from backend.diagnostics import network
            self.assertFalse(network()["possible_dpi"])


class ManagerTests(unittest.TestCase):
    def test_reset_recovers_corrupt_configuration(self):
        with tempfile.TemporaryDirectory() as d:
            m=ZapretManager(d,d)
            m.config.path.write_text('{broken JSON')
            self.assertIn('Invalid configuration',m.status()['error'])
            m.dispatch('reset',{})
            self.assertEqual(m.config.load(),validate(DEFAULT))
            self.assertEqual((Path(d)/'config.invalid.json').read_text(),'{broken JSON')

    def test_failed_apply_rolls_back_persistent_and_service_state(self):
        with tempfile.TemporaryDirectory() as d:
            m=ZapretManager(d,d)
            original=m.config.load()
            m.installed=lambda: True
            calls=[]
            def sync(c):
                calls.append(c["active"])
                if len(calls)==1: raise RuntimeError("service failure")
            m._sync=sync
            changed={**original,"active":"split-2"}
            with self.assertRaisesRegex(RuntimeError,"previous configuration restored"):
                m.apply(changed)
            self.assertEqual(m.config.load(),original)
            self.assertEqual(calls,["split-2","split-1"])

    def test_unknown_rpc_and_setting_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            m=ZapretManager(d,d)
            for op,data in [("shell",{"cmd":"id"}),("configure",{"qnum":0}),("configure",{"command":"id"})]:
                with self.subTest(op=op),self.assertRaises(ValueError):m.dispatch(op,data)

    def test_autotune_restores_and_does_not_apply_suggestion(self):
        with tempfile.TemporaryDirectory() as d:
            m=ZapretManager(d,d)
            original=m.config.load()
            m.apply=lambda c:m.config.save(c)
            baseline={"control":{"https":True},"targets":[{"https":False,"ms":10}]}
            success={"control":{"https":True},"targets":[{"https":True,"ms":20}]}
            m.tuning=True
            with patch("backend.zapret_manager.process_identity",return_value={"pid":1,"boot":"test","start":"0"}), patch("backend.zapret_manager.network",side_effect=[baseline,success,success,success]):m.autotune()
            self.assertEqual(m.config.load(),original)
            self.assertEqual(m.tune_result["suggestion"],"split-1")
            self.assertFalse(m.tuning)

    def test_failed_control_does_not_try_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            m=ZapretManager(d,d)
            original=m.config.load()
            states=[]
            m.apply=lambda c:states.append(c)
            with patch("backend.zapret_manager.process_identity",return_value={"pid":1,"boot":"test","start":"0"}), patch("backend.zapret_manager.network",return_value={"control":{"https":False}}):m.autotune()
            self.assertEqual(len(states),2)
            self.assertEqual(states[-1],original)
            self.assertIsNone(m.tune_result["suggestion"])

    def test_mutations_blocked_during_tune(self):
        with tempfile.TemporaryDirectory() as d:
            m=ZapretManager(d,d)
            m.tuning=True
            with self.assertRaises(RuntimeError):m.dispatch("reset",{})
            self.assertTrue(m.dispatch("cancel_tune",{})["cancel_requested"])

    def test_backend_entrypoint_error_envelope(self):
        main=importlib.import_module("main")
        fake=SimpleNamespace(dispatch=lambda *a: (_ for _ in ()).throw(ValueError("bad input")),error="",recover=lambda:None)
        async def smoke():
            p=main.Plugin()
            with patch.object(main,"ZapretManager",return_value=fake):await p._main()
            result=await p.request("unknown",{})
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"],"bad input")
        asyncio.run(smoke())


if __name__ == "__main__":
    unittest.main()
