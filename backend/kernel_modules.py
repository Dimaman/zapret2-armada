"""Check fixed kernel dependencies without treating built-ins as missing modules."""
import platform
from pathlib import Path

from .commands import run

MODULE_ROOT = Path("/sys/module")
REQUIRED = ("nf_conntrack", "nfnetlink_queue", "nft_queue")


def ensure_module(name, runner=run, module_root=MODULE_ROOT):
    if name not in REQUIRED:
        raise ValueError("Unexpected kernel module")
    if (module_root / name).is_dir():
        return "present in running kernel"
    result = runner(["/usr/sbin/modprobe", name], check=False)
    if result.returncode and not (module_root / name).is_dir():
        detail = (result.stderr or result.stdout).strip()[-500:]
        raise RuntimeError(
            f"Kernel {platform.release()}: {name} is unavailable. "
            f"Check the installed kernel modules and Armada NFQUEUE support. {detail}"
        )
    return "loaded"


def inspect_module(name, runner=run, module_root=MODULE_ROOT):
    if name not in REQUIRED:
        raise ValueError("Unexpected kernel module")
    if (module_root / name).is_dir():
        return "present in running kernel"
    result = runner(["/usr/sbin/modprobe", "-n", name], check=False)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip()[-500:])
    return "loadable"
