"""Construct nfqws2 arguments exclusively from validated structured profiles."""
import struct
import os
import shutil
from pathlib import Path
from .config_manager import atomic_write, validate
from .commands import run

QUEUE = 20073
MARK = "0x40000000"


def copy_runtime(source, target):
    source, target = Path(source), Path(target)
    target.mkdir(mode=0o755)
    target.chmod(0o755)
    for name in ("backend", "bin", "lua", "files"):
        src = source / name
        if src.is_symlink() or any(p.is_symlink() for p in src.rglob("*")):
            raise RuntimeError("Symlinks in runtime payload are forbidden")
        shutil.copytree(src, target / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for path in target.rglob("*"):
        path.chmod(0o755 if path.is_dir() or path.name == "nfqws2" else 0o644)


def elf_machine(path):
    with open(path, "rb") as f:
        h = f.read(64)
    if len(h) < 64 or h[:4] != b"\x7fELF" or h[4] != 2 or h[5] != 1:
        raise ValueError("Expected ELF64 little endian")
    return struct.unpack_from("<H", h, 18)[0]


def arguments(app, state, c):
    c = validate(c)
    app, state = Path(app), Path(state)
    # nfqws2 validates hostlists after dropping to nobody, including --dry-run.
    # Only generated public hostlists live here; JSON configuration is 0600.
    state.mkdir(parents=True, exist_ok=True)
    os.chmod(state, 0o755)
    p = next(p for p in c["profiles"] if p["id"] == c["active"])
    if not c["domains"]:
        raise ValueError("At least one included domain required; refusing global interception")
    atomic_write(state / "hosts.txt", "\n".join(c["domains"]) + "\n", 0o644)
    atomic_write(state / "exclude.txt", "\n".join(c["exclude"]) + "\n", 0o644)
    lists = [f"--hostlist={state / 'hosts.txt'}", f"--hostlist-exclude={state / 'exclude.txt'}"]
    args = [str(app / "bin/nfqws2"), f"--qnum={QUEUE}", f"--fwmark={MARK}", "--user=nobody",
            f"--lua-init=@{app / 'lua/zapret-lib.lua'}", f"--lua-init=@{app / 'lua/zapret-antidpi.lua'}",
            "--filter-tcp=80,443", "--filter-l7=http,tls", *lists,
            "--out-range=-d8", f"--lua-desync={p['method']}:pos={p['position']}:repeats={p['repeats']}"]
    if c["udp"]:
        args += ["--new", f"--blob=quic:@{app / 'files/quic.bin'}", "--filter-udp=443", "--filter-l7=quic", *lists,
                 "--out-range=-d3", f"--lua-desync=fake:blob=quic:repeats={p['repeats']}"]
    return args


def check_engine(app, state, c, runner=run):
    args = arguments(app, state, c)
    import platform
    expected = {"aarch64": 183, "arm64": 183, "x86_64": 62}.get(platform.machine())
    if elf_machine(args[0]) != expected:
        raise RuntimeError("nfqws2 ELF architecture does not match the host")
    runner([args[0], "--version"])
    runner([*args, "--dry-run"])
    # Unlike --dry-run, --intercept=0 executes Lua initialization and catches
    # engine/Lua ABI mismatches without creating an NFQUEUE listener.
    runner([*args, "--intercept=0"])
    return args
