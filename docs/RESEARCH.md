# Research log — 2026-11-03

Inspected source snapshots:

| Project | Commit | Findings |
|---|---|---|
| bol-van/zapret2 | f924d796b49da9e455c6bb09268298ef1471cd74 | MIT core/Lua, nfq2/Makefile, --dry-run, --intercept=0, --lua-init and --lua-desync. Stable release currently v1.0.6. |
| rosakodu/zapret-deck | fb01c5d9ebb3c5fd366189efcb4072567fecaf24 | BSD-3-Clause. Existing implementation uses nfqws (Zapret1), not reused. TLS verification bypass and unrestricted command strings must not be carried over. |
| SteamDeckHomebrew/decky-loader | ffd103b9c1a4ce5bf305e7c0998eda6e05457dad | GPL-2.0. Native ARM64 workflow, root flag, API v1, py_modules import, _uninstall hook, local ZIP support in browser.py and developer settings. |
| SteamDeckHomebrew/decky-plugin-template | 90d0780e882a17f5714fc6de044c645f22608290 | BSD-3-Clause, @decky/api callable, @decky/ui, ESM rollup build. |
| armada-os/armada | e039c33448f80b96c4684dc21f2bfb0b7b83d21a | Original code GPL-2.0-or-later. Decky root plugin and /var/home/armada/homebrew; Fedora bootc; investigate NFQUEUE availability. |

References: https://armadaos.dev/ and the five upstream repositories above. These are inspected snapshots, not permanent claims about future versions.
