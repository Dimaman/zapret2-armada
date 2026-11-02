#!/usr/bin/env python3
"""Must run inside `sudo unshare --net`; never uses the host network namespace."""
import copy
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.commands import run
from backend.config_manager import DEFAULT
from backend.nftables_manager import NftablesManager, NFT
from backend.service import queue_ready
from backend.strategy_manager import check_engine

assert Path('/proc/self/ns/net').readlink() != Path('/proc/1/ns/net').readlink(), 'Refusing host namespace'
root=Path(__file__).resolve().parents[1]
run(['/usr/sbin/ip','link','add','wlan-test','type','dummy'])
run(['/usr/sbin/ip','link','set','wlan-test','up'])
run(['/usr/sbin/ip','address','add','198.51.100.1/24','dev','wlan-test'])
run(['/usr/sbin/ip','route','add','1.1.1.1/32','dev','wlan-test'])
run([NFT,'add','table','inet','foreign_sentinel'])
nft=NftablesManager()
child=None
try:
 with tempfile.TemporaryDirectory() as d:
  c=copy.deepcopy(DEFAULT)
  args=check_engine(root,d,c)
  child=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for _ in range(100):
   if queue_ready(child.pid):break
   if child.poll() is not None:raise AssertionError('nfqws2 exited before NFQUEUE readiness')
   time.sleep(.05)
  assert queue_ready(child.pid),'No real NFQUEUE listener'
  nft.apply(False)
  nft.apply(True)
  child.terminate();child.wait(timeout=5)
  assert not queue_ready(child.pid)
  # No listener: a packet must continue to the next rule because of bypass.
  run([NFT,'add','rule','inet','zapret2_armada','output','counter','comment','bypass-probe'])
  with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:s.sendto(b'probe',('1.1.1.1',443))
  data=json.loads(run([NFT,'-j','list','chain','inet','zapret2_armada','output']).stdout)
  counters=[e['counter']['packets'] for x in data['nftables'] for e in x.get('rule',{}).get('expr',[]) if 'counter'in e]
  assert counters and counters[-1]>=1,'Bypass did not continue packet processing'
finally:
 nft.remove()
 if child and child.poll() is None:child.terminate();child.wait(timeout=5)
run([NFT,'list','table','inet','foreign_sentinel'])
print('PASS: real NFQUEUE start/stop, atomic rules, queue bypass after crash, foreign firewall preserved')
