"""Standard-library controller; private connection settings stay in local config."""
import argparse
import base64
from datetime import datetime, timezone
import importlib.resources
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

from . import __version__

ENGINE_IDS = {"dawdreamer_surge", "fluidsynth_sf2", "midi_ddsp"}
SSH_OPTIONS = ["-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=10"]


def default_config():
    return json.loads(importlib.resources.files("midi_orchestra").joinpath("resources/defaults.json").read_text(encoding="utf-8"))


def validate(data):
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported configuration schema")
    transport = data["transport"]
    if transport["type"] not in ("local", "ssh"):
        raise ValueError("Transport must be local or ssh")
    if transport["type"] == "ssh":
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", transport.get("ssh_alias", "")):
            raise ValueError("Use a preconfigured SSH alias, without username or command options")
        for key in ("work_root", "runner"):
            path = transport.get(key, "")
            if not PureWindowsPath(path).is_absolute() or re.search(r"[\s\"';&|<>]", path):
                raise ValueError("SSH work_root and runner must be absolute Windows paths without shell metacharacters or spaces")
    seen = set()
    for item in data["instruments"]:
        for key in [item["id"]] + item.get("aliases", []):
            if not re.fullmatch(r"[a-z][a-z0-9_]*", key) or key in seen:
                raise ValueError("Invalid or duplicate instrument ID")
            seen.add(key)
        if item["engine"] not in ENGINE_IDS or item["engine"] not in data["engines"]:
            raise ValueError("Unknown instrument engine")
        program = item["midi_program"]
        if type(program) is not int or not 0 <= program <= 127:
            raise ValueError("MIDI program must be an integer from 0 to 127")
    if transport["type"] == "ssh":
        # Relative paths would resolve against the remote login directory.
        for engine_id, engine in data["engines"].items():
            if not engine.get("enabled", False):
                continue
            values = [engine.get(key, "") for key in ("plugin_path", "soundfont_path", "environment_root", "msvc_runtime")]
            values += [engine[key] for key in ("python", "executable") if re.search(r"[\\/]", engine.get(key, ""))]
            values += [item.get("preset_path", "") for item in data["instruments"] if item["engine"] == engine_id]
            if any(value and not PureWindowsPath(value).is_absolute() for value in values):
                raise ValueError("SSH engine paths must be absolute Windows paths on the render host: " + engine_id)
    return data


def load_config(path, required=False):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        if required:
            raise ValueError("Create a private configuration with init before rendering")
        return validate(default_config()), path.parent
    return validate(json.loads(path.read_text(encoding="utf-8"))), path.parent


def select(data, name):
    for item in data["instruments"]:
        if name == item["id"] or name in item.get("aliases", []):
            return item
    raise ValueError("Unknown instrument; use list")


def local_path(value, base):
    path = Path(value).expanduser()
    return str((base / path).resolve() if not path.is_absolute() else path.resolve())


def executable(value, base):
    if "/" not in value and "\\" not in value:
        return value
    # Keep symlinks: a virtual environment's python links to its base interpreter.
    path = Path(value).expanduser()
    return os.path.normpath(path if path.is_absolute() else base / path)


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def remote_ps(transport, script):
    encoded = base64.b64encode(("$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; " + script).encode("utf-16le")).decode("ascii")
    subprocess.run(["ssh", *SSH_OPTIONS, transport["ssh_alias"], "powershell -NoProfile -NonInteractive -EncodedCommand " + encoded], check=True, timeout=1800)


def transfer(transport, source, destination):
    subprocess.run(["scp", *SSH_OPTIONS, str(source), str(destination)], check=True, timeout=1800)


def worker_file():
    return Path(__file__).with_name("worker.py")


