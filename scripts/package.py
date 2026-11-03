#!/usr/bin/env python3
"""Create deterministic ZIP layouts, complete source payload and checksums."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'release'
PREFIX='zapret2-armada/'

def put(z,name,data,executable=False):
    info=zipfile.ZipInfo(name,(2026,11,3,0,0,0))
    info.compress_type=zipfile.ZIP_DEFLATED
    info.create_system=3
    info.external_attr=(0o100755 if executable else 0o100644)<<16
    z.writestr(info,data)

def files(names):
    result=[]
    for name in names:
        p=ROOT/name
        if not p.exists():raise FileNotFoundError(p)
        result += [p] if p.is_file() else sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.suffix!='.pyc')
    return result

def validate_zip(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        names=z.namelist()
        assert len(names)==len(set(names))
        assert all(n.startswith(PREFIX) and '..' not in Path(n).parts for n in names)
        assert [n for n in names if n.endswith('/plugin.json') and n.count('/')==1]==[PREFIX+'plugin.json']
        for name in ['main.py','dist/index.js','bin/nfqws2','lua/zapret-lib.lua','lua/zapret-antidpi.lua','sources/zapret2.tar.gz','LICENSE','THIRD_PARTY_NOTICES.md','configs/zapret2-armada.service']:
            assert PREFIX+name in names,name
        engine=z.read(PREFIX+'bin/nfqws2')
        assert engine[:6]==b'\x7fELF\x02\x01' and engine[18:20]==b'\xb7\x00'
        info=json.loads(z.read(PREFIX+'bin/build-info.json'))
        assert hashlib.sha256(engine).hexdigest()==info['sha256']
        assert (z.getinfo(PREFIX+'bin/nfqws2').external_attr>>16)&0o111
        assert json.loads(z.read(PREFIX+'plugin.json'))['flags']==['root']
        print(f'Package validated: {path.name}, {len(names)} entries')

def package():
    from subprocess import run
    run([sys.executable,str(ROOT/'scripts/validate-project.py')],check=True)
    OUT.mkdir(exist_ok=True)
    common=['main.py','backend','configs','LICENSE','THIRD_PARTY_NOTICES.md','README.md','CHANGELOG.md','docs','package.json','plugin.json']
    runtime=files(common+['scripts/install.sh','scripts/uninstall.sh','dist/index.js','bin','lua','files'])
    archive=OUT/'zapret2-armada-v0.1.1-arm64.zip'
    assert (ROOT/'bin/nfqws2').read_bytes()[18:20]==b'\xb7\x00','Refusing non-ARM64 package'
    with zipfile.ZipFile(archive,'w') as z:
        for f in runtime:put(z,PREFIX+str(f.relative_to(ROOT)),f.read_bytes(),f.name=='nfqws2' or f.suffix=='.sh')
        for f in files(['build/licenses']):put(z,PREFIX+'LICENSES/'+str(f.relative_to(ROOT/'build/licenses')),f.read_bytes())
        for f in files(['.cache/sources']):put(z,PREFIX+'sources/'+f.name,f.read_bytes())
    source=OUT/'zapret2-armada-v0.1.1-source.zip'
    with zipfile.ZipFile(source,'w') as z:
        for f in files(common+['src','scripts','tests','.github','.gitignore','package-lock.json','tsconfig.json','rollup.config.js','.cache/sources']):
            put(z,PREFIX+str(f.relative_to(ROOT)),f.read_bytes(),f.suffix=='.sh')
    validate_zip(archive)
    sums=''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in (archive,source))
    (OUT/'SHA256SUMS').write_text(sums)
    print(sums)

if __name__=='__main__':
    if len(sys.argv)>1:validate_zip(Path(sys.argv[1]))
    else:package()
