"""Decky API v1: fixed Hysteria2 VPN operations only."""
import asyncio
import os
from pathlib import Path
import sys

PLUGIN = Path(os.environ.get("DECKY_PLUGIN_DIR", Path(__file__).resolve().parent))
sys.path.insert(0, str(PLUGIN))
from vpn.manager import Manager


class Plugin:
    async def _main(self):
        self.manager = Manager(PLUGIN)

    async def request(self, operation, payload):
        try:
            return {"ok": True, "data": await asyncio.to_thread(self.manager.dispatch, operation, payload)}
        except Exception as e:
            self.manager.error = str(e)
            return {"ok": False, "error": str(e)}

    async def _uninstall(self):
        await asyncio.to_thread(self.manager.uninstall)
