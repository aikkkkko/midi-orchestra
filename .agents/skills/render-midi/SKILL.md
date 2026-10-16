---
name: render-midi
description: Compose MIDI in a requested style and render it, or render existing MIDI files, into instrument audio with an installed midi-orchestra CLI (fixed Surge presets, FluidSynth SF2, or an existing MIDI-DDSP environment). Use for short-video background music, mood beds, transitions, instrument auditions and rendering MIDI parts.
---

Work with the installed `midi-orchestra` command and the user's private configuration. If the command is missing, point the user to the repository README for installation. Report only results the tool actually produced.

Read [engine guidance](references/engines.md) when choosing sounds, and [composing guidance](references/composing.md) when writing music.

## When the user describes music instead of providing MIDI

Compose it. Settle the brief first: mood or style, length in seconds, tempo, key, and which sounds from `midi-orchestra list` are enabled. Then write a format 1 MIDI file with one track per part, using a short script (the `write_midi` helper in `scripts/generate_examples.py` is a standard-library example). Keep every note on the beat grid of the tempo you declare. Save the script next to the MIDI so the piece can be revised and regenerated.

## Rendering

- Use `list` and `info` to inspect the catalog. Run `doctor` when environment readiness is unknown; a passed path check confirms paths, while audio quality is confirmed by listening.
- Keep the user's chosen instrument and input file. Render each instrument separately with `--track`, and keep the original MIDI.
- MIDI-DDSP plays one note at a time per track. Split overlapping voices into separate tracks or choose a polyphonic engine, so every note is kept. A sound listed in the catalog may still need a first listening check.
- Write each render to a new or empty output folder. Use `--normalize` for whole-track peak normalization, then set the balance between parts when mixing.
- Read the returned render report and source credits. Return playable audio together with the instrument, sample rate, timing scope and material limitations. Describe numeric checks as measurements and leave listening judgments to the user.
- Keep user configuration, authentication data, machine paths and runtime logs in private locations, outside published source or examples. Use the existing SSH authentication and keep private keys where they are.

For a custom configuration, use `midi-orchestra --config <private-config> <command>`. The global option precedes the subcommand.
