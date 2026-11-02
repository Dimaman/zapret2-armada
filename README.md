# Zapret2 Armada

Native ARM64 **nfqws2** + Lua integration for Armada OS and Decky Loader.

Development branch: `feature/v0.1.0`. Version: 0.1.0 prerelease.

This project is under active implementation. The draft release is not an installable product until its publication gates pass. AYN Odin 3 hardware testing has not yet been performed. No device compatibility is claimed.

Configuration lives under `/var/lib/zapret2-armada`, logs under `/var/log/zapret2-armada` and the service under `/etc/systemd/system`. The immutable image is not modified. Only the owned nftables table `inet zapret2_armada` may be changed. UDP interception is disabled by default.

Original project code is GPL-2.0-or-later; see LICENSE. Independently licensed dependencies retain their upstream licenses. Redistribution notices and exact source/build information are included in release packages.
