# Architecture and failure model

Decky API v1 root plugin exposes a single bounded operation dispatcher. It has
no shell, URL fetch, command string or arbitrary file-path RPC. Configuration
uses explicit schemas and numeric/method allowlists. User Lua is not executed.

The systemd service runs a small Python supervisor and nfqws2. The engine drops
to nobody using its native privilege mechanism. CapabilityBoundingSet restricts
the service to net-admin/net-raw/setuid/setgid; systemd restricts filesystem
writes to its own persistent state/logs. Python runs in isolated interpreter mode.
No TCP/HTTP control server is exposed.

Start: validate ELF, native execution, --dry-run and --intercept=0 Lua ABI;
start listener; check kernel NFQUEUE peer readiness; atomically check/apply
owned nft table. Readiness requires both listener and owned rules. Stop: remove
owned rules before terminating the listener. Queue bypass protects traffic if
userspace exits. ExecStopPost also removes stale owned rules. systemd owns
crash restart and cgroup cleanup. A fixed queue number collision fails startup.

Only inet zapret2_armada with matching ownership comment can be replaced or
removed. Foreign tables with that name are refused. nft --check precedes one
atomic transaction. No flush ruleset, route manipulation or VPN service calls.
Early outgoing conntrack packet counts limit queue overhead; Linux nft_ct
packet-count expressions enable conntrack accounting for new connections.
Already existing connections may need reopening for a meaningful test.

Configuration writes use fsync + atomic replace. Failed service application
restores the previous config and service state. Autotune retains the original
configuration in an owner/boot/process-start-identified recovery journal,
restores on normal completion/cancellation and recovers an interrupted test on
backend reload or service startup. A hard backend termination during the
baseline (when the engine is stopped) can delay restoring the service until
Decky reload or reboot; traffic remains fail-open. This limitation is explicit.

No continuous connectivity polling occurs. UI refreshes local status while
mounted, every 10 seconds. Network probes run only on explicit diagnosis/test.
DNS resolution is bounded; probes reject non-public resolved IPs, pin the selected
IP for TLS, verify certificates and avoid redirects/proxies. HTTP reachability
is not evidence of video/voice success or a definitive DPI diagnosis.

Wi-Fi device names wl* are matched dynamically, so changing Wi-Fi networks does
not require inserting duplicate rules. No suspend inhibitor is used. Resume
behavior and actual kernel module availability need hardware acceptance tests.
