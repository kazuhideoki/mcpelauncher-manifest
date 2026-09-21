import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'manage.py'
spec = importlib.util.spec_from_file_location('manage', MODULE)
manage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manage)


class ProfileRecovery(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='joycon workflow ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / 'launcher data'
        self.runtime = self.root / 'new runtime'
        self.runtime.mkdir()
        self.profiles = self.data / 'profiles/profiles.ini'
        self.profiles.parent.mkdir(parents=True)
        self.original = b'; keep original formatting\r\n[General]\r\nselected=Existing\r\n\r\n[Existing]\r\ncustom=value\r\n'
        self.profiles.write_bytes(self.original)
        config = manage.parser_ini()
        config['Joy-Con-Keyboard'] = manage.profile(self.runtime, self.data, self.root / 'single update mod')
        (self.runtime / 'profile.fragment.ini').write_text(manage.serialize(config))

    def test_activation_preserves_other_profile_and_restores_exact_bytes(self):
        receipt = manage.apply_profile(self.runtime, self.profiles, 'Test-Keyboard')
        config = manage.parser_ini()
        config.read(self.profiles)
        self.assertEqual(config['Existing']['custom'], 'value')
        self.assertEqual(config['General']['selected'], 'Test-Keyboard')
        self.assertEqual(config['Test-Keyboard']['version'], 'lock 972605101')
        manage.restore_receipt(receipt)
        self.assertEqual(self.profiles.read_bytes(), self.original)

    def test_existing_profile_is_not_overwritten(self):
        with self.assertRaisesRegex(ValueError, 'already exists'):
            manage.apply_profile(self.runtime, self.profiles, 'Existing')
        self.assertEqual(self.profiles.read_bytes(), self.original)

    def test_restore_refuses_newer_user_edits(self):
        receipt = manage.apply_profile(self.runtime, self.profiles, 'Test-Keyboard')
        with self.profiles.open('a') as stream:
            stream.write('\n[user_edit]\nkeep=yes\n')
        changed = self.profiles.read_bytes()
        with self.assertRaisesRegex(ValueError, 'newer edits'):
            manage.restore_receipt(receipt)
        self.assertEqual(self.profiles.read_bytes(), changed)

    def test_data_directory_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'dataDir'):
            manage.apply_profile(self.runtime, self.root / 'wrong/profiles/profiles.ini', 'Test')

    def test_ambiguous_paths_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Paths'):
            manage.profile(self.root / 'quoted"name', self.data, self.root / 'mod')


class LaunchArguments(unittest.TestCase):
    def test_literal_arguments_log_permissions_and_rotation(self):
        with tempfile.TemporaryDirectory(prefix='joycon runtime ') as directory:
            root = Path(directory)
            executable = root / 'Contents/MacOS/mcpelauncher_client'
            executable.parent.mkdir(parents=True)
            executable.write_text('#!/usr/bin/env python3\nimport sys,json\nprint(json.dumps(sys.argv[1:]))\n')
            executable.chmod(0o755)
            launch = root / 'launch_client.sh'
            shutil.copy2(MODULE.parent / 'launch_client.sh', launch)
            args = ['-dg', '日本語 game path', '-m', 'one mod', '$(not-a-command)', 'literal;value']
            subprocess.run(['sh', str(launch), 'original executable', *args], check=True)
            log = root / 'runtime.log'
            self.assertEqual(json.loads(log.read_text()), args)
            self.assertEqual(log.stat().st_mode & 0o777, 0o600)
            subprocess.run(['sh', str(launch), 'original', 'second'], check=True)
            self.assertEqual(json.loads((root / 'runtime.previous.log').read_text()), args)
            self.assertEqual(json.loads(log.read_text()), ['second'])


if __name__ == '__main__':
    unittest.main()
