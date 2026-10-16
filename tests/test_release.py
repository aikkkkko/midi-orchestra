import base64
import importlib.util
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

from midi_orchestra import cli
from midi_orchestra.presets import convert_fxp

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('audit_release',ROOT/'scripts/audit_release.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


class ConfigurationTests(unittest.TestCase):
    def test_catalog_contains_unique_ids_and_correct_voice_constraints(self):
        data=cli.validate(cli.default_config())
        self.assertEqual(len(data['instruments']),18)
        self.assertFalse(cli.select(data,'violin')['polyphonic_track'])
        self.assertTrue(cli.select(data,'surge_pad')['polyphonic_track'])
        self.assertFalse(data['engines']['midi_ddsp']['enabled'])

    def test_init_never_overwrites_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'config.local.json'
            with patch('sys.stdout',new=io.StringIO()):cli.run(['init','--out',str(p)])
            before=p.read_bytes()
            with self.assertRaises(FileExistsError):cli.run(['init','--out',str(p)])
            self.assertEqual(before,p.read_bytes())

    def test_local_paths_are_relative_to_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(cli.local_path('presets/one',Path(directory)),str((Path(directory)/'presets/one').resolve()))

    def test_every_example_configuration_is_valid(self):
        for path in (ROOT/'configs').glob('*.json'):cli.validate(json.loads(path.read_text()))

    def test_interpreter_symlinks_are_kept(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);(d/'base').write_text('');(d/'env/bin').mkdir(parents=True)
            try:(d/'env/bin/python').symlink_to(d/'base')
            except OSError:self.skipTest('symlinks unavailable')
            self.assertEqual(cli.executable('env/bin/python',d),str(d/'env/bin/python'))
            self.assertEqual(cli.executable('fluidsynth',d),'fluidsynth')

    def test_unsafe_ssh_alias_is_rejected(self):
        data=json.loads((ROOT/'configs/ssh-windows.example.json').read_text())
        data['transport']['ssh_alias']='host; echo changed'
        with self.assertRaises(ValueError):cli.validate(data)

    def test_ssh_engine_paths_must_be_absolute(self):
        data=json.loads((ROOT/'configs/ssh-windows.example.json').read_text())
        for engine in data['engines'].values():engine['enabled']=True
        cli.validate(data)
        data['engines']['midi_ddsp']['environment_root']='.runtime/midi-ddsp/env'
        with self.assertRaises(ValueError):cli.validate(data)

    def test_doctor_looks_up_bare_commands_on_path(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);(d/'piano.sf2').write_bytes(b'sf2');data=cli.default_config()
            data['engines']['dawdreamer_surge']['enabled']=False
            data['engines']['fluidsynth_sf2'].update(enabled=True,soundfont_path='piano.sf2')
            with patch.object(cli.shutil,'which',return_value='/bin/found'),patch('sys.stdout',new=io.StringIO()) as out:cli.doctor(data,d)
            self.assertIn('OK fluidsynth_sf2:executable',out.getvalue())
        data=json.loads((ROOT/'configs/ssh-windows.example.json').read_text());data['engines']['fluidsynth_sf2']['enabled']=True
        with patch.object(cli,'remote_ps') as remote:cli.doctor(data,ROOT)
        script=remote.call_args.args[1]
        self.assertIn("Get-Command -Name 'fluidsynth'",script);self.assertIn("Test-Path -LiteralPath 'C:/midi-orchestra/.runtime/soundfonts/piano.sf2'",script)

    def test_failed_remote_command_reports_status_without_command_line(self):
        failure=subprocess.CalledProcessError(1,['ssh','render-host','powershell -EncodedCommand SECRETSCRIPT'])
        with patch.object(cli,'run',side_effect=failure),patch('sys.stderr',new=io.StringIO()) as err:
            with self.assertRaises(SystemExit):cli.main()
        self.assertIn('ssh exited with status 1',err.getvalue());self.assertNotIn('SECRETSCRIPT',err.getvalue())

    def test_ssh_uses_host_verification_and_encoded_script(self):
        t={'ssh_alias':'render-host'}
        with patch.object(cli.subprocess,'run') as run:
            cli.remote_ps(t,"Write-Output 'ready'")
        command=run.call_args.args[0]
        self.assertIn('StrictHostKeyChecking=yes',command)
        encoded=command[-1].rsplit(' ',1)[-1]
        self.assertIn("Write-Output 'ready'",base64.b64decode(encoded).decode('utf-16le'))

    def test_render_refuses_existing_output_before_starting_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);m=d/'input.mid';m.write_bytes(b'MThd')
            out=d/'out';out.mkdir();(out/'keep.txt').write_text('keep')
            args=type('Args',(),dict(instrument='surge_pad',midi=str(m),out=str(out),cpu=False,dry=False,normalize=True,track=None))()
            with patch.object(cli.subprocess,'run') as run:
                with self.assertRaises(ValueError):cli.render(cli.default_config(),d,args)
                run.assert_not_called()
            self.assertEqual((out/'keep.txt').read_text(),'keep')

    def test_local_render_resolves_paths_and_copies_results(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);m=d/'input.mid';m.write_bytes(b'MThd')
            args=type('Args',(),dict(instrument='surge_pad',midi=str(m),out=str(d/'out'),cpu=False,dry=False,normalize=True,track=None))()
            def fake_worker(command,**kwargs):
                job=Path(command[2]);request=json.loads((job/'job.json').read_text())
                self.assertTrue(Path(request['preset_path']).is_absolute())
                self.assertTrue(request['normalize'])
                result=job/'result';result.mkdir()
                for name in ('mix.wav','render.json','prepared.mid','CREDITS.txt'):(result/name).write_bytes(b'result')
            with patch.object(cli.subprocess,'run',side_effect=fake_worker),patch('sys.stdout',new=io.StringIO()):cli.render(cli.default_config(),d,args)
            self.assertEqual((d/'out/mix.wav').read_bytes(),b'result')


