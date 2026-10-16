# Sounds and engines

**English** · [简体中文](../engines.md)

## Surge XT + DawDreamer

Verified with Surge XT 1.3.4 and DawDreamer 0.9.0: offline CPU rendering with polyphony and velocity, 48 kHz stereo by default. The setup script builds four fixed presets on both Windows x64 and macOS. The plugin and factory sounds are downloaded from the official release during setup; the release package holds this project's code.

## FluidSynth

On Windows, download it from the [FluidSynth releases](https://github.com/FluidSynth/fluidsynth/releases); on macOS, install it with Homebrew: `brew install fluid-synth`. Then choose an SF2 SoundFont you are licensed to use. The Python environment FluidSynth jobs run in needs numpy, pretty_midi and soundfile: install this project's `render` extra, or on macOS use `.runtime/surge/env/bin/python` created by setup. Then set `executable`, `soundfont_path` and the exact source, author and license in the configuration, and enable `fluidsynth_sf2`.

The adapter uses the default bank, with programs counted from 0. A piano SoundFont contains piano sounds; for other banks, drums or special channels, extend the adapter. A recommended piano is [FreePats](https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html), which is the piano in the demos.

## MIDI-DDSP

[MIDI-DDSP](https://github.com/magenta/midi-ddsp) runs in its own environment and is installed as needed: follow the official instructions for the code, TensorFlow/DDSP and the pretrained weights, then set its `python` (and `environment_root` if needed) in the configuration and enable `midi_ddsp`.

The verified combination is Python 3.8.20, TensorFlow 2.7.0, DDSP 3.2.0 and MIDI-DDSP 0.2.6, kept separate from Surge's Python environment. These dependencies are from an earlier generation and fit best on a Windows machine with an NVIDIA GPU, which Macs and other computers drive over [SSH](ssh.md). Get the weights and the CUDA runtime from their official sources.

The model offers 13 instruments, each track playing one note at a time, with 16 kHz output by default. Violin and cello have been rendered and listened to; for the other instruments, listen to a short test the first time you use them. Jobs use the GPU by default and point you to the environment check whenever the GPU needs attention; add `--cpu` to render on the CPU.

The model samples its own expression, so every render of the same MIDI comes out a little different; render important passages a few times and pick the best. During long rests the model outputs low-level noise (about 10–20 dB below the playing level): when a part enters late, open it from its entry point in the mix, or render only the segments that contain notes and align them afterwards. Render time grows with the total duration, rests included.
