#!/usr/bin/env python3
"""Generate the original example MIDI using only the Python standard library.

All examples share one key (D major), tempo (88 BPM, 4/4) and harmony, so every
note sits on the beat grid and tempo-synced effects follow the music. Solo
phrases: Gmaj9 | A6 | F#m7 Bm7 | Em9 A7sus4 A7 | Dmaj9. The ensemble is eight
bars: piano theme over Gmaj9 | A6 | F#m7 | Bm7, then violin restates the motif
over Em9 | F#7 | Gmaj7 A7sus4 A7 | Dmaj9, whose final chord rings for six beats.
"""
import argparse
from pathlib import Path
import struct

BPM = 88
PPQ = 480
NAMES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def pitch(name):
    """'F#5' -> 78 (C4 = 60)."""
    semitone = NAMES[name[0]] + name.count('#') - name.count('b')
    return 12 * (int(name.lstrip('ABCDEFG#b')) + 1) + semitone


def vlq(number):
    output = [number & 127]
    while number := number >> 7:
        output.insert(0, (number & 127) | 128)
    return bytes(output)


def chunk(events):
    data = bytearray()
    previous = 0
    # At equal times: meta and controllers, then note-offs, then note-ons.
    for tick, _, message in sorted(events, key=lambda event: (event[0], event[1])):
        data += vlq(tick - previous) + message
        previous = tick
    data += b'\0\xff\x2f\0'
    return b'MTrk' + struct.pack('>I', len(data)) + bytes(data)


def trim_repeats(notes):
    """End a note where the same pitch starts again; a late note-off would cut the new note."""
    notes = sorted(notes, key=lambda note: (pitch(note[0]), note[1]))
    for i, (name, start, length, velocity) in enumerate(notes[:-1]):
        following = notes[i + 1]
        if pitch(following[0]) == pitch(name) and start + length > following[1]:
            notes[i] = (name, start, following[1] - start, velocity)
    return notes


def write_midi(path, parts):
    """parts: [(track name, channel, GM program, notes, pedal)]; beats as floats.

    Format 1: a conductor track with tempo and time signature, then one track per
    part. Track names describe parts only; no user metadata is written.
    """
    tick = lambda beat: round(beat * PPQ)
    conductor = [(0, 0, b'\xff\x51\x03' + round(60e6 / BPM).to_bytes(3, 'big')),
                 (0, 0, b'\xff\x58\x04\x04\x02\x18\x08')]
    tracks = [chunk(conductor)]
    for name, channel, program, notes, pedal in parts:
        notes = trim_repeats(notes)
        events = [(0, 0, b'\xff\x03' + vlq(len(name)) + name.encode('ascii')),
                  (0, 0, bytes([0xC0 | channel, program]))]
        for beat, value in pedal:
            events.append((tick(beat), 0, bytes([0xB0 | channel, 64, value])))
        for note, start, length, velocity in notes:
            events.append((tick(start), 2, bytes([0x90 | channel, pitch(note), velocity])))
            events.append((tick(start + length), 1, bytes([0x80 | channel, pitch(note), 0])))
        tracks.append(chunk(events))
    header = b'MThd' + struct.pack('>IHHH', 6, 1, len(tracks), PPQ)
    path.write_bytes(header + b''.join(tracks))


def line(spec, start=0.0, velocity=80, legato=1.0):
    """'A4:.5 D5:.5 F#5:1.5' -> notes placed one after another; 'r' is a rest."""
    notes, beat = [], start
    for token in spec.split():
        name, length = token.split(':')
        length = float(length)
        if name != 'r':
            notes.append((name, beat, length * legato, velocity))
        beat += length
    return notes


def shape(notes, velocities):
    return [(n, s, d, v) for (n, s, d, _), v in zip(notes, velocities, strict=True)]


def voicings(spec, velocities, overlap=0.0):
    """[(start, length, 'B3 D4 F#4')] -> sustained chords; common tones are tied, others overlap slightly."""
    notes, held = [], {}
    for index, ((start, length, names), velocity) in enumerate(zip(spec, velocities, strict=True)):
        names = names.split()
        for name in list(held):
            if name not in names:
                begin, level = held.pop(name)
                notes.append((name, begin, start - begin + overlap, level))
        for name in names:
            held.setdefault(name, (start, velocity))
        if index == len(spec) - 1 or spec[index + 1][0] != start + length:
            notes += [(name, begin, start + length - begin, level) for name, (begin, level) in held.items()]
            held = {}
    return notes


