# Zapret2 Armada 0.1.0

Experimental Pre-release. Native ARM64 nfqws2 (Zapret2 v1.0.6), Lua 5.4.8.
No FEX/Wine/Proton is used by the engine. Host filtering also covers translated games.

Russian/English Decky interface, enable/disable/restart, bounded profile editing
and import, domain/exclusion editing/export, systemd persistence, rotating logs,
TLS/DNS diagnostics and comparative strategy tests. Recommendations require a
separate action. QUIC UDP 443 is opt-in.

Install the ARM64 ZIP through Decky Settings → Developer → local ZIP; prepare
the service from the plugin's Diagnostics page. See docs/INSTALL_RU.md and
docs/HARDWARE_TEST_RU.md. Uninstall through Decky; only this plugin's service
and owned firewall table are removed. Settings and logs are retained.

Requirements: ARM64 Linux, glibc >=2.39, Python >=3.12, systemd, nftables,
NFQUEUE/nft_queue kernel support, curl/getent/modprobe and Decky API v1 root
plugin support. The immutable Fedora bootc image is not modified.

## Known limitations

- Not tested on real AYN Odin 3 or the user's Armada/Decky version. Sleep/resume,
  Wi-Fi, FPS, battery and ISP effectiveness need device verification.
- Some Armada kernels may omit NFQUEUE/nft_queue. Missing support prevents startup;
  the plugin does not install or replace a kernel.
- Templates are syntax/Lua tested, not ISP-certified. HTTPS probes cannot prove
  DPI causation, video playback, WebSockets or Discord voice availability.
- Wi-Fi interfaces wl* only; TCP 80/443 and optional QUIC UDP 443. Marked traffic,
  common LAN/reserved addresses and tunnel devices are bypassed. No route/DNS/VPN
  configuration or foreign firewall tables are changed.
- No remote domain-list downloads, unrestricted Lua import or desktop tray.
  A maintained seed domain list is included in this version.
- Testing temporarily restarts the engine. Use fresh connections. Diagnostic
  exports contain your domain configuration and system information.
- x86_64 engine is tested as preparation for Steam Deck; this release packages ARM64 only.

Assets: zapret2-armada-v0.1.0-arm64.zip, zapret2-armada-v0.1.0-source.zip,
SHA256SUMS. Complete engine/library sources and license notices are included.
Incomplete or failed builds must remain a draft, not an installable release.
