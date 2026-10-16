# Engine selection

- `surge_pad`: sustained midrange chords and soft support.
- `surge_bass`: low-register rhythmic notes.
- `surge_pluck`: short notes and arpeggios.
- `surge_texture`: sparse transition effects. Check the end of the tail.
- `piano`: configured FluidSynth SF2. Polyphony, velocity and sustain depend on the selected library.
- `violin` and related acoustic model IDs: MIDI-DDSP, one note at a time per track, 16 kHz by default. Report the listening checks that were actually done for the chosen instrument.

Surge output defaults to 48 kHz stereo 24-bit with 6 seconds of tail. Each Surge ID keeps its fixed preset through MIDI program changes. Effects sync to the first tempo in the file; later tempo changes move the notes, while tempo-synced effects keep the first tempo. CC and pitch-wheel responses depend on the preset.

`--dry` switches off FluidSynth's added reverb. `--cpu` runs MIDI-DDSP on the CPU; the other engines always render on the CPU. Check a library's default bank and program mapping before registering a new SF2 instrument.