def arpeggio(spec, step, pattern, accents, length):
    """Repeat a pattern of chord-tone indices over each (start, beats, tones) span."""
    notes = []
    for start, beats, tones in spec:
        tones = tones.split()
        for i in range(round(beats / step)):
            notes.append((tones[pattern[i % len(pattern)]], start + i * step, length, accents[i % len(accents)]))
    return notes


def pedal(changes, end):
    """Release just before each harmony change and press again just after it."""
    events = []
    for beat in changes:
        if beat:
            events.append((beat - 0.04, 0))
        events.append((beat + 0.06, 127))
    return events + [(end, 0)]


# Solo examples: five bars that resolve to the tonic.
SOLO_HARMONY = [(0, 4, 'Gmaj9'), (4, 4, 'A6'), (8, 2, 'F#m7'), (10, 2, 'Bm7'),
                (12, 2, 'Em9'), (14, 1, 'A7sus4'), (15, 1, 'A7'), (16, 4, 'Dmaj9')]


def solo_pad():
    spec = [(0, 4, 'G3 B3 D4 F#4 A4'), (4, 4, 'A3 C#4 E4 F#4 A4'), (8, 2, 'F#3 C#4 E4 F#4 A4'),
                (10, 2, 'B2 B3 D4 F#4 A4'), (12, 2, 'E3 B3 D4 F#4 G4'), (14, 1, 'A2 A3 D4 E4 G4'),
                (15, 1, 'A2 A3 C#4 E4 G4'), (16, 3.5, 'D3 A3 C#4 E4 F#4 A4')]
    return voicings(spec, (62, 70, 74, 76, 80, 78, 76, 70), overlap=0.1)


def solo_bass():
    bars = [
        'G2:1 r:.5 G2:.5 G3:.5 D3:1 B2:.5',
        'A2:1 r:.5 A2:.5 A3:.5 E3:1 G#2:.5',
        'F#2:.75 r:.25 C#3:.5 F#2:.5 B2:.75 r:.25 D3:.5 F#2:.5',
        'E2:.75 r:.25 B2:.5 E3:.5 A2:.75 r:.25 A2:.5 C#2:.5',
        'D2:3.5',
    ]
    notes = []
    for bar, spec in enumerate(bars):
        notes += line(spec, start=bar * 4, legato=0.9)
    return [(n, s, d, 104 if s % 4 == 0 else 92 if s % 1 == 0 else 82) for n, s, d, _ in notes]


def solo_pluck():
    spans = [(0, 4, 'G4 B4 D5 F#5 A5'), (4, 4, 'A4 C#5 E5 F#5 A5'), (8, 2, 'F#4 A4 C#5 E5 F#5'),
             (10, 2, 'F#4 A4 B4 D5 F#5'), (12, 2, 'E4 G4 B4 D5 F#5'), (14, 1, 'E4 A4 D5 E5 G5'),
             (15, 1, 'E4 G4 A4 C#5 E5')]
    # Rolling sixteenths with a 3+3+2 accent shape; chord roots underneath like a harp.
    notes = arpeggio(spans, 0.25, [0, 1, 2, 3, 4, 3, 2, 1], [92, 60, 66, 86, 62, 70, 84, 64], 0.3)
    notes += [(root, start, min(length, 2), 84) for start, length, root in
              [(0, 4, 'G3'), (4, 4, 'A3'), (8, 2, 'F#3'), (10, 2, 'B2'), (12, 2, 'E3'), (14, 2, 'A2')]]
    notes += line('D3:.25 F#3:.25 A3:.25 C#4:.25 E4:.25 F#4:.25 A4:.25 D5:2.25', start=16, velocity=84)
    return notes


def solo_texture():
    # Each note becomes a burbling harmonic series, so the layer moves in roots and fifths.
    return voicings([(0, 4, 'G3 D4'), (4, 4, 'A3 E4'), (8, 2, 'F#3 C#4'), (10, 2, 'B2 F#3'),
                     (12, 2, 'E3 B3'), (14, 2, 'A2 E3'), (16, 4, 'D3 A3 D4')], [76] * 7, overlap=0.25)