class PresetTests(unittest.TestCase):
    def test_container_retains_factory_chunk_and_offsets(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);fxp=d/'one.fxp';dest=d/'one.vstpreset'
            raw=b'sub3'+b'\0'*28+b'<patch/>'
            fxp.write_bytes(b'CcnK'+b'\0'*4+b'FPCh'+b'\0'*48+raw)
            digest=convert_fxp(fxp,dest);data=dest.read_bytes()
            self.assertEqual(data[:4],b'VST3');self.assertEqual(data[48:48+len(raw)],raw)
            offset=struct.unpack('<Q',data[40:48])[0]
            self.assertEqual(data[offset:offset+4],b'List');self.assertEqual(len(digest),64)

    def test_non_surge_data_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'bad.fxp';p.write_bytes(b'not a preset')
            with self.assertRaises(ValueError):convert_fxp(p,p.with_suffix('.vstpreset'))


class SetupTests(unittest.TestCase):
    def test_setup_targets_windows_x64_and_macos(self):
        spec=importlib.util.spec_from_file_location('setup_surge',ROOT/'scripts/setup_surge.py')
        setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
        self.assertEqual(setup.platform_name('Windows','AMD64'),'windows')
        self.assertEqual(setup.platform_name('Darwin','arm64'),'macos');self.assertEqual(setup.platform_name('Darwin','x86_64'),'macos')
        with self.assertRaises(ValueError):setup.platform_name('Linux','x86_64')
        self.assertTrue(all(len(item)==3 and len(item[2])==64 for items in setup.DOWNLOADS.values() for item in items))

    def test_setup_refuses_existing_backup_before_downloading(self):
        spec=importlib.util.spec_from_file_location('setup_surge',ROOT/'scripts/setup_surge.py')
        setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
        with tempfile.TemporaryDirectory() as directory:
            config=Path(directory)/'config.local.json';config.write_text('{}')
            self.assertEqual(setup.refuse_existing_backup(config).name,'config.local.json.bak')
            config.with_suffix('.json.bak').write_text('{}')
            with self.assertRaises(ValueError):setup.refuse_existing_backup(config)


class WorkerAndPrivacyTests(unittest.TestCase):
    def test_worker_rejects_directory_outside_job_root_before_importing_engines(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);wrong=d/'wrong';wrong.mkdir()
            result=subprocess.run([sys.executable,str(cli.worker_file()),str(wrong),'--jobs-root',str(d/'jobs')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn('ModuleNotFoundError',result.stderr)

    def test_audit_reports_categories_without_echoing_sensitive_values(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory)
            value='192.'+'168.'+'50.10'
            (d/'bad.txt').write_text(value)
            report=audit.scan(d)
            self.assertEqual(report['status'],'failed')
            self.assertIn('private_ip',[f['category'] for f in report['findings']])
            self.assertNotIn(value,json.dumps(report))

    def test_example_midi_matches_generator(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run([sys.executable,str(ROOT/'scripts/generate_examples.py'),'--out',directory],check=True)
            generated={p.name:p.read_bytes() for p in Path(directory).glob('*.mid')}
        self.assertEqual(generated,{p.name:p.read_bytes() for p in (ROOT/'examples/midi').glob('*.mid')})

    def test_ensemble_tracks_follow_documented_track_indices(self):
        data=(ROOT/'examples/midi/ensemble.mid').read_bytes();offset=14;names=[]
        while offset<len(data):
            size=int.from_bytes(data[offset+4:offset+8],'big');body=data[offset+8:offset+8+size]
            if body.startswith(b'\0\xff\x03'):names.append(body[4:4+body[3]].decode())
            offset+=8+size
        self.assertEqual(names,['piano','violin','cello','surge_pad','surge_bass','surge_pluck','surge_texture'])

    def test_demo_wavs_contain_only_format_and_pcm_chunks(self):
        for p in (ROOT/'examples/audio').glob('*.wav'):
            b=p.read_bytes();self.assertEqual(b[:4],b'RIFF');offset=12;chunks=[]
            while offset+8<=len(b):
                chunk=b[offset:offset+4];size=int.from_bytes(b[offset+4:offset+8],'little');chunks.append(chunk);offset+=8+size+(size%2)
            self.assertEqual(chunks,[b'fmt ',b'data'])
            with wave.open(str(p)) as w:self.assertEqual((w.getframerate(),w.getnchannels(),w.getsampwidth()),(48000,2,3))


if __name__=='__main__':unittest.main()
