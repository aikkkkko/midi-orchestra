#!/usr/bin/env python3
"""Mix rendered example stems into the WAV files in examples/audio.

Render every stem first (commands in examples/CREDITS.md), each with --out STEMS/<name>,
then run:  python scripts/mix_examples.py STEMS
Requires numpy. Levels use ITU-R BS.1770 K-weighted loudness rather than peaks, the
reverb is a fixed synthetic room, and output WAVs contain only fmt and PCM data chunks.
"""
import argparse
from pathlib import Path
import wave

import numpy as np

RATE = 48000
BEAT = 60 / 88
# Output name -> (length in beats, integrated LUFS, {stem: settings}). Stem settings:
# level (LU relative to the lead), pan (-1..1), highpass (Hz), reverb (send), gate (beats
# where the stem is open) and cents (pitch correction).
# MIDI-DDSP synthesizes noise during rests and after the last note, so string stems are
# gated to their notes; its cello model measured about 12 cents sharp in every take.
EXAMPLES = {
    'surge_pad': (23, -18, {'surge_pad': dict(highpass=40)}),
    'surge_bass': (21.5, -18, {'surge_bass': dict(highpass=25)}),
    'surge_pluck': (23.5, -18, {'surge_pluck': dict(highpass=60, reverb=0.08)}),
    'surge_texture': (23, -18, {'surge_texture': dict(highpass=60, reverb=0.15)}),
    'piano': (23, -18, {'piano': dict(highpass=30, reverb=0.12)}),
    'violin': (22, -18, {'violin': dict(highpass=150, reverb=0.3, gate=(0, 20))}),
    'ensemble': (37, -16, {
        'ensemble_violin': dict(pan=-0.18, highpass=170, reverb=0.32, gate=(15.9, 34.25)),
        'ensemble_piano': dict(level=-1.5, highpass=45, reverb=0.14),
        'ensemble_cello': dict(level=-5, pan=0.22, highpass=55, reverb=0.28, gate=(15.9, 34.25), cents=-12),
        'ensemble_surge_bass': dict(level=-6, highpass=30),
        'ensemble_surge_pad': dict(level=-9.5, highpass=140, reverb=0.05),
        'ensemble_surge_pluck': dict(level=-11, pan=0.25, highpass=220, reverb=0.12),
        'ensemble_surge_texture': dict(level=-15, pan=-0.2, highpass=220, reverb=0.2),
    }),
}


def read_wav(path):
    with wave.open(str(path)) as source:
        width, channels, rate = source.getsampwidth(), source.getnchannels(), source.getframerate()
        raw = np.frombuffer(source.readframes(source.getnframes()), np.uint8)
    if width != 3:
        raise ValueError(str(path) + ': expected 24-bit PCM from the renderer')
    samples = raw.reshape(-1, 3).astype(np.int32)
    values = samples[:, 0] | (samples[:, 1] << 8) | (samples[:, 2] << 16)
    values = np.where(values & 0x800000, values - 0x1000000, values)
    audio = (values / 8388608.0).reshape(-1, channels)
    if rate != RATE:
        audio = fit(audio, round(len(audio) * RATE / rate))
    return audio if channels == 2 else np.repeat(audio, 2, axis=1)


def write_wav(path, audio):
    values = np.round(np.clip(audio, -1, 1 - 2 ** -23) * 8388608).astype(np.int32)
    raw = values.reshape(-1, 1).view(np.uint8).reshape(-1, 4)[:, :3]
    with wave.open(str(path), 'wb') as target:
        target.setnchannels(2)
        target.setsampwidth(3)
        target.setframerate(RATE)
        target.writeframes(raw.tobytes())


def fit(audio, length, pad=8192):
    """Band-limited FFT resampling to a sample count; padding keeps the transform from wrapping."""
    padded = np.pad(audio, ((pad, pad), (0, 0)))
    total = round(len(padded) * length / len(audio))
    output = np.fft.irfft(np.fft.rfft(padded, axis=0), n=total, axis=0) * (total / len(padded))
    start = round(pad * length / len(audio))
    return output[start:start + length]


