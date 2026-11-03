# Changelog

## 0.1.1 — experimental prerelease

- Accept `nf_conntrack`, `nfnetlink_queue` and `nft_queue` already present in the
  running kernel even if `modprobe` cannot find a loadable module for the release.
- Show an actionable kernel-dependency error if a required component is absent.
- Show when starting was requested but nfqws2 remains stopped in the Decky panel.
- First Odin 3 startup attempt failed at `modprobe nf_conntrack` for
  `/lib/modules/6.11.0`; actual kernel support and this fix still need device testing.

## 0.1.0 — experimental prerelease

- Native nfqws2 1.0.6 with matching Lua, pinned-source ARM64 build.
- Decky API v1 React/TypeScript interface, Russian/English.
- Safe TCP split/disorder profiles; QUIC UDP 443 disabled by default.
- Profile edit/import/save, domain/exclusion text import/export and snapshot-pinned
  updates from the allowlisted zapret-deck domain sources.
- Atomic configuration, rollback and last-configuration restore.
- systemd persistence and restart-on-failure outside the bootc image.
- Owned nftables table, absent-listener bypass, VPN/marked/LAN exclusions.
- On-demand TLS/DNS diagnostics, rotating logs and JSON report.
- Comparative tests, with separate confirmation to apply suggestions.
- ARM64/x86_64 engine checks, isolated network tests, package validation.

Actual Odin 3 hardware and ISP strategy effectiveness remain unverified.