def solo_piano():
    melody = (line('A4:.5 D5:.5 F#5:1.5 E5:.5 D5:1', 0) + line('C#5:1.5 D5:.5 E5:2', 4)
              + line('F#5:1 E5:.5 C#5:.5 D5:1 B4:1', 8) + line('G5:1.5 F#5:.5 E5:1 C#5:1', 12)
              + [('D5', 16, 4, 72), ('A5', 16.75, 3.25, 54)])
    melody = shape(melody, [70, 76, 86, 74, 72, 78, 70, 84, 88, 80, 74, 76, 72, 86, 80, 76, 74, 72, 54])
    left = []
    for start, beats, tones in [(0, 4, 'G2 D3 A3 B3 D4 B3 A3 D3'), (4, 4, 'A2 E3 B3 C#4 E4 C#4 B3 E3'),
                                (8, 2, 'F#2 C#3 A3 C#4'), (10, 2, 'B2 F#3 A3 D4'),
                                (12, 2, 'E2 B2 F#3 G3'), (14, 1, 'A2 E3'), (15, 1, 'G3 C#4')]:
        for i, name in enumerate(tones.split()):
            left.append((name, start + i * 0.5, 0.5, 58 if i == 0 else 48 + (i % 3) * 3))
    # Final chord rolled from the bass upward.
    left += [(name, 16 + i * 0.07, 4 - i * 0.07, 66 - i * 3) for i, name in enumerate('D2 A2 F#3 C#4 E4'.split())]
    # The pedal stays down through the mixer's fade so the chord decays naturally.
    return melody + left, pedal([0, 4, 8, 10, 12, 14, 15, 16], 23)


def solo_violin():
    # Gmaj9 arpeggio, answer over A6, peak on C#6, then 7-to-3 and leading-tone resolutions.
    notes = (line('D5:2 F#5:1 A5:1', 0) + line('E5:1.5 F#5:.5 E5:1 C#5:1', 4)
             + line('A5:1 C#6:1 B5:1.5 A5:.5', 8) + line('G5:1 F#5:1 E5:1 C#5:1', 12) + line('D5:3.5', 16))
    return shape(notes, [76, 80, 86, 82, 80, 76, 72, 86, 92, 84, 78, 80, 76, 72, 74, 70])