def sync(data):
    t = data["transport"]
    if t["type"] != "ssh":
        print("Local transport uses the packaged worker; no synchronization needed.")
        return
    parent = str(PureWindowsPath(t["runner"]).parent)
    remote_ps(t, "New-Item -ItemType Directory -Force -Path " + ps_quote(parent) + "," + ps_quote(t["work_root"]) + " | Out-Null")
    transfer(t, worker_file(), t["ssh_alias"] + ":" + t["runner"].replace("\\", "/"))
    print("Worker synchronized.")


def doctor(data, base):
    t = data["transport"]
    paths = []
    for engine_id, engine in data["engines"].items():
        if not engine.get("enabled", False):
            continue
        paths.append((engine_id + ":python", engine.get("python", "python")))
        for key in ("plugin_path", "executable", "soundfont_path"):
            if engine.get(key):
                paths.append((engine_id + ":" + key, engine[key]))
        for item in data["instruments"]:
            if item["engine"] == engine_id and item.get("preset_path"):
                paths.append((item["id"] + ":preset", item["preset_path"]))
    # Bare interpreter and executable names are looked up on PATH, as render does.
    command = lambda label, value: label.endswith((":python", ":executable")) and "/" not in value and "\\" not in value
    if t["type"] == "ssh":
        paths.append(("worker", t["runner"]))
        checks = []
        for label, value in paths:
            test = "Get-Command -Name " + ps_quote(value) + " -CommandType Application -ErrorAction SilentlyContinue" if command(label, value) else "Test-Path -LiteralPath " + ps_quote(value)
            checks.append("if(" + test + "){Write-Output " + ps_quote("OK " + label) + "}else{Write-Output " + ps_quote("MISSING " + label) + ";$missing=$true}")
        try:
            remote_ps(t, "$missing=$false; " + "; ".join(checks) + "; if($missing){exit 1}")
        except subprocess.CalledProcessError:
            raise ValueError("Install enabled engines or correct their render host paths in configuration") from None
    else:
        missing = []
        for label, value in paths:
            exists = bool(shutil.which(value)) if command(label, value) else Path(local_path(value, base)).exists()
            print(("OK " if exists else "MISSING ") + label)
            if not exists:
                missing.append(label)
        if missing:
            raise ValueError("Install enabled engines or correct their paths in local configuration")


