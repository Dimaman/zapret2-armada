# Zapret2 Armada

Experimental Decky Loader plugin for **Armada OS / ARM64**. The native engine
is **nfqws2 from Zapret2 v1.0.6**, with matching Lua. No FEX, Wine or Proton is
used to execute it. Development: `feature/v0.1.0`, target: `main`.

**AYN Odin 3 hardware testing has not been performed.** Kernel NFQUEUE support,
Decky integration, Wi-Fi resume and performance need device verification.
A draft release must not be treated as an installable release.

- React/TypeScript, @decky/api v1, @decky/ui, Russian/English.
- Enable/disable/restart, persistent systemd supervisor, bounded rotating logs.
- Structured profiles, import/edit/save/rollback; no arbitrary Lua/command RPC.
- Included/excluded domain lists, text import/export, bundled seed restoration.
- Optional QUIC UDP 443; all UDP disabled by default.
- Owned atomic nftables table, queue bypass if listener stops; no foreign firewall,
  DNS, routes or VPN configuration changes. Wi-Fi `wl*` only.
- Explicit DNS/TLS diagnostics and comparative testing; applying a suggestion
  requires a separate confirmation. Tests cannot establish DPI causation.
- Source-pinned native engine builds, ARM64/x86_64 CI, isolated real NFQUEUE tests,
  package validation, corresponding source archives and license notices.

Read [installation/removal](docs/INSTALL_RU.md), [device acceptance tests](docs/HARDWARE_TEST_RU.md),
[release limitations](docs/RELEASE_NOTES.md), [architecture](docs/ARCHITECTURE.md),
[research](docs/RESEARCH.md), [licenses](THIRD_PARTY_NOTICES.md) and [roadmap](docs/ROADMAP.md).

## Build

Python 3.12+, Node 22, npm, make, C compiler, pkg-config, libc headers,
sys/capability.h. Native ARM64 builds run on GitHub's ubuntu-24.04-arm runner.

```bash
npm ci --ignore-scripts
npm run typecheck
npm run build
python -m unittest discover -s tests -v
python scripts/build-engine.py
python scripts/verify-engine.py arm64
python scripts/package.py
```

For cross-compilation use scripts/build-arm64.sh with the AArch64 GCC toolchain.
The isolated firewall test must run in a disposable network namespace;
`sudo unshare --net /usr/bin/python3 scripts/test-network.py`. Never run network
integration tests against the host namespace. CI checks both engine/Lua ABI and
real NFQUEUE listener lifecycle, crash bypass and foreign-table preservation.

Persistent paths: `/var/lib/zapret2-armada`, `/var/log/zapret2-armada`,
`/etc/systemd/system/zapret2-armada.service`,
`/etc/modules-load.d/zapret2-armada.conf`. No `/usr` writes or bootc unlock.
Original code GPL-2.0-or-later; independently licensed upstream sources and
notices accompany release packages. See LICENSE and THIRD_PARTY_NOTICES.md.
