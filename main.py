"""Decky API v1, fixed SpoofDPI and Hysteria2 operations."""
import asyncio
import os
from pathlib import Path
import sys

PLUGIN = Path(os.environ.get("DECKY_PLUGIN_DIR", Path(__file__).resolve().parent))
sys.path.insert(0, str(PLUGIN))
from dpi.manager import DpiManager
from vpn.manager import Manager


class Plugin:
    async def _main(self):
        self.manager = Manager(PLUGIN)
        self.dpi = DpiManager(PLUGIN)
        self.lock = asyncio.Lock()
        try:
            await asyncio.to_thread(self.manager.retire_old_service)
        except Exception as e:
            self.manager.error = str(e)

    def status(self):
        return {"vpn": self.manager.status(), "dpi": self.dpi.status(), "version": "0.3.0"}

    def set_mode(self, mode):
        if mode not in ("off", "dpi", "vpn"):
            raise ValueError("Expected off, dpi or vpn")
        old_dpi = self.dpi.load()["enabled"]
        old_vpn = self.manager.store.load()["enabled"]
        try:
            if mode != "dpi" and old_dpi:
                self.dpi.dispatch("set_enabled", {"enabled": False})
            if mode != "vpn" and old_vpn:
                self.manager.dispatch("set_enabled", {"enabled": False})
            if mode == "dpi" and not old_dpi:
                self.dpi.dispatch("set_enabled", {"enabled": True})
            if mode == "vpn" and not old_vpn:
                self.manager.dispatch("set_enabled", {"enabled": True})
        except Exception:
            # Restore the preceding mode if a new service could not start.
            if old_dpi and not self.dpi.load()["enabled"]:
                self.dpi.dispatch("set_enabled", {"enabled": True})
            if old_vpn and not self.manager.store.load()["enabled"]:
                self.manager.dispatch("set_enabled", {"enabled": True})
            raise
        return self.status()

    def dispatch(self, operation, payload):
        if not isinstance(operation, str) or not isinstance(payload, dict):
            raise ValueError("Invalid operation")
        if operation == "status":
            if payload:
                raise ValueError("No parameters expected")
            return self.status()
        if operation == "set_mode":
            if set(payload) != {"mode"}:
                raise ValueError("Expected mode")
            return self.set_mode(payload["mode"])
        if operation == "dpi_set_profile":
            return self.dpi.dispatch("set_profile", payload)
        if operation == "dpi_logs":
            return self.dpi.dispatch("logs", payload)
        if operation in ("save_server", "set_autostart", "logs"):
            result = self.manager.dispatch(operation, payload)
            return result if operation == "logs" else self.status()
        raise ValueError("Unknown operation")

    async def request(self, operation, payload):
        async with self.lock:
            try:
                return {"ok": True, "data": await asyncio.to_thread(self.dispatch, operation, payload)}
            except Exception as e:
                self.dpi.error = str(e)
                return {"ok": False, "error": str(e)}

    async def _uninstall(self):
        async with self.lock:
            await asyncio.to_thread(self.dpi.uninstall)
            await asyncio.to_thread(self.manager.uninstall)