# Ensemble: eight bars, all parts on one grid; render each track with --track.
def ensemble():
    piano_a = (line('A4:.5 D5:.5 F#5:1.5 E5:.5 D5:1', 0) + line('C#5:1.5 D5:.5 E5:2', 4)
               + line('F#5:1 E5:.5 C#5:.5 A4:2', 8) + line('B4:1.5 C#5:.5 D5:1 E5:1', 12))
    piano = shape(piano_a, [68, 74, 84, 74, 72, 76, 70, 84, 86, 76, 72, 70, 70, 72, 76, 80])
    for start, tones in [(0, 'G2 D3 A3 B3 D4 B3 A3 D3'), (4, 'A2 E3 B3 C#4 E4 C#4 B3 E3'),
                         (8, 'F#2 C#3 G#3 A3 C#4 A3 G#3 C#3'), (12, 'B2 F#3 C#4 D4 F#4 D4 C#4 F#3')]:
        piano += [(n, start + i * 0.5, 0.5, 56 if i == 0 else 46 + (i % 3) * 3) for i, n in enumerate(tones.split())]
    # Second half: the piano steps back to octave roots and soft chords under the strings.
    for start, length, names, velocity in [(16, 4, 'E2 E3', 54), (20, 4, 'F#2 F#3', 56), (24, 2, 'G2 G3', 56),
                                           (26, 2, 'A2 A3', 58), (16, 2, 'G3 B3 D4 F#4', 50), (18, 2, 'G3 B3 D4 F#4', 44),
                                           (20, 2, 'A#3 C#4 E4', 52), (22, 2, 'A#3 C#4 E4', 46), (24, 2, 'B3 D4 F#4', 52),
                                           (26, 1, 'D4 E4 G4', 50), (27, 1, 'C#4 E4 G4', 52)]:
        piano += [(n, start, length, velocity) for n in names.split()]
    # Final chord: rolled, held under the strings, with a high A-C#-E arpeggio on top.
    piano += [(n, 28 + i * 0.06, 6 - i * 0.06, 62 - i * 2) for i, n in enumerate('D2 A2 F#3 C#4 E4 A4'.split())]
    piano += [('A5', 30, 4, 46), ('C#6', 30.5, 3.5, 42), ('E6', 31, 3, 40)]
    piano_pedal = pedal([0, 4, 8, 12, 16, 20, 24, 26, 27, 28], 36)

    # Violin restates the opening motif (up a fourth, up a third, down by step) in sequence.
    violin = (line('B4:.5 E5:.5 G5:1.5 F#5:.5 E5:1', 16) + line('C#5:.5 F#5:.5 A#5:1.5 G#5:.5 F#5:1', 20)
              + line('D6:1.5 C#6:.5 B5:1 A5:.5 G5:.5', 24) + line('F#5:5.75', 28))
    violin = shape(violin, [74, 80, 88, 80, 78, 78, 84, 92, 84, 80, 96, 88, 84, 80, 78, 82])
    cello = line('G3:2 B3:2 C#4:2 E4:2 D4:3 C#4:1 D4:5.75', 16, velocity=74)

    # Quiet in the first half, fuller under the strings; the section change re-strikes the chord.
    pad = voicings([(0, 4, 'B3 D4 F#4 A4'), (4, 4, 'C#4 E4 F#4 A4'), (8, 4, 'C#4 E4 F#4 A4'),
                    (12, 4, 'B3 D4 F#4 A4')], [56, 58, 60, 60], overlap=0.1)
    pad += voicings([(16, 4, 'B3 D4 F#4 G4'), (20, 4, 'A#3 C#4 E4 F#4'), (24, 2, 'B3 D4 F#4 G4'),
                     (26, 1, 'A3 D4 E4 G4'), (27, 1, 'A3 C#4 E4 G4'), (28, 5.5, 'D3 A3 C#4 E4 F#4')],
                    [70, 74, 76, 74, 72, 66], overlap=0.1)

    bass = []
    for bar, spec in enumerate(['E2:1 r:.5 E2:.5 E3:.5 B2:1 G2:.5', 'F#2:1 r:.5 F#2:.5 F#3:.5 C#3:1 A#2:.5',
                                'G2:1 r:.5 G2:.5 A2:1 A2:.5 C#2:.5', 'D2:6']):
        bass += line(spec, start=16 + bar * 4, velocity=96, legato=0.9)

    pluck = arpeggio([(8, 4, 'F#4 A4 C#5 E5'), (12, 4, 'F#4 A4 B4 D5')], 0.5,
                     [0, 1, 2, 3, 2, 1, 2, 3], [70, 52, 58, 64, 54, 60, 66, 56], 0.45)
    pluck += arpeggio([(16, 4, 'E4 G4 B4 D5'), (20, 4, 'F#4 A#4 C#5 E5'), (24, 2, 'G4 B4 D5 F#5'),
                       (26, 1, 'E4 A4 D5 E5'), (27, 1, 'E4 G4 A4 C#5')], 0.25,
                      [0, 1, 2, 3, 3, 2, 1, 0], [84, 56, 62, 72, 64, 58, 54, 60], 0.3)
    pluck += line('D4:.25 F#4:.25 A4:.25 C#5:.25 E5:.25 F#5:.25 A5:2.5', 28, velocity=76)

    texture = [('A3', 0, 15.5, 70), ('D4', 27.5, 6.5, 66), ('A4', 27.5, 6.5, 66)]

    return [('piano', 0, 0, piano, piano_pedal), ('violin', 1, 40, violin, []), ('cello', 2, 42, cello, []),
            ('surge_pad', 3, 89, pad, []), ('surge_bass', 4, 38, bass, []), ('surge_pluck', 5, 46, pluck, []),
            ('surge_texture', 6, 95, texture, [])]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', default=str(Path(__file__).resolve().parents[1] / 'examples/midi'))
    root = Path(parser.parse_args().out)
    root.mkdir(parents=True, exist_ok=True)
    piano, piano_pedal = solo_piano()
    for name, channel, program, notes, sustain in [
            ('surge_pad', 0, 89, solo_pad(), []), ('surge_bass', 0, 38, solo_bass(), []),
            ('surge_pluck', 0, 46, solo_pluck(), []), ('surge_texture', 0, 95, solo_texture(), []),
            ('piano', 0, 0, piano, piano_pedal), ('violin', 0, 40, solo_violin(), [])]:
        write_midi(root / (name + '.mid'), [(name, channel, program, notes, sustain)])
    write_midi(root / 'ensemble.mid', ensemble())


if __name__ == '__main__':
    main()
