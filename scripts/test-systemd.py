#!/usr/bin/env python3
"""Disposable-runner integration: real install/start/restart/stop/uninstall.

The service and this driver share an isolated network namespace. No host
firewall changes occur. Refuses existing installation paths or existing unit.
"""
import copy
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.commands import run
from backend.config_manager import DEFAULT
from backend.nftables_manager import NFT
from backend.zapret_manager import ZapretManager, ROOT, LOG, UNIT, MODULES

plugin=Path(__file__).resolve().parents[1]
dropin=Path('/etc/systemd/system/zapret2-armada.service.d')

def inside():
    assert Path('/proc/self/ns/net').readlink()!=Path('/proc/1/ns/net').readlink(),'Refusing host namespace'
    manager=ZapretManager(plugin)
    try:
        run([NFT,'add','table','inet','foreign_systemd_sentinel'])
        manager.install()
        assert manager.installed()
        desired=copy.deepcopy(DEFAULT);desired['enabled']=True
        manager.apply(desired)
        assert manager.status()['engine_running'] and manager.nft.owned()
        manager.apply({**desired,'active':'split-2'})
        assert manager.status()['engine_running']
        manager.apply({**desired,'enabled':False,'active':'split-2'})
        assert not manager.active() and not manager.nft.owned()
        manager.uninstall()
        assert not UNIT.exists() and not MODULES.exists() and not (ROOT/'app').exists()
        run([NFT,'list','table','inet','foreign_systemd_sentinel'])
        print('PASS: actual hardened systemd service install/start/restart/stop/uninstall in isolated network')
    finally:
        try:manager.uninstall()
        except Exception as e:print('Cleanup:',e,file=sys.stderr)

if __name__=='__main__':
    if '--inside' in sys.argv:
        inside()
    else:
        assert os.geteuid()==0
        for p in (ROOT,LOG,UNIT,MODULES,dropin):assert not p.exists(),f'Existing path: refusing test: {p}'
        namespace=f'za-test-{os.getpid()}'
        run(['/usr/sbin/ip','netns','add',namespace])
        try:
            dropin.mkdir(parents=True)
            (dropin/'test-namespace.conf').write_text(f'[Service]\nNetworkNamespacePath=/run/netns/{namespace}\n')
            run(['/usr/sbin/ip','netns','exec',namespace,'/usr/bin/python3',str(Path(__file__).resolve()),'--inside'],timeout=120)
        except Exception:
            logs=run(['/usr/bin/journalctl','-u','zapret2-armada.service','-n','100','--no-pager'],check=False)
            print(logs.stdout,file=sys.stderr)
            raise
        finally:
            run(['/usr/bin/systemctl','stop','zapret2-armada.service'],check=False)
            for p in (UNIT,MODULES):
                if p.exists() and p.read_text().startswith('# zapret2-armada-managed-v1'):p.unlink()
            for p in (dropin,ROOT,LOG):
                if p.exists():shutil.rmtree(p)
            run(['/usr/bin/systemctl','daemon-reload'])
            run(['/usr/sbin/ip','netns','delete',namespace])
