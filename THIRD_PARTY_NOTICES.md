# Third-party components and audio sources

The MIT license covers the original controller/worker, setup and packaging code, documentation and authored MIDI examples in this repository. Third-party engines, sample libraries, presets, models and dependencies keep their own licenses; their executables, weights, SF2 files and factory preset binaries come from their official sources during installation.

- DawDreamer: https://github.com/DBraun/DawDreamer (GPL-3.0; also see upstream dependency notices).
- Surge XT: https://github.com/surge-synthesizer/surge ; official 1.3.4 packages: https://github.com/surge-synthesizer/releases-xt/releases/tag/1.3.4 (GPL-3.0; preserve upstream content notices in the downloaded package).
- FluidSynth: https://github.com/FluidSynth/fluidsynth (LGPL; refer to the selected release).
- MIDI-DDSP: https://github.com/magenta/midi-ddsp (refer to upstream code, model and dataset notices).
- Python: https://www.python.org/ (PSF license; downloaded separately).
- FreePats YDP Grand Piano 2016-08-04, used in the piano and ensemble demonstrations: FreePats / Roberto; Yamaha Disklavier Pro samples recorded by Zenph Studios / Dr. Mikhail Krishtal for OLPC. Source: https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html . Attribution license: https://creativecommons.org/licenses/by/3.0/ . Changes in the demonstrations: MIDI performance, reverb, filtering, level adjustment, mixing, limiting and final fade.
- MIDI-DDSP official URMP pretrained model, used for the violin and cello in the demonstrations; refer to the upstream model and dataset notices.

Audio example credits and the exact selected factory sounds are in examples/CREDITS.md. Retain those credits when sharing the demonstrations; they apply alongside the source-code license.
