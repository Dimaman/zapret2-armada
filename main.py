"""Decky API v1 entry point. No shell or arbitrary command RPC exists."""
import asyncio
import os
from pathlib import Path
import sys

PLUGIN = Path(os.environ.get("DECKY_PLUGIN_DIR", Path(__file__).resolve().parent))
sys.path.insert(0, str(PLUGIN))
from backend.zapret_manager import ZapretManager


class Plugin:
    async def _main(self):
        self.manager = ZapretManager(PLUGIN)

    async def request(self, operation, payload):
        try:
            data = await asyncio.to_thread(self.manager.dispatch, operation, payload)
            return {"ok": True, "data": data}
        except Exception as e:
            self.manager.error = str(e)
            return {"ok": False, "error": str(e)}

    async def _unload(self):
        # The system service remains under the user's explicit enabled choice.
        self.manager.cancel.set()

    async def _uninstall(self):
        self.manager.cancel.set()
        # Wait until test worker has restored the saved state before uninstall.
        await asyncio.to_thread(self._remove)

    def _remove(self):
        with self.manager.lock:
            self.manager.uninstall()
