# Configuration and extension

**English** · [简体中文](../configuration.md)

`midi-orchestra init` creates a private `config.local.json` and leaves any existing file as it is. `configs/` holds three generic templates: `local.example.json` (local on Windows), `local-macos.example.json` (local on macOS) and `ssh-windows.example.json` (driving a Windows render machine over SSH). Surge is enabled by default; paths and preset hashes in the templates are filled in by the setup script or by you.

`--config` is a global option and goes before the subcommand:

```bash
midi-orchestra --config config.local.json list
midi-orchestra --config config.local.json render surge_pluck --midi examples/midi/surge_pluck.mid --normalize
```

Relative local paths are resolved against the folder that contains the configuration file. In SSH mode, enabled engines use absolute paths on the Windows render machine, and the configuration check confirms this. `python` and `executable` may be bare command names, which are looked up on PATH; `doctor` and rendering follow the same rule. Each engine sets its own `python`, so environments stay separate, including MIDI-DDSP's TensorFlow environment.

`engines` stores the locations of executables, sample libraries and plugins. `instruments` stores each sound's ID, program, preset location, SHA-256 and tail length in seconds. If your engines are already installed, edit this configuration directly and skip the automatic download.

To add a Surge sound, extract the chunk from a Surge XT 1.3.4 factory FXP preset and wrap it as a VST3 preset with `midi_orchestra.presets.convert_fxp`. Give it a new sound ID and register the SHA-256 of the output file. After rendering a short MIDI test and recording its source credit, it counts as a verified sound. The wrapper uses the Surge XT 1.3.4 plugin class ID; the factory files on Windows and macOS produce byte-identical presets, so presets work on both platforms.

Presets load through `load_vst3_preset`, which works without opening the plugin window and therefore suits SSH sessions too. On Windows, the automatic setup uses a separate official Python runtime, avoiding the older MSVC runtime bundled with some Conda environments; set `msvc_runtime` in the engine configuration to point at a specific system DLL if you need to. On macOS, Surge runs in the virtual environment `.runtime/surge/env` created by setup, and FluidSynth can share it.

The Surge factory file MKS-70 Warm Pad carries the historical internal name Buggy Brass; sounds are identified by file path and SHA-256. Presets with random modulation vary slightly from render to render.
