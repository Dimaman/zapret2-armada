# Copyright and redistribution

Original Zapret2 Armada code: Copyright (c) 2026 Dimaman and contributors,
GPL-2.0-or-later (LICENSE). No Zapret Deck or Armada implementation code is copied.
Decky Loader itself is not bundled. Its public API is used.

Engine and Lua: bol-van/zapret2 v1.0.6, MIT, Copyright 2016–2026 bol-van.
Included IETF Trust crypto code has its original notice in nfq2/crypto/sha.h.
Both notices are preserved. The source archive is pinned by SHA256.

The engine links libnetfilter_queue 1.0.5 and libnfnetlink 1.0.2 (GPL-2.0-or-later),
libmnl 1.0.5 (LGPL-2.1-or-later), Lua 5.4.8 (MIT), zlib 1.3.1 (zlib license).
The combined engine binary is distributed under GPL-2.0-or-later; upstream
files retain their individual licenses. glibc/libm/libdl remain unbundled system
libraries. Exact source/copyright files take precedence over this summary.

Binary ZIP: corresponding engine/library source archives in sources/; notices
in LICENSES/. Source ZIP: original plugin code, build scripts and full pinned
archives under .cache/sources/. URLs/hashes: configs/sources.lock.json.
Rebuild/relink with Python 3.12+, make, C compiler, pkg-config, libc headers and
sys/capability.h: `python scripts/build-engine.py`. LGPL library replacement
is permitted. No prebuilt engine is trusted.

Bundled frontend dependencies: @decky/api 1.1.3 (BSD-3-Clause), tslib 2.8.1
(0BSD). Their license texts are packaged. React and @decky/ui are supplied
by Decky/Steam. Rollup configuration follows the BSD-3-Clause Decky template
convention, Copyright 2022–2024 Steam Deck Homebrew; complete notice is in
`docs/DECKY_TEMPLATE_LICENSE`. No upstream name implies endorsement.

Optional domain list data: rosakodu/zapret-deck, BSD-3-Clause, Copyright (c)
2026 rosakodu. Its complete notice is in docs/ZAPRET_DECK_LICENSE. Updates
resolve the main branch to an immutable commit before downloading both files;
URL, source SHA256 and commit are recorded in domain-sources.json.
