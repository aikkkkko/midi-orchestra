#!/usr/bin/env python3
"""Scan every release file; print finding categories and relative paths, never values."""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import re

PATTERNS = {
    'private_key': rb'-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----',
    'ssh_public_key': rb'\bssh-(?:rsa|ed25519)\s+[A-Za-z0-9+/]{40,}',
    'github_token': rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})',
    'api_token': rb'\bsk-[A-Za-z0-9_-]{24,}',
    'cloud_access_key': rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'credential_assignment': rb'(?i)\b(?:password|api_key|access_token|client_secret)\s*[=:]\s*[\x22\x27][^\x22\x27\r\n]{8,}[\x22\x27]',
    'personal_unix_path': rb'/(?:Users|home)/[A-Za-z0-9_.-]+(?:/|\\)',
    'personal_windows_path': rb'(?i)[A-Z]:[\\/]+Users[\\/]+[A-Za-z0-9_.-]+',
    'machine_name': rb'(?i)\b(?:DESKTOP|LAPTOP)-[A-Za-z0-9]{5,}\b',
}
TEXT_EXTENSIONS={'.py','.md','.json','.toml','.yml','.yaml','.txt','.ps1'}


def scan(root):
    root=Path(root);findings=[];count=0
    forbidden={'.git','.ssh','.aws','.env','__pycache__','node_modules','.venv','archive','outputs','.runtime'}
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root)
        if p.is_symlink(): findings.append({'file':str(rel),'category':'symlink'});continue
        if not p.is_file():continue
        count+=1
        if any(part in forbidden for part in rel.parts) or p.name in {'known_hosts','authorized_keys','.DS_Store','Thumbs.db'} or p.name.startswith(('id_rsa','id_ed25519','._')) or p.suffix in {'.pem','.key','.pyc'} or '.local.json' in p.name:
            findings.append({'file':str(rel),'category':'excluded_file'})
        raw=p.read_bytes()
        # Binary PCM/MIDI data is not text. Known credential/path signatures still scan all bytes.
        for category,pattern in PATTERNS.items():
            if re.search(pattern,raw):findings.append({'file':str(rel),'category':category})
        if p.suffix in TEXT_EXTENSIONS or p.name in {'LICENSE','.gitignore'}:
            for match in re.finditer(rb'(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])',raw):
                try: address=ipaddress.ip_address(match.group().decode())
                except ValueError:continue
                if address.is_private or address.is_loopback or address.is_link_local:
                    findings.append({'file':str(rel),'category':'private_ip'});break
    return {'status':'passed' if not findings else 'failed','files_scanned':count,'findings':findings,'checks':list(PATTERNS)+['excluded_file','private_ip','symlink'],'limitation':'Pattern scans are supplemented by an explicit source allowlist and manual review; they cannot prove the absence of every possible secret.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root');p.add_argument('--report');args=p.parse_args()
    report=scan(args.root)
    if args.report:Path(args.report).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2));raise SystemExit(0 if report['status']=='passed' else 1)


if __name__=='__main__':main()
