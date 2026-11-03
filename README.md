# Hysteria2 Armada

Decky Loader plugin for Armada OS handhelds. One compact switch in Steam Game
Mode starts or stops an official ARM64 Hysteria2 client in TUN mode. TCP and UDP
from local applications are routed through the configured Hysteria2 server.
No NFQUEUE, nf_conntrack, Zapret2 engine, or remote control port is needed.
The Hysteria2 project notes that its TUN mode does not tunnel ICMP.

The plugin is an experimental update of Zapret2 Armada. It uses the same
Decky ZIP root directory, so Decky replaces the old entry. On first activation
it disables only the old owned service and removes its owned nftables table.
The previous domain settings remain on disk but are not used by this VPN.

Configure the server address, UDP port, authentication password, optional
Salamander obfuscation password, and TLS SNI through the plugin settings.
Credentials are stored as root-only files under /var/lib/hysteria2-armada,
never included in status RPC. TLS verification is on by default.
The server IP is resolved before installing the TUN default routes and is
excluded from those routes to avoid a connection loop. IPv4 and IPv6 default
routes are installed by the official Hysteria2 client while connected.

The official Hysteria2 v2.13.0 ARM64 release is pinned by SHA256 at build time.
Sources and complete release checksums accompany the installable ZIP.
See [installation](docs/INSTALL_RU.md) and [release notes](docs/RELEASE_NOTES.md).

Device-specific operation on an Odin 3 kernel 6.11.0 remains unverified.
GitHub CI checks syntax, schema, release digest, ELF architecture, and the
packaged ZIP; it does not stand in for a real device connection.
