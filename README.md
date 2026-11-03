# SpoofDPI Armada

Decky Loader plugin for ARM64 Armada OS handhelds. The compact Game Mode panel
has two mutually exclusive switches:

- Local DPI bypass: SpoofDPI v1.5.5 in system-wide IPv4 TUN mode. Connections
  leave the handheld directly, with no VPS. TCP TLS ClientHello is split and
  optional fake packets are sent. UDP is forwarded without fake packets by
  default to avoid interfering with games.
- Hysteria2 VPN: the existing full TCP/UDP tunnel through your server.

Both modes need `/dev/net/tun` and Decky root access. SpoofDPI does not use
NFQUEUE or `nf_conntrack`. The upstream TUN implementation is experimental,
currently handles IPv4 packets, and depends on Linux routing and permissions.
IPv6 is not intercepted by its TUN implementation. No DPI method can guarantee
unblocking every site or game: effectiveness depends on the network and server.

On/off operations manage only this plugin's owned systemd services. Switching
modes stops the old service before starting the other and rolls back on failure.
Autostart is disabled for local DPI; optional VPN autostart remains as configured.
Secrets for Hysteria2 remain in root-only files. The ZIP root remains
`zapret2-armada/` so Decky replaces the previous plugin entry, while its
visible name and the release artifacts are SpoofDPI Armada.

See [installation](docs/INSTALL_RU.md) and [release notes](docs/RELEASE_NOTES.md).
GitHub CI checks frontend, lifecycle, upstream ARM64 binary execution, systemd
units and installable ZIP. The Odin 3 hardware network path must still be tested
on the device.
