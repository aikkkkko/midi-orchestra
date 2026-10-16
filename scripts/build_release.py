#!/usr/bin/env python3
"""Build deterministic, allowlisted source archives without local deployment data."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import zipfile

from audit_release import scan

NAME='midi-orchestra-0.1.0'
EPOCH=1792108800  # 2026-10-16 UTC
FILES=('README.md','README.zh-CN.md','LICENSE','THIRD_PARTY_NOTICES.md','CHANGELOG.md','pyproject.toml','.gitignore')
DIRECTORIES=('src','scripts','configs','docs','tests','examples','.agents','.github')


def copy_sources(root, target):
    for name in FILES:
        shutil.copyfile(root/name,target/name)
    for name in DIRECTORIES:
        for source in sorted((root/name).rglob('*')):
            if source.is_symlink():raise ValueError('Symlinks are not allowed in release inputs')
            if not source.is_file():continue
            rel=source.relative_to(root)
            if '__pycache__' in rel.parts or any(part.endswith('.egg-info') for part in rel.parts) or source.suffix in ('.pyc','.pyo'):
                continue
            destination=target/rel;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',default='../release-artifacts');args=p.parse_args()
    root=Path(__file__).resolve().parents[1];out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    outputs=[out/(NAME+'.zip'),out/(NAME+'.tar.gz'),out/'SHA256SUMS.txt']
    if any(path.exists() for path in outputs):raise ValueError('Release artifacts already exist; choose a new output directory')
    with tempfile.TemporaryDirectory(prefix='midi-orchestra-source-') as temporary:
        target=Path(temporary)/NAME;target.mkdir();copy_sources(root,target)
        audit=scan(target)
        if audit['status']!='passed':raise ValueError(json.dumps(audit))
        (target/'PUBLICATION_AUDIT.json').write_text(json.dumps(audit,indent=2)+'\n')
        manifest=[]
        for file in sorted(target.rglob('*')):
            if file.is_file():manifest.append(hashlib.sha256(file.read_bytes()).hexdigest()+'  '+file.relative_to(target).as_posix())
        (target/'MANIFEST.sha256').write_text('\n'.join(manifest)+'\n')
        with zipfile.ZipFile(outputs[0],'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
            for file in sorted(target.rglob('*')):
                if not file.is_file():continue
                member=zipfile.ZipInfo(NAME+'/'+file.relative_to(target).as_posix(),(2026,10,16,0,0,0))
                member.create_system=3;member.external_attr=(0o100644<<16);member.compress_type=zipfile.ZIP_DEFLATED
                archive.writestr(member,file.read_bytes())
        with outputs[1].open('wb') as raw, gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=EPOCH) as compressed, tarfile.open(fileobj=compressed,mode='w') as archive:
            for file in sorted(target.rglob('*')):
                if not file.is_file():continue
                payload=file.read_bytes();member=tarfile.TarInfo(NAME+'/'+file.relative_to(target).as_posix());member.size=len(payload);member.mode=0o644;member.uid=member.gid=0;member.uname=member.gname='';member.mtime=EPOCH
                archive.addfile(member,io.BytesIO(payload))
        outputs[2].write_text('\n'.join(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name for path in outputs[:2])+'\n')
        print(json.dumps({'status':'passed','files':len(manifest)+1,'archives':[p.name for p in outputs[:2]]},indent=2))


if __name__=='__main__':main()
