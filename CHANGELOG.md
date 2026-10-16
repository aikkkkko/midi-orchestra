# Changelog

## 0.1.0 — 2026-10-16

- Standalone controller and isolated render worker; local rendering on Windows x64 and macOS, and SSH rendering on Windows.
- Four fixed Surge presets generated from a user's official installation.
- Optional FluidSynth and MIDI-DDSP adapters with separate Python environments.
- Pinned Surge setup for Windows x64 and macOS (Apple silicon and Intel); on macOS the VST3 plugin and factory patches are taken from the official installer into the project folder.
- `render-midi` agent skill that composes MIDI to a style brief or renders existing MIDI, with a composing guide; source credits.
- Examples: an eight-bar ensemble for piano, violin, cello and the four Surge sounds, plus solo phrases for each sound, all in D major at 88 BPM; MIDI from `scripts/generate_examples.py`, mix from `scripts/mix_examples.py`.
- Surge renders run a short warm-up block after loading the preset, so notes at time zero always sound.
- `doctor` looks up bare `python`/`executable` command names on PATH, locally and over SSH, as rendering does; SSH failures report a status instead of the encoded command line.
- Local mode keeps symlinks in interpreter paths, so virtual environments on macOS and Linux work.
- SSH configurations check that enabled engines use absolute paths; the SSH example uses absolute render-host paths throughout.
- `setup_surge.py` checks for an existing configuration backup before downloading, and reports errors without a traceback.
- Public source separated from private configuration, runtime data and deployment history.
