#!/usr/bin/env python3
"""Verify architecture, declared system dependencies and all permitted Lua templates."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.config_manager import DEFAULT
from backend.strategy_manager import check_engine, elf_machine

root=Path(__file__).resolve().parents[1]
machine=elf_machine(root/'bin/nfqws2')
assert machine == (183 if sys.argv[-1]=='arm64' else 62), machine
info=json.loads((root/'bin/build-info.json').read_text())
assert info['sha256']==hashlib.sha256((root/'bin/nfqws2').read_bytes()).hexdigest()
r=subprocess.run(['readelf','-d',str(root/'bin/nfqws2')],capture_output=True,text=True,check=True)
needed=[line.split('[')[1].split(']')[0] for line in r.stdout.splitlines() if '(NEEDED)' in line]
assert set(needed) <= {'libc.so.6','libm.so.6','libdl.so.2','libpthread.so.0','ld-linux-aarch64.so.1','ld-linux-x86-64.so.2'}, needed
for p in DEFAULT['profiles']:
 for udp in (False,True):
  c=copy.deepcopy(DEFAULT);c['active']=p['id'];c['udp']=udp
  with tempfile.TemporaryDirectory() as d:check_engine(root,d,c)
print(json.dumps({'ELF_machine':machine,'needed':needed,'profiles_tested':6,'version':info['version']}))
