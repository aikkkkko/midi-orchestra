#!/usr/bin/env python3
"""Install a pinned, isolated Surge XT runtime on Windows x64 or macOS from official downloads."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))
from midi_orchestra.cli import default_config
from midi_orchestra.presets import FACTORY_PRESETS, convert_fxp

RELEASES = 'https://github.com/surge-synthesizer/releases-xt/releases/download/1.3.4/'
DOWNLOADS = {
    'windows': (
        ('surge-xt-win64-1.3.4-portable-install.zip', RELEASES + 'surge-xt-win64-1.3.4-portable-install.zip',
         'a5f2376702ad218c0382640ed0c7b9ebb222ba2410a210879899c0f726859d8e'),
        ('python-3.11.9-embed-amd64.zip', 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip',
         '009d6bf7e3b2ddca3d784fa09f90fe54336d5b60f0e0f305c37f400bf83cfd3b'),
    ),
    'macos': (
        ('surge-xt-macOS-1.3.4.dmg', RELEASES + 'surge-xt-macOS-1.3.4.dmg',
         'b56e8d51a8dc2382ae668c9ff4e96bae38dbd452af4e584d5a5ef50ab2d09b07'),
    ),
}
# DawDreamer 0.9.0 publishes wheels for these Python versions.
MACOS_PYTHONS = ((3, 11), (3, 12), (3, 13), (3, 14))


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def fetch(folder, name, url, digest):
    destination = folder / name
    if destination.exists() and sha256(destination) == digest:
        return destination
    temporary = destination.with_suffix(destination.suffix + '.part')
    print('Downloading ' + name, flush=True)
    with urllib.request.urlopen(url, timeout=90) as source, temporary.open('wb') as output:
        while chunk := source.read(1024 * 1024):
            output.write(chunk)
    if sha256(temporary) != digest:
        raise ValueError('Download checksum mismatch: ' + name)
    temporary.replace(destination)
    return destination


def extract(archive, target):
    target = target.resolve()
    with zipfile.ZipFile(archive) as source:
        for item in source.infolist():
            path = (target / item.filename).resolve()
            if path != target and target not in path.parents:
                raise ValueError('Unsafe archive member')
        source.extractall(target)


def platform_name(system=None, machine=None):
    system = system or platform.system()
    machine = (machine or platform.machine()).lower()
    if system == 'Windows' and machine in ('amd64', 'x86_64'):
        return 'windows'
    if system == 'Darwin' and machine in ('arm64', 'x86_64'):
        return 'macos'
    raise ValueError('Automatic setup covers Windows x64 and macOS; configure other systems by hand (docs/configuration.md)')


def requirements(python):
    subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(REPO / 'scripts/requirements-surge.txt')], check=True)


def install_windows(root, archives):
    extract(archives[0], root / 'portable')
    extract(archives[1], root / 'python')
    env = root / 'env'
    bootstrap = env / 'Scripts/python.exe'
    if not bootstrap.exists():
        subprocess.run([sys.executable, '-m', 'venv', str(env)], check=True)
    requirements(bootstrap)
    # Official embedded CPython avoids inherited Conda DLL search order.
    (root / 'python/python311._pth').write_text('python311.zip\n.\n..\\env\\Lib\\site-packages\nimport site\n', encoding='utf-8')
    data = root / 'portable/Surge Synth Team'
    return root / 'python/python.exe', data / 'Surge XT.vst3', data / 'SurgeXTData/patches_factory'


def install_macos(root, archives):
    """Copy the VST3 bundle and factory patches out of the official installer; nothing is installed system-wide."""
    plugin, factory = root / 'Surge XT.vst3', root / 'patches_factory'
    with tempfile.TemporaryDirectory(prefix='surge-installer-') as temporary:
        mount, expanded = Path(temporary) / 'mount', Path(temporary) / 'expanded'
        subprocess.run(['hdiutil', 'attach', '-nobrowse', '-readonly', '-noautoopen', '-mountpoint', str(mount), str(archives[0])],
                       check=True, stdout=subprocess.DEVNULL)
        try:
            subprocess.run(['pkgutil', '--expand-full', str(mount / 'surge-xt-macOS-1.3.4.pkg'), str(expanded)], check=True)
        finally:
            subprocess.run(['hdiutil', 'detach', str(mount), '-quiet'], check=True)
        for source, target in ((expanded / 'Surge_XT_VST3.pkg/Payload/Surge XT.vst3', plugin),
                               (expanded / 'Surge_XT_Resources.pkg/Payload/patches_factory', factory)):
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target, symlinks=True)
    python = root / 'env/bin/python'
    if not python.exists():
        subprocess.run([sys.executable, '-m', 'venv', str(root / 'env')], check=True)
    requirements(python)
    return python, plugin, factory


def refuse_existing_backup(config_path):
    """Stop before downloading anything if the configuration backup slot is taken."""
    backup = config_path.with_suffix('.json.bak')
    if config_path.exists() and backup.exists():
        raise ValueError('Configuration backup already exists: ' + backup.name + '; move it away, then run setup again')
    return backup


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', default='.runtime/surge')
    p.add_argument('--config', default='config.local.json')
    args = p.parse_args()
    name = platform_name()
    if name == 'windows' and sys.version_info[:2] != (3, 11):
        raise ValueError('Run setup with Python 3.11 (for example: py -3.11 scripts/setup_surge.py)')
    if name == 'macos' and sys.version_info[:2] not in MACOS_PYTHONS:
        raise ValueError('Run setup with Python 3.11 to 3.14 (for example: python3.12 scripts/setup_surge.py)')
    root = Path(args.root).resolve()
    config_path = Path(args.config).resolve()
    data = json.loads(config_path.read_text(encoding='utf-8')) if config_path.exists() else default_config()
    if data['transport']['type'] != 'local':
        raise ValueError('Run setup on the render machine with a local configuration')
    backup = refuse_existing_backup(config_path)
    downloads = root / 'downloads'
    downloads.mkdir(parents=True, exist_ok=True)
    archives = [fetch(downloads, *item) for item in DOWNLOADS[name]]
    python, plugin, factory = (install_windows if name == 'windows' else install_macos)(root, archives)
    engine = data['engines']['dawdreamer_surge']
    engine.update(enabled=True, python=str(python), plugin_path=str(plugin), sample_rate=48000)
    engine.pop('msvc_runtime', None)
    runtime = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/msvcp140.dll'
    if name == 'windows' and runtime.is_file():
        engine['msvc_runtime'] = str(runtime)
    for item in data['instruments']:
        if item['id'] in FACTORY_PRESETS:
            preset = root / 'presets' / (item['id'] + '.vstpreset')
            item['preset_sha256'] = convert_fxp(factory / FACTORY_PRESETS[item['id']], preset)
            item['preset_path'] = str(preset)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        with backup.open('x', encoding='utf-8') as stream:
            stream.write(config_path.read_text(encoding='utf-8'))
    temporary = config_path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temporary.replace(config_path)
    print('Installed Surge XT 1.3.4 and fixed presets. Run midi-orchestra doctor, then render a MIDI example.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print('Error: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
