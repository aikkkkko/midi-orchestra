# Composing for midi-orchestra

## Shape the piece

- Short-video cues work well at 15–40 seconds: 4–8 bars to establish, 4–8 bars to lift, and a held final chord of 4–6 beats that fades.
- Pick a tempo whose note grid matches the tempo marker; tempo-synced Surge effects follow the first tempo in the file.
- Build contrast by adding parts rather than by playing louder: for example a piano theme first, then strings take the melody while bass and plucks enter underneath.
- Develop one short motif (a rise of a fourth and a third, then stepwise descent, say) instead of writing unrelated phrases; restating it a step higher makes an easy climax.
- Resolve at the end: dominant to tonic, with the seventh falling to the third.

## Parts and ranges

- `piano`: melody between A4 and G5, broken chords from about G2 to F#4; press the sustain pedal (CC64) just after each chord change and release it just before the next.
- `violin`: melody between D5 and D6 sings well; `cello` countermelody between G3 and E4. One note at a time per track, with each note ending exactly where the next begins for legato.
- `surge_pad`: four-note voicings between B3 and A4; tie common tones across chords instead of re-striking them.
- `surge_bass`: G2 to G3 keeps it audible on small speakers; syncopate (root on 1, again on the "and" of 2, a fifth or octave on 3, an approach note on the "and" of 4).
- `surge_pluck`: sixteenth-note arpeggios of four chord tones between E4 and D5, accents in a 3+3+2 pattern.
- `surge_texture`: each note becomes a burbling harmonic series that starts about 0.3 s late; hold roots or fifths for several beats at a low level.

## MIDI hygiene

- Format 1: a conductor track with tempo and time signature, then one named track per part, each on its own channel. `--track N` counts note tracks from 0 in file order.
- When the same pitch repeats, end the first note where the second begins; a later note-off would cut the new note short.
- Sort events so that note-offs come before note-ons at the same tick.

## Rendering and mixing

- MIDI-DDSP takes differ on every render: render important string parts two to four times and keep the best-tuned take. Its cello model has measured about 12 cents sharp.
- MIDI-DDSP outputs low noise during rests and after the last note; gate each string part to the span where it plays, with a short release.
- Balance parts by loudness (BS.1770) rather than by peak. A working starting point: lead 0 LU, piano -1.5, countermelody -5, bass -6, pad -9.5, pluck -11, texture -15; master to about -16 LUFS with peaks under -1 dBFS.
- `scripts/mix_examples.py` shows a complete mix: resampling, high-pass filters, panning, a shared room reverb, gating, pitch correction, limiting and a final fade.