def retune(audio, cents, size=2048, hop=256):
    """Shift pitch without moving notes: phase-vocoder time stretch, then resample to the original length."""
    speed = 2 ** (-cents / 1200)
    window = np.hanning(size)
    advance = 2 * np.pi * hop * np.arange(size // 2 + 1) / size
    channels = []
    for signal in audio.T:
        signal = np.pad(signal, (size, size + hop))
        frames = np.array([np.fft.rfft(window * signal[i:i + size]) for i in range(0, len(signal) - size, hop)])
        positions = np.arange(0, len(frames) - 1, speed)
        output, weight = np.zeros(len(positions) * hop + size), np.zeros(len(positions) * hop + size)
        phase = np.angle(frames[0])
        for k, position in enumerate(positions):
            i, fraction = int(position), position - int(position)
            magnitude = (1 - fraction) * np.abs(frames[i]) + fraction * np.abs(frames[i + 1])
            output[k * hop:k * hop + size] += window * np.fft.irfft(magnitude * np.exp(1j * phase), size)
            weight[k * hop:k * hop + size] += window ** 2
            delta = np.angle(frames[i + 1]) - np.angle(frames[i]) - advance
            phase += advance + (delta + np.pi) % (2 * np.pi) - np.pi
        output /= np.maximum(weight, 1e-2)
        start = round(size / speed)
        channels.append(output[start:start + round((len(signal) - 2 * size - hop) / speed)])
    return fit(np.stack(channels, axis=1), len(audio))


def spectral(audio, response):
    """Apply a zero-phase magnitude response given as a function of frequency in Hz."""
    spectrum = np.fft.rfft(audio, axis=0)
    spectrum *= response(np.fft.rfftfreq(len(audio), 1 / RATE))[:, None]
    return np.fft.irfft(spectrum, n=len(audio), axis=0)


def high_pass(audio, cutoff):
    return spectral(audio, lambda f: 1 / np.sqrt(1 + (cutoff / np.maximum(f, 1e-3)) ** 4))


def biquad(b, a, f):
    z = np.exp(-2j * np.pi * f / RATE)
    return np.abs((b[0] + b[1] * z + b[2] * z * z) / (1 + a[0] * z + a[1] * z * z))


def loudness(audio):
    """BS.1770 integrated loudness (K-weighting, 400 ms blocks, absolute and relative gates)."""
    weighted = spectral(audio, lambda f: biquad((1.53512485958697, -2.69169618940638, 1.19839281085285),
                                                (-1.69065929318241, 0.73248077421585), f)
                        * biquad((1, -2, 1), (-1.99004745483398, 0.99007225036621), f))
    block, hop = int(0.4 * RATE), int(0.1 * RATE)
    power = np.array([np.sum(np.mean(weighted[i:i + block] ** 2, axis=0))
                      for i in range(0, len(weighted) - block + 1, hop)])
    power = power[power > 10 ** ((-70 + 0.691) / 10)]
    if not len(power):
        return -70.0
    power = power[power > np.mean(power) * 10 ** (-10 / 10)]
    return -0.691 + 10 * np.log10(np.mean(power))


def room(seconds=2.6, seed=7):
    """Stereo synthetic room: sparse early reflections and a band-dependent exponential tail."""
    rng = np.random.default_rng(seed)
    length = int(seconds * RATE)
    time = np.arange(length) / RATE
    impulse = np.zeros((length, 2))
    for channel in range(2):
        noise = rng.standard_normal(length)
        tail = np.zeros(length)
        # Lower bands ring longer than upper bands, like an absorptive hall.
        for low, high, rt60 in ((0, 500, 2.1), (500, 3000, 1.7), (3000, RATE / 2, 0.8)):
            band = spectral(noise[:, None], lambda f: ((f >= low) & (f < high)).astype(float))[:, 0]
            tail += band * 10 ** (-3 * time / rt60)
        tail *= np.clip((time - 0.022) / 0.03, 0, 1)
        for delay, gain in rng.uniform([0.007, 0.25], [0.03, 0.6], (6, 2)):
            impulse[int(delay * RATE), channel] += gain * rng.choice([-1, 1])
        impulse[:, channel] += tail * 0.5
    return impulse / np.sqrt(np.sum(impulse ** 2) / 2)


def convolve(audio, impulse):
    length = len(audio) + len(impulse) - 1
    size = 1 << (length - 1).bit_length()
    result = np.fft.irfft(np.fft.rfft(audio, size, axis=0) * np.fft.rfft(impulse, size, axis=0), size, axis=0)
    return result[:len(audio)]


def pan(audio, position):
    angle = (position + 1) * np.pi / 4
    return audio * (np.array([np.cos(angle), np.sin(angle)]) * np.sqrt(2))


def limit(audio, ceiling=10 ** (-1 / 20), release=0.08):
    """Look-ahead peak limiter on 1 ms blocks; gain recovers exponentially."""
    step = RATE // 1000
    blocks = -(-len(audio) // step)
    peak = np.pad(np.abs(audio).max(axis=1), (0, blocks * step - len(audio))).reshape(blocks, step).max(axis=1)
    need = np.minimum(1, ceiling / np.maximum(peak, 1e-9))
    padded = np.pad(need, (1, 5), constant_values=1)
    need = np.min([padded[k:k + blocks] for k in range(7)], axis=0)
    gain, current, recover = np.empty(blocks), 1.0, 1 - np.exp(-1 / (release * 1000))
    for i, value in enumerate(need):
        current = value if value < current else current + (value - current) * recover
        gain[i] = current
    gain = np.interp(np.arange(len(audio)) / step, np.arange(blocks), gain)
    return np.clip(audio * gain[:, None], -ceiling, ceiling)


def gate(audio, start, end, attack=0.05, release=0.3):
    time = np.arange(len(audio)) / RATE
    return audio * np.clip(np.minimum((time - start) / attack, (end - time) / release), 0, 1)[:, None]


def finish(audio, target, length, fade=2.0):
    """Set loudness, keep peaks under -1 dBFS, cut to length and fade out over the release tail."""
    audio = np.pad(audio, ((0, max(0, length - len(audio))), (0, 0)))[:length]
    audio = limit(audio * 10 ** ((target - loudness(audio)) / 20))
    fade = int(fade * RATE)
    audio[-fade:] *= (np.cos(np.linspace(0, np.pi / 2, fade)) ** 2)[:, None]
    return audio


def mix(stems, beats, target, spec, impulse):
    length = round(beats * BEAT * RATE)
    dry, send = np.zeros((length, 2)), np.zeros((length, 2))
    for name, settings in spec.items():
        settings = dict(dict(level=0, pan=0, highpass=20, reverb=0, gate=None, cents=0), **settings)
        audio = read_wav(stems / name / 'mix.wav')
        if settings['cents']:
            audio = retune(audio, settings['cents'])
        audio = high_pass(audio, settings['highpass'])[:length]
        if settings['gate']:
            audio = gate(audio, settings['gate'][0] * BEAT, settings['gate'][1] * BEAT)
        audio = pan(audio * 10 ** ((-23 + settings['level'] - loudness(audio)) / 20), settings['pan'])
        dry[:len(audio)] += audio
        send[:len(audio)] += audio * settings['reverb']
    return finish(dry + convolve(send, impulse), target, length, 2.4 if beats > 30 else 1.6)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('stems', help='Directory with <stem>/mix.wav render outputs')
    parser.add_argument('--out', default=str(Path(__file__).resolve().parents[1] / 'examples/audio'))
    args = parser.parse_args()
    stems, out = Path(args.stems), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    impulse = room()
    for name, (beats, target, spec) in EXAMPLES.items():
        audio = mix(stems, beats, target, spec, impulse)
        write_wav(out / (name + '.wav'), audio)
        print(f'{name}.wav {len(audio) / RATE:.1f}s')


if __name__ == '__main__':
    main()
