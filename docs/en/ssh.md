# Rendering on a Windows machine over SSH

**English** · [简体中文](../ssh.md)

Install the engines on the Windows render machine and this tool on the controlling computer (Windows, macOS or Linux). SSH/SCP, the Windows OpenSSH server, key authentication and host fingerprint checks all use your own system configuration.

1. Copy `configs/ssh-windows.example.json` to `config.local.json`.
2. Replace the template alias `render-host` with an SSH alias you have already configured. Passwords and keys stay in SSH's own configuration; the JSON holds only the alias.
3. Set `work_root` and `runner` to absolute Windows paths of your choice, using folder names without spaces; engine, plugin and preset paths may contain spaces.
4. Fill in the engine Python, plugin and preset paths, and the `preset_sha256` values produced by setup in place of the placeholder `generated-by-setup`. Enabled engines use absolute paths on the render machine; `python` and `executable` may also be bare command names (such as `fluidsynth`), which `doctor` looks up on the render machine's PATH.
5. Copy the worker over, then check and render:

```bash
midi-orchestra sync
midi-orchestra doctor
midi-orchestra render surge_pad --midi examples/midi/surge_pad.mid --normalize
```

`sync` copies only the worker script; engines, models and your private configuration stay where they are. Every render gets its own job folder, with the original input kept separate from the prepared MIDI. SSH runs with BatchMode and StrictHostKeyChecking, so it connects only to hosts whose fingerprints you have already confirmed.

Use a dedicated folder for render jobs. Remote jobs and local outputs can contain real deployment paths or input material, so keep them private; the release tooling packages only allowlisted files.

On a Mac you can keep two configurations side by side: one that renders Surge and piano locally, and one that drives a Windows GPU machine for the MIDI-DDSP instruments over SSH. Switch between them with `--config`.
