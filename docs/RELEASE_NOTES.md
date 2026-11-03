# SpoofDPI Armada 0.3.0

Pre-release for ARM64 Armada OS. Local SpoofDPI TUN mode now appears as the
primary compact switch in Decky. It runs DPI bypass on the handheld with a
direct connection, without NFQUEUE or a remote VPN server. The second switch
retains Hysteria2 for the occasions when a full VPN is needed. The two services
cannot run simultaneously from the plugin.

Two TLS strategies are available: SNI split with two fake packets by default,
or a stronger chunk split. UDP fake packets are disabled by default to preserve
game compatibility and direct latency. The upstream SpoofDPI TUN implementation
intercepts IPv4 TCP/UDP; IPv6 traffic is outside this mode.

The package contains pinned upstream SpoofDPI v1.5.5 and Hysteria2 v2.13.0
ARM64 executables with license notices. CI verifies checksums, ARM64 execution,
service syntax and installable ZIP checksums.

## Device test required

No physical Odin 3 / Armada 6.11.0 test is available to the maintainer. The
kernel must provide `/dev/net/tun`; available network routes and permissions
must allow a TUN interface. Check the status, logs, direct public IP, blocked
sites and an actual game after installing. SpoofDPI's upstream TUN mode is
experimental. No single DPI strategy works for every provider or restriction.
