"""No shell, fixed system tool paths, bounded execution and sanitized environment."""
import os
import subprocess

ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8", "HOME": "/root"}


def run(argv, *, text=None, timeout=20, check=True):
    r = subprocess.run([str(x) for x in argv], input=text, capture_output=True,
                       text=True, env=ENV, timeout=timeout, check=False)
    if check and r.returncode:
        raise RuntimeError(f"{os.path.basename(str(argv[0]))}: {(r.stderr or r.stdout)[-2500:]}")
    return r
