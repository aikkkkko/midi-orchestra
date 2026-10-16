"""Isolated worker for local execution or a Windows SSH render host."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import argparse
import shutil

def main():
    parser = argparse.ArgumentParser(description='Isolated MIDI render worker')
    parser.add_argument('directory')
    parser.add_argument('--jobs-root', required=True)
    args = parser.parse_args()
    directory = Path(args.directory).resolve()
    jobs = Path(args.jobs_root).resolve()
    if jobs not in directory.parents:
        raise ValueError('任务目录不属于登记的 jobs 根目录')
    request = json.loads((directory / 'job.json').read_text(encoding='utf-8'))
    if request['schema_version'] != 1:
        raise ValueError('任务格式版本不支持')
    out = directory / 'result'
    out.mkdir(exist_ok=False)
    if request['engine'] == 'dawdreamer_surge':
        # Use the system runtime, avoiding Conda's older bundled MSVC DLL.
        import ctypes
        if os.name == 'nt' and request.get('msvc_runtime'):
            ctypes.WinDLL(request['msvc_runtime'])
    import numpy as np
    import pretty_midi
    import soundfile as sf
    midi = pretty_midi.PrettyMIDI(str(directory / 'input.mid'))
    if request.get('track') is not None:
        index = request['track']
        if index < 0 or index >= len(midi.instruments):
            raise ValueError('轨道编号超出范围')
        midi.instruments = [midi.instruments[index]]
    midi.instruments = [item for item in midi.instruments if item.notes]
    if not midi.instruments:
        raise ValueError('MIDI 没有可渲染音符')
    program = request['program']
    if not isinstance(program, int) or not 0 <= program <= 127:
        raise ValueError('MIDI program 需要是 0–127 的整数')
    for index, item in enumerate(midi.instruments):
        if item.is_drum:
            raise ValueError('当前音色不支持鼓轨，请用 --track 选择旋律轨')
        item.program = program
        item.notes.sort(key=lambda note:(note.start,note.end))
        if request['engine'] == 'midi_ddsp':
            previous_end = -1.0
            for note in sorted(item.notes, key=lambda x:(x.start,x.end)):
                if note.start < previous_end - 0.0001:
                    raise ValueError('MIDI-DDSP 要求每轨单声部；第 %d 轨存在音符重叠，请先拆分声部' % index)
                previous_end = max(previous_end,note.end)
        elif request['engine'] == 'fluidsynth_sf2' and not request.get('dry'):
            # CC91 sets the channel's send level into the global reverb effect.
            item.control_changes.append(pretty_midi.ControlChange(number=91,value=35,time=0))
    prepared = out / 'prepared.mid'
    midi.write(str(prepared))
    start = time.perf_counter()
    if request['engine'] == 'midi_ddsp':
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
        os.environ['CUDA_VISIBLE_DEVICES'] = '-1' if request.get('cpu') else '0'
        environment = Path(request.get('environment_root', Path(sys.executable).parent))
        if os.name == 'nt':
            os.environ['PATH'] = os.pathsep.join(str(p) for p in (environment/'Library/bin', environment/'Scripts', environment)) + os.pathsep + os.environ.get('PATH', '')
        import tensorflow as tf
        gpus = tf.config.list_physical_devices('GPU')
        if not request.get('cpu') and not gpus:
            raise RuntimeError('GPU 不可用；请先检查环境，或明确使用 --cpu')
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu,True)
        from midi_ddsp import load_pretrained_model,synthesize_midi
        sg,eg = load_pretrained_model()
        result = synthesize_midi(sg,eg,str(prepared),output_dir=str(out/'stems'),display_progressbar=False)
        if result is None:
            raise RuntimeError('MIDI-DDSP 未返回音频')
        sf.write(str(out/'mix.wav'),result['mix_audio'],16000,subtype='PCM_24')
        credit = 'Engine: MIDI-DDSP 0.2.6 / DDSP 3.2.0, official URMP pretrained model.\nSource: https://github.com/magenta/midi-ddsp\n'
    elif request['engine'] == 'fluidsynth_sf2':
        configured = request['executable']
        engine = Path(shutil.which(configured) or configured)
        font = Path(request['soundfont_path'])
        if not engine.is_file() or not font.is_file():
            raise FileNotFoundError('FluidSynth 或 SF2 路径不存在')
        args = [str(engine),'-ni','-r',str(request['sample_rate']),'-g','0.45','-F',str(out/'mix.wav'),'-T','wav','-O','float','-o','synth.chorus.active=0','-o','synth.reverb.active='+str(int(not request.get('dry',False)))]
        if not request.get('dry'):
            args += ['-o','synth.reverb.room-size=0.55','-o','synth.reverb.damp=0.4','-o','synth.reverb.level=0.22','-o','synth.reverb.width=0.8']
        subprocess.run(args+[str(font),str(prepared)],check=True)
        credit = 'SoundFont: '+request['soundfont_name']+'\nCredit: '+request['soundfont_credit']+'\nLicense: '+request['soundfont_license']+'\nSource: '+request['soundfont_source']+'\nChanges: MIDI performance, sustain, optional light reverb and optional whole-track gain normalization.\n'
    elif request['engine'] == 'dawdreamer_surge':
        import dawdreamer as daw
        import hashlib
        import mido
        plugin = Path(request['plugin_path'])
        preset = Path(request['preset_path'])
        if not plugin.exists() or not preset.is_file():
            raise FileNotFoundError('Surge 插件或固定预设不存在')
        if hashlib.sha256(preset.read_bytes()).hexdigest() != request['preset_sha256']:
            raise ValueError('固定预设哈希不匹配；请核对版本')
        # Program changes can select a different patch; fixed presets ignore them.
        events = mido.MidiFile(str(prepared))
        for track in events.tracks:
            pending = 0
            kept = []
            for message in track:
                if message.type == 'program_change':
                    pending += message.time
                else:
                    kept.append(message.copy(time=message.time + pending))
                    pending = 0
            track[:] = kept
        events.save(str(prepared))
        rate = request['sample_rate']
        engine = daw.RenderEngine(rate, 512)
        synth = engine.make_plugin_processor('surge', str(plugin))
        engine.load_graph([(synth, [])])
        # load_state creates a GUI window; VST3 presets load without a GUI.
        if not synth.load_vst3_preset(str(preset)):
            raise RuntimeError('Surge VST3 预设载入失败')
        # Surge applies a loaded patch on its next audio block; without this warm-up
        # block the patch change silences notes that start at time zero.
        engine.render(0.1)
        tempos = midi.get_tempo_changes()[1]
        engine.set_bpm(float(tempos[0]) if len(tempos) else 120.0)
        synth.load_midi(str(prepared), clear_previous=True, beats=False, all_events=True)
        duration = midi.get_end_time() + float(request['tail_seconds'])
        engine.render(duration)
        audio = engine.get_audio().T
        sf.write(str(out/'mix.wav'), audio, rate, subtype='FLOAT')
        credit = ('Engine: DawDreamer 0.9.0 + Surge XT 1.3.4 (VST3), CPU offline rendering.\n'
                  'Source: https://github.com/DBraun/DawDreamer ; https://github.com/surge-synthesizer/releases-xt/releases/tag/1.3.4\n'
                  'Preset: ' + request['preset_source'] + '\n'
                  'Preset SHA256: ' + request['preset_sha256'] + '\n'
                  'Changes: factory FXP chunk repackaged as VST3 preset; MIDI performance; optional normalization.\n')
    else:
        raise ValueError('没有实现此引擎；请先添加后端适配器')
    render_seconds = time.perf_counter()-start
    audio,rate = sf.read(str(out/'mix.wav'),always_2d=True)
    if not np.all(np.isfinite(audio)):
        raise ValueError('音频包含非有限数值')
    if not audio.size:
        raise ValueError('Engine returned empty audio')
    peak = float(np.max(np.abs(audio)))
    if peak < 1e-8:
        raise ValueError('输出是静音，请核对 SF2 preset、program 与 bank')
    if request.get('normalize'):
        audio *= 10**(-1/20)/peak
    elif peak > 1:
        raise ValueError('原始音频超出 PCM 范围；请使用 --normalize 或降低 MIDI 力度')
    sf.write(str(out/'mix.wav'),audio,rate,subtype='PCM_24')
    report = {key: request[key] for key in ('schema_version', 'job_id', 'instrument_id', 'engine', 'program', 'track', 'cpu', 'dry', 'normalize')}
    report.update(render_seconds=render_seconds, sample_rate=rate, audio_seconds=len(audio)/rate, channels=audio.shape[1], peak=float(np.max(np.abs(audio))), input_tracks=len(midi.instruments), timing_scope='engine initialization and synthesis; excludes transfer, MIDI preparation and final PCM write')
    if request.get('preset_sha256'):
        report['preset_sha256'] = request['preset_sha256']
    (out/'render.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'CREDITS.txt').write_text(credit,encoding='utf-8')
    print('MIDI_ORCHESTRA_RENDER_COMPLETE '+json.dumps(report,ensure_ascii=False),flush=True)

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Diagnostics stay in the private runtime; do not publish runtime folders.
        print('Render failed: ' + str(error), file=sys.stderr, flush=True)
        raise SystemExit(1)
