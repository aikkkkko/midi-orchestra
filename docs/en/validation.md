# v0.1.0 validation record

**English** · [简体中文](../validation.md)

Date: 2026-10-16.

## Windows x64 (over SSH)

The `midi-orchestra` command from this source drove a Windows x64 render machine over SSH: `sync` uploaded this version's worker, `doctor` passed every check, and every demo file was rendered along this path. The real host, configuration, paths and raw job records are kept in a private environment.

| Render job | Engine | Audio length | Synthesis time | Output |
|---|---|---:|---:|---|
| `surge_pad` | Surge | 19.30s | 1.01s | 48000Hz / 2ch |
| `surge_bass` | Surge | 19.06s | 0.71s | 48000Hz / 2ch |
| `surge_pluck` | Surge | 19.64s | 1.31s | 48000Hz / 2ch |
| `surge_texture` | Surge | 19.64s | 1.27s | 48000Hz / 2ch |
| `piano` | FluidSynth | 18.50s | 0.27s | 48000Hz / 2ch |
| `violin` | MIDI-DDSP (GPU) | 14.30s | 47.65s | 16000Hz / 1ch |
| `ensemble.mid --track 0` piano | FluidSynth | 27.36s | 0.27s | 48000Hz / 2ch |
| `--track 1` violin | MIDI-DDSP (GPU) | 24.01s | 64.32s | 16000Hz / 1ch |
| `--track 2` cello | MIDI-DDSP (GPU) | 24.01s | 64.97s | 16000Hz / 1ch |
| `--track 3` surge_pad | Surge | 28.84s | 1.18s | 48000Hz / 2ch |
| `--track 4` surge_bass | Surge | 28.77s | 0.78s | 48000Hz / 2ch |
| `--track 5` surge_pluck | Surge | 27.82s | 1.34s | 48000Hz / 2ch |
| `--track 6` surge_texture | Surge | 29.18s | 1.10s | 48000Hz / 2ch |

Timing covers engine initialization and synthesis; transfer, MIDI preparation and the final PCM write are counted separately. Every job passed the non-silence, finite-value, peak and 24-bit PCM checks, and Surge presets were verified by SHA-256. `doctor`'s PATH lookup of command names was also checked on the real host, with one command present and one absent.

## macOS 15 (Apple silicon)

- The setup script took the Surge XT VST3 plugin and factory sounds from the official dmg (SHA-256 pinned) in 12 seconds with the dmg already downloaded. The copied plugin passed its code-signature check, `doctor` passed every check, and a repeated run backed up the existing configuration first.
- All four Surge sounds rendered locally with exactly the same lengths as on Windows, band energies within 0.2 dB and envelope correlations of 0.87–0.98 (the texture preset has random modulation). The four presets built from the macOS factory files have the same SHA-256 as on Windows.
- Homebrew's FluidSynth 2.6.1 rendered the piano with a sample-level correlation of 1.0000 to the Windows result.

## Fixed in this round

- Surge applies a loaded preset at its first audio block, so the previous worker dropped notes at t=0 (re-rendering the original pad example lost the whole first chord, with the first sound at 3.0 s). The worker now renders a 0.1 s warm-up after loading the preset; on the same probe MIDI the first sound moved from 4.09 s to 0.00 s.
- Local mode used to resolve symlinks in the interpreter path, so the python of a macOS virtual environment lost its packages (virtual environments on Windows use file copies, which is why this stayed hidden). Symlinks are now kept.

Issues like these show up only under targeted checks, so this round added the following:

- Harmony: spectral energy of the finished audio was measured chord by chord against the chord chart. For piano, violin, pad and pluck, 83–100% falls on chord tones; the rest are intentional passing and color tones.
- MIDI-DDSP intonation: the pitch of every note was estimated and compared with the MIDI (the estimator is accurate to ±2 cents on synthetic tones). Violin and cello were each rendered 3–4 times and the best-tuned take was kept. The cello model came out about 12 cents sharp in every take; the mix corrects this, leaving an average of -1 cent and a 7 ms onset shift.
- MIDI-DDSP outputs noise at -19 to -35 dBFS during rests and after the last note, so the mix opens each part only where it has notes.
- Loudness: solo demos at -18 LUFS, the ensemble at -16 LUFS, peaks at most -1 dBFS. The tool's BS.1770 measurement agrees with pyloudnorm to within 0.1 LU.

## Automated tests

21 standard-library tests cover: catalog and IDs, monophonic declarations, configuration overwrite protection, relative configuration paths, every example configuration being valid, interpreter symlinks being kept, SSH input and host verification, absolute SSH engine paths, `doctor` looking up command names on PATH (local and SSH), remote failures reporting only their status, setup's platform detection and pinned download checksums, setup protecting an existing backup before downloading, output overwrite protection, local job dispatch, VST3 chunk preservation, recognition of invalid presets, the worker's job-root restriction, the privacy scan reporting only categories, example MIDI matching the generator byte for byte, ensemble track order matching the docs, and audio containing only format and sample data.

## Next

- Rerun the automatic setup end to end on a fresh Windows system.
- Run the CI template on GitHub.
- Have a person listen before release; the listening-related conclusions above come from objective measurements.
- The release is reassembled from an allowlist of sources, with text and media metadata checked; pattern scans and manual review work together.
