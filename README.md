# MIDI Orchestra

**English** · [简体中文](README.zh-CN.md)

MIDI Orchestra gives an AI agent an orchestra for short-video soundtracks: background music, mood beds and transitions played on piano, strings, winds, brass and synths. Describe the style you want and the agent writes the MIDI and renders it, or hand it a MIDI file you already have. It comes with a `render-midi` skill for agents and a command-line tool you can use directly.

## Listen

[▶ 25-second ensemble](examples/audio/ensemble.wav): a piano theme, then a violin with a cello countermelody, over pad, bass, pluck and texture layers. The music was written as MIDI by a script and every part was rendered by this tool.

One sound at a time: [piano](examples/audio/piano.wav) · [violin](examples/audio/violin.wav) · [soft pad](examples/audio/surge_pad.wav) · [synth bass](examples/audio/surge_bass.wav) · [pluck](examples/audio/surge_pluck.wav) · [transition texture](examples/audio/surge_texture.wav)

## Sounds

| ID | Sound | Engine | Windows x64 | macOS |
|---|---|---|---|---|
| `surge_pad`, `surge_bass`, `surge_pluck`, `surge_texture` | Soft pad, synth bass, pluck, transition texture | Surge XT 1.3.4 factory presets | Setup script | Setup script |
| `piano` | Sampled piano | FluidSynth + an SF2 you choose | FluidSynth release + SF2 | Homebrew `fluid-synth` + SF2 |
| `violin`, `viola`, `cello`, `double_bass`, `flute`, `oboe`, `clarinet`, `saxophone`, `bassoon`, `trumpet`, `horn`, `trombone`, `tuba` | Acoustic instruments | MIDI-DDSP neural models | Local, GPU recommended | Over SSH on a Windows GPU machine |

`midi-orchestra list` shows the catalog and which engines are enabled.

## Use it with an agent

The skill lives in [.agents/skills/render-midi/](.agents/skills/render-midi/SKILL.md). Open the project in an agent workspace that discovers `.agents/skills`, or install the whole skill folder the way your agent expects. After installing the tool (below), you can ask for music by style:

> Use render-midi to write 30 seconds of warm, hopeful background music for my product video: piano melody, soft pad, light pluck rhythm, about 90 BPM. Render each part as its own WAV for mixing, and include the source credits.

The agent settles the key, tempo and form, writes a multi-track MIDI file, renders each part and returns the audio with its render report. It works the same way with your own MIDI: "render track 1 of this file on violin".

## Install

### Windows x64

Python 3.11 x64 and the Microsoft C++ runtime. From the project folder:

```powershell
py -3.11 -m pip install .
py -3.11 scripts/setup_surge.py
midi-orchestra doctor
```

### macOS (Apple Silicon or Intel)

Python 3.11–3.14, for example from Homebrew. From the project folder:

```bash
python3 -m pip install .
python3 scripts/setup_surge.py
midi-orchestra doctor
```

The setup script downloads Surge XT 1.3.4 from its official release and checks its SHA-256 (about 313 MB on Windows, including a separate Python 3.11.9 runtime; about 400 MB on macOS). On macOS it takes the VST3 plugin and factory patches straight from the official installer into the project's `.runtime/` folder, with no administrator install. It then builds the four synth presets and writes your private `config.local.json`, keeping a backup of any previous one.

For the piano, add FluidSynth (`brew install fluid-synth` on macOS) and a SoundFont; MIDI-DDSP instruments run in their own GPU environment. See [engines](docs/en/engines.md). The command-line tool itself only needs the Python standard library, so any computer can drive a Windows render machine over SSH; see [SSH rendering](docs/en/ssh.md). Connection details stay in your private configuration.

## Render from the command line

```bash
midi-orchestra list
midi-orchestra render surge_pad --midi examples/midi/surge_pad.mid --normalize
midi-orchestra render violin --midi song.mid --track 1 --normalize
```

Each job writes to `outputs/<job>/`:

- `mix.wav`: 24-bit PCM audio
- `prepared.mid`: the MIDI that was actually played
- `render.json`: format, timing, peak level and preset checksum
- `CREDITS.txt`: engine, sound and source attribution

Your input MIDI stays as it was, and every job writes to a new or empty folder. For several instruments, render one track per instrument with `--track` and mix the WAVs afterwards. [examples/CREDITS.md](examples/CREDITS.md) shows the full workflow that produced the demos above.

## Good to know

- MIDI-DDSP instruments play one note at a time per track and output 16 kHz audio. Each render has its own phrasing, so render important parts a few times and keep the best take.
- Piano and synths play chords. Drum tracks (MIDI channel 10) go to your usual drum tool.
- Each Surge ID keeps its fixed preset, while CC and pitch bend go to the synth.
- Engines, sample libraries and models come from their own projects under their own licenses. Keep their credits with any audio you publish.

## Documentation

[Configuration](docs/en/configuration.md) · [Engines](docs/en/engines.md) · [SSH rendering](docs/en/ssh.md) · [Agent skill](docs/en/agent-skill.md) · [Validation](docs/en/validation.md) · [Release and privacy](docs/en/releasing.md)

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/audit_release.py .
```

The examples are reproducible. [scripts/generate_examples.py](scripts/generate_examples.py) writes the MIDI and [scripts/mix_examples.py](scripts/mix_examples.py) mixes the rendered parts.

## License

The original code is MIT licensed. Third-party engines, presets, samples and models keep their own licenses; see [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md).
