# Hysteria2 Armada 0.2.0

Experimental ARM64 pre-release. The Decky Game Mode panel now presents one
compact Hysteria2 VPN switch. Turning it on starts the official Hysteria2
v2.13.0 client in system-wide TUN mode; turning it off stops the service.
It routes TCP and UDP over the user's own Hysteria2 server without NFQUEUE.
ICMP is not tunneled by Hysteria2 TUN mode.

Server, UDP port, authentication, optional Salamander obfuscation and TLS SNI
are set in a separate Decky settings dialog. Secrets are stored in root-only
files and omitted from status results. TLS validation defaults to enabled.
Autostart is opt-in. Upgrade retires only the previous plugin's owned service
and nftables table; its old domain configuration is retained.

The binary is pinned to the upstream release SHA256 and verified by CI.
The ARM64 ZIP and source ZIP include license notices and SHA256SUMS.

## Known limitations

- No real AYN Odin 3 / Armada 6.11.0 hardware connection test yet. The
  kernel must expose /dev/net/tun and Decky must allow the root service.
- TUN routing is managed by Hysteria2. VPN mode is not a replacement for the
  old Zapret2 strategy editor or its domain list.
- Server must be reachable over UDP; authentication, Salamander password and
  TLS SNI must match the user's server. An unreachable server cannot be fixed
  by a plugin switch.
- A VPN routes traffic via the server and may increase game latency.
