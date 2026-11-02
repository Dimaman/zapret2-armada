"""Operate only on our ownership-marked table, in atomic nft transactions."""
import json
from .commands import run
from .strategy_manager import QUEUE

TABLE = "zapret2_armada"
OWNER = "zapret2-armada-managed-v1"
NFT = "/usr/sbin/nft"


def rules(udp=False, existing=False):
    # Queue bypass passes traffic when no userspace listener exists.
    # Marked policy-routed traffic and non-WiFi (including VPN tunnel devices)
    # are excluded, as are LAN/link-local/multicast/reserved destinations.
    prefix = f"delete table inet {TABLE}\n" if existing else ""
    udp_rule = f"udp dport 443 ct original packets 1-3 counter queue num {QUEUE} bypass" if udp else ""
    return prefix + f'''add table inet {TABLE} {{
 comment "{OWNER}"
 chain output {{
  type filter hook output priority mangle; policy accept;
  meta mark != 0 return
  oifname != "wl*" return
  ip daddr {{ 0.0.0.0/8, 10.0.0.0/8, 100.64.0.0/10, 127.0.0.0/8, 169.254.0.0/16, 172.16.0.0/12, 192.168.0.0/16, 224.0.0.0/4, 240.0.0.0/4 }} return
  ip6 daddr {{ ::/128, ::1/128, fc00::/7, fe80::/10, ff00::/8 }} return
  tcp dport {{ 80, 443 }} ct original packets 1-12 counter queue num {QUEUE} bypass
  {udp_rule}
 }}
}}
'''


class NftablesManager:
    def __init__(self, runner=run):
        self.run = runner

    def owned(self):
        r = self.run([NFT, "-j", "list", "tables"])
        tables = json.loads(r.stdout)["nftables"]
        exists = any(x.get("table", {}).get("family") == "inet" and x["table"].get("name") == TABLE for x in tables)
        if not exists:
            return False
        r = self.run([NFT, "-j", "list", "table", "inet", TABLE])
        table = next(x["table"] for x in json.loads(r.stdout)["nftables"] if "table" in x)
        if table.get("comment") != OWNER:
            raise RuntimeError("Table name collision: refusing to modify a foreign table")
        return True

    def apply(self, udp=False):
        text = rules(udp, self.owned())
        self.run([NFT, "--check", "--file", "-"], text=text)
        self.run([NFT, "--file", "-"], text=text)

    def remove(self):
        if self.owned():
            self.run([NFT, "--file", "-"], text=f"delete table inet {TABLE}\n")
