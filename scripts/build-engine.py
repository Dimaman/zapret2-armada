#!/usr/bin/env python3
"""Build pinned nfqws2 and static third-party libs; glibc remains a system lib.

Native: python scripts/build-engine.py
Cross: TARGET=aarch64-linux-gnu CC=aarch64-linux-gnu-gcc
       AR=aarch64-linux-gnu-ar RANLIB=aarch64-linux-gnu-ranlib python scripts/build-engine.py
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "build/engine"
DEPS = WORK / "deps"
CACHE = ROOT / ".cache/sources"


def command(args, cwd, env):
    subprocess.run(args, cwd=cwd, env=env, check=True)


def build():
    lock = json.loads((ROOT / "configs/sources.lock.json").read_text())
    CACHE.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    DEPS.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({"CC": os.getenv("CC", "cc"), "AR": os.getenv("AR", "ar"),
                "RANLIB": os.getenv("RANLIB", "ranlib"), "CFLAGS": "-O2 -fPIC",
                "PKG_CONFIG_LIBDIR": str(DEPS / "lib/pkgconfig"), "PKG_CONFIG_PATH": str(DEPS / "lib/pkgconfig")})
    target = os.getenv("TARGET", "")
    paths = {}
    for name, item in lock.items():
        archive = CACHE / item["file"]
        if not archive.exists():
            req = urllib.request.Request(item["url"], headers={"User-Agent": "zapret2-armada-source-builder/0.1.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                archive.write_bytes(r.read(20_000_000))
        if hashlib.sha256(archive.read_bytes()).hexdigest() != item["sha256"]:
            raise RuntimeError(f"Source SHA256 mismatch: {name}")
        dest = WORK / name
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir()
        with tarfile.open(archive) as t:
            t.extractall(dest, filter="data")
        paths[name] = next(dest.iterdir())
    jobs = f"-j{min(os.cpu_count() or 2, 4)}"
    for name in ("libmnl", "libnfnetlink", "libnetfilter_queue"):
        args = ["./configure", f"--prefix={DEPS}", "--disable-shared", "--enable-static", "--disable-dependency-tracking"]
        if target:
            args += [f"--host={target}"]
        command(args, paths[name], env)
        command(["make", jobs], paths[name], env)
        command(["make", "install"], paths[name], env)
    lua = paths["lua"] / "src"
    command(["make", jobs, "liblua.a", f"CC={env['CC']}", f"AR={env['AR']} rcu", f"RANLIB={env['RANLIB']}", "MYCFLAGS=-O2 -fPIC -DLUA_USE_LINUX"], lua, env)
    (DEPS / "include/lua").mkdir(parents=True, exist_ok=True)
    for f in lua.glob("*.h"):
        shutil.copy(f, DEPS / "include/lua" / f.name)
    shutil.copy(lua / "liblua.a", DEPS / "lib/liblua.a")
    command(["./configure", f"--prefix={DEPS}", "--static"], paths["zlib"], env)
    command(["make", jobs, "install"], paths["zlib"], env)
    engine_env = dict(env)
    engine_env["CFLAGS"] += f" -I{DEPS / 'include'} -DZAPRET_GH_VER=v1.0.6 -DZAPRET_GH_HASH=pinned-source-sha256"
    # libc/libm/libdl are intentionally linked as platform system libraries.
    engine_env["LDFLAGS"] = f"-L{DEPS / 'lib'}"
    command(["make", jobs, "LUA_JIT=0", f"LUA_CFLAGS=-I{DEPS / 'include/lua'}", f"LUA_LIB=-L{DEPS / 'lib'} -llua -ldl"], paths["zapret2"] / "nfq2", engine_env)
    for folder in ("bin", "lua", "files", "build/licenses"):
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    shutil.copy(paths["zapret2"] / "nfq2/nfqws2", ROOT / "bin/nfqws2")
    for name in ("zapret-lib.lua", "zapret-antidpi.lua"):
        shutil.copy(paths["zapret2"] / "lua" / name, ROOT / "lua" / name)
    shutil.copy(paths["zapret2"] / "files/fake/quic_initial_www_google_com.bin", ROOT / "files/quic.bin")
    for name, source in paths.items():
        dest = ROOT / "build/licenses" / name
        dest.mkdir(exist_ok=True)
        for f in source.rglob("*"):
            if f.is_file() and (f.name.lower() in {"copying", "copying.lib", "license", "license.txt", "copyright", "readme", "sha.h"}):
                rel = f.relative_to(source)
                (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(f, dest / rel)
    info = {"version": "Zapret2 v1.0.6 / Lua 5.4.8", "source_sha256": lock["zapret2"]["sha256"],
            "sha256": hashlib.sha256((ROOT / "bin/nfqws2").read_bytes()).hexdigest(), "target": target or os.uname().machine}
    (ROOT / "bin/build-info.json").write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps(info))


if __name__ == "__main__":
    build()
