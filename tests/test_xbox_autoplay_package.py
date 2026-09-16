import json
import unittest
import zipfile
import test_xbox_nexuiz_content as fixtures

class AutoplayPackageTests(unittest.TestCase):
    setUp = fixtures.NexuizPreparationTests.setUp
    write_pack = fixtures.NexuizPreparationTests.write_pack
    run_tool = fixtures.NexuizPreparationTests.run_tool
    stage = fixtures.NexuizPreparationTests.stage

    def add_demos(self, names):
        for name in names:
            payload = b'-1\n' + b'generated fixture, not a playable world'
            self.entries[name] = payload
            self.selection['assets'].append(dict(path=name, source='fixture.pk3', sha256=fixtures.digest(payload),
                license='CC0-1.0', attribution='fixture', notice='docs/license.txt'))
        self.write_pack(self.entries)
        self.selection['sources'][0]['sha256'] = fixtures.digest(self.archive.read_bytes())
        self.selection['max_asset_bytes'] = 65536
        self.selection['max_total_bytes'] = 1048576

    def test_selected_demos_generate_autoplay_and_controller_config_automatically(self):
        self.add_demos(['demos/z.dem', 'demos/a.dem'])
        self.stage()
        with zipfile.ZipFile(self.root / 'out/data/xboxprep.pk3') as pack:
            cfg = pack.read('xbox-benchmark.cfg').decode()
        self.assertIn('xbox_demo_playlist "demos/a.dem" "demos/z.dem"', cfg)
        self.assertIn('joy_enable 1', cfg)
        self.assertIn('bind X360_RIGHT_TRIGGER "+attack"', cfg)
        self.assertIn('bind X360_LEFT_TRIGGER "+attack2"', cfg)
        self.assertIn('bind X360_LEFT_SHOULDER "weapprev"', cfg)
        self.assertIn('bind X360_RIGHT_SHOULDER "weapnext"', cfg)
        manifest = json.loads((self.root / 'out/manifest.json').read_text())
        self.assertTrue(manifest['autoplay']['configured'])
        self.assertEqual(manifest['autoplay']['demos'], ['demos/a.dem', 'demos/z.dem'])
        self.assertEqual(manifest['generated_files'][0]['sha256'], fixtures.digest(cfg.encode()))
        self.assertFalse(manifest['xbox_ready'])

    def test_no_selected_demo_is_explicitly_not_autoplay_ready(self):
        self.stage()
        manifest = json.loads((self.root / 'out/manifest.json').read_text())
        self.assertFalse(manifest['autoplay']['configured'])

    def test_requested_autoplay_without_a_demo_fails_before_output(self):
        selection = self.root / 'selection.json'
        selection.write_text(json.dumps(self.selection))
        result = self.run_tool('stage', '--data-dir', self.data, '--selection', selection,
              '--output', self.root / 'out', '--require-autoplay', success=False)
        self.assertIn('demo', result.stderr.lower())
        self.assertFalse((self.root / 'out').exists())

    def test_explicit_order_and_missing_demo_validation(self):
        self.add_demos(['demos/a.dem', 'demos/z.dem'])
        selection = self.root / 'selection.json'
        selection.write_text(json.dumps(self.selection))
        self.run_tool('stage', '--data-dir', self.data, '--selection', selection,
              '--output', self.root / 'out', '--demo', 'demos/z.dem', '--demo', 'demos/a.dem')
        with zipfile.ZipFile(self.root / 'out/data/xboxprep.pk3') as pack:
            self.assertIn('"demos/z.dem" "demos/a.dem"', pack.read('xbox-benchmark.cfg').decode())
        self.run_tool('stage', '--data-dir', self.data, '--selection', selection,
              '--output', self.root / 'bad', '--demo', 'demos/missing.dem', success=False)
        self.assertFalse((self.root / 'bad').exists())

    def test_more_than_eight_demos_are_not_silently_truncated(self):
        self.add_demos([f'demos/{i}.dem' for i in range(9)])
        self.assertIn('8', self.stage(success=False).stderr)

    def test_generated_config_cannot_replace_a_selected_source_file(self):
        self.add_demos(['demos/a.dem'])
        self.entries['xbox-benchmark.cfg'] = b'caller config'
        self.selection['assets'].append(dict(path='xbox-benchmark.cfg', source='fixture.pk3',
            sha256=fixtures.digest(b'caller config'), license='CC0-1.0', attribution='fixture', notice='docs/license.txt'))
        self.write_pack(self.entries)
        self.selection['sources'][0]['sha256'] = fixtures.digest(self.archive.read_bytes())
        self.assertIn('collides', self.stage(success=False).stderr)

    def test_generated_playlist_fits_small_memory_command_buffer(self):
        self.add_demos(['demos/' + str(i) + 'x' * 115 + '.dem' for i in range(8)])
        self.assertIn('command', self.stage(success=False).stderr)

    def test_autoplay_pack_and_manifest_are_reproducible(self):
        self.add_demos(['demos/first.dem'])
        self.stage('first')
        self.selection['assets'].reverse()
        self.stage('second')
        for name in ['manifest.json', 'data/xboxprep.pk3']:
            self.assertEqual((self.root / 'first' / name).read_bytes(), (self.root / 'second' / name).read_bytes())

if __name__ == '__main__':
    unittest.main()
