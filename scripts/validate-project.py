#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
plugin=json.loads((root/'plugin.json').read_text())
package=json.loads((root/'package.json').read_text())
assert plugin['api_version']==1 and plugin['flags']==['root']
assert package['type']=='module' and package['version']=='0.1.0'
assert 'remote_binary' not in package
assert 'GNU GENERAL PUBLIC LICENSE' in (root/'LICENSE').read_text()
for path in ['main.py','backend/service.py','configs/zapret2-armada.service','src/index.tsx','docs/INSTALL_RU.md','docs/HARDWARE_TEST_RU.md','THIRD_PARTY_NOTICES.md']:
    assert (root/path).stat().st_size>30,path
lock=json.loads((root/'configs/sources.lock.json').read_text())
assert set(lock)=={'zapret2','lua','zlib','libmnl','libnfnetlink','libnetfilter_queue'}
for name,item in lock.items():
    assert item['url'].startswith('https://') and len(item['sha256'])==64
    source=root/'.cache/sources'/item['file']
    if source.exists():assert hashlib.sha256(source.read_bytes()).hexdigest()==item['sha256'],name
print('Decky metadata, native source pins, license declaration and required files validated')