def render(data, base, args):
    item = select(data, args.instrument)
    engine = data["engines"][item["engine"]]
    if not engine.get("enabled", False):
        raise ValueError("This engine is disabled; configure and enable it first")
    if args.cpu and item["engine"] != "midi_ddsp":
        raise ValueError("--cpu applies only to MIDI-DDSP; other engines already use CPU")
    if args.dry and item["engine"] != "fluidsynth_sf2":
        raise ValueError("--dry applies only to FluidSynth")
    midi = Path(args.midi).expanduser().resolve()
    if not midi.is_file() or midi.suffix.lower() not in (".mid", ".midi"):
        raise ValueError("Provide an existing MIDI file")
    job_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + item["id"] + "-" + uuid.uuid4().hex[:8]
    destination = Path(args.out).expanduser().resolve() if args.out else base / "outputs" / job_id
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError("Output directory must be empty; existing files are never overwritten")
    destination.mkdir(parents=True, exist_ok=True)
    t = data["transport"]
    spec = {"schema_version": 1, "job_id": job_id, "instrument_id": item["id"], "engine": item["engine"], "program": item["midi_program"], "track": args.track, "cpu": args.cpu, "dry": args.dry, "normalize": args.normalize, "sample_rate": engine.get("sample_rate", 48000)}
    for key in ("plugin_path", "executable", "soundfont_path", "soundfont_name", "soundfont_license", "soundfont_credit", "soundfont_source", "environment_root", "msvc_runtime"):
        if key in engine:
            spec[key] = engine[key]
    for key in ("preset_path", "preset_sha256", "preset_source", "tail_seconds"):
        if key in item:
            spec[key] = item[key]
    python = engine.get("python", "python")
    if t["type"] == "local":
        for key in ("plugin_path", "soundfont_path", "environment_root", "preset_path", "msvc_runtime"):
            if spec.get(key):
                spec[key] = local_path(spec[key], base)
        if spec.get("executable"):
            spec["executable"] = executable(spec["executable"], base)
        root = Path(local_path(t["work_root"], base))
        directory = root / job_id
        directory.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(midi, directory / "input.mid")
        (directory / "job.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        subprocess.run([executable(python, base), str(worker_file()), str(directory), "--jobs-root", str(root)], check=True, timeout=1800)
        for name in ("mix.wav", "render.json", "prepared.mid", "CREDITS.txt"):
            shutil.copyfile(directory / "result" / name, destination / name)
    else:
        directory = t["work_root"].rstrip("\\/") + "/" + job_id
        remote_ps(t, "New-Item -ItemType Directory -Path " + ps_quote(directory) + " | Out-Null")
        prefix = t["ssh_alias"] + ":" + directory.replace("\\", "/")
        transfer(t, midi, prefix + "/input.mid")
        with tempfile.TemporaryDirectory(prefix="midi-orchestra-job-") as folder:
            request = Path(folder) / "job.json"
            request.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
            transfer(t, request, prefix + "/job.json")
        command = "$env:PYTHONIOENCODING='utf-8'; & " + ps_quote(python) + " " + ps_quote(t["runner"]) + " " + ps_quote(directory) + " --jobs-root " + ps_quote(t["work_root"]) + "; exit $LASTEXITCODE"
        remote_ps(t, command)
        for name in ("mix.wav", "render.json", "prepared.mid", "CREDITS.txt"):
            transfer(t, prefix + "/result/" + name, destination / name)
    print("Complete: " + str(destination / "mix.wav"))


def run(argv=None):
    p = argparse.ArgumentParser(description="MIDI Orchestra: reproducible MIDI instrument rendering")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--config", default="config.local.json", help="Private configuration file")
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create local configuration without overwriting existing files")
    init.add_argument("--out", default="config.local.json")
    listing = sub.add_parser("list")
    listing.add_argument("--family")
    info = sub.add_parser("info"); info.add_argument("instrument")
    sub.add_parser("doctor"); sub.add_parser("sync")
    cmd = sub.add_parser("render")
    cmd.add_argument("instrument"); cmd.add_argument("--midi", required=True); cmd.add_argument("--out")
    cmd.add_argument("--track", type=int); cmd.add_argument("--cpu", action="store_true")
    cmd.add_argument("--dry", action="store_true"); cmd.add_argument("--normalize", action="store_true")
    args = p.parse_args(argv)
    if args.command == "init":
        with Path(args.out).open("x", encoding="utf-8") as f:
            json.dump(default_config(), f, ensure_ascii=False, indent=2); f.write("\n")
        print("Created local configuration; install or configure engines before rendering.")
        return
    data, base = load_config(args.config, required=args.command in ("render", "sync", "doctor"))
    if args.command == "list":
        if args.family and args.family not in {item["family"] for item in data["instruments"]}:
            raise ValueError("Unknown family")
        for item in data["instruments"]:
            if not args.family or item["family"] == args.family:
                state = "enabled" if data["engines"][item["engine"]].get("enabled") else "disabled"
                print(f"{item['id']:16} {item['name']:12} {item['engine']:20} {state}")
    elif args.command == "info":
        item = select(data, args.instrument)
        print(json.dumps({k: v for k, v in item.items() if k != "preset_path"}, ensure_ascii=False, indent=2))
    elif args.command == "doctor": doctor(data, base)
    elif args.command == "sync": sync(data)
    else: render(data, base, args)


def main():
    try:
        run()
    except subprocess.CalledProcessError as error:
        # The command line holds encoded remote scripts and paths; report only the status.
        print("Error: " + Path(str(error.cmd[0])).name + " exited with status " + str(error.returncode), file=sys.stderr)
        raise SystemExit(1)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        print("Error: " + str(error), file=sys.stderr)
        raise SystemExit(1)
