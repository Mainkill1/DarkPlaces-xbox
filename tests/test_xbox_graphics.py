"""Graphics policy, packaging defaults and real menu behavior with service doubles."""
import importlib.util
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class GraphicsTests(unittest.TestCase):
    def test_generated_profile_disables_adaptation_without_disabling_future_toggle(self):
        spec = importlib.util.spec_from_file_location('autoplay_config', ROOT / 'tools/xbox/autoplay_config.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _, output = module.build_config(['demos/world.dem'], require=True)
        settings = output.decode().splitlines()
        self.assertIn('cl_minfps 0', settings)
        self.assertIn('cl_minfps_force 0', settings)
        self.assertIn('cl_minfps_qualitymin 0.25', settings)
        self.assertIn('cl_minfps_qualitymax 1', settings)
        self.assertIn('xbox_autoquality_target 60', settings)

    def test_engine_default_is_off(self):
        source = (ROOT / 'cl_main.c').read_text()
        self.assertRegex(source, r'cvar_t cl_minfps\s*=\s*\{[^\n]+"cl_minfps", "0"')

    def test_real_menu_and_quality_toggle(self):
        for name in ('cl_graphics_menu.c', 'cl_graphics_menu.h', 'tests/graphics_engine_harness.c'):
            self.assertTrue((ROOT / name).is_file(), f'Missing implementation: {name}')
        cc = shlex.split(os.environ.get('CC', 'cc'))
        self.assertTrue(shutil.which(cc[0]))
        with tempfile.TemporaryDirectory() as temp:
            exe = str(Path(temp) / 'graphics-test')
            result = subprocess.run([*cc, '-std=c11', '-O1', '-Wall', '-Wextra', '-Werror',
                '-Wno-missing-field-initializers', '-DCONFIG_MENU', '-I', str(ROOT),
                '-I', str(ROOT/'tests'), '-include', str(ROOT/'tests/graphics_engine_stubs.h'),
                str(ROOT/'cl_graphics_menu.c'), str(ROOT/'tests/graphics_engine_harness.c'),
                '-lm', '-o', exe], capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            result = subprocess.run([exe], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_menu_draw_key_and_controller_call_sites(self):
        self.assertIn('CL_GraphicsMenu_Draw()', (ROOT/'cl_screen.c').read_text())
        keys = (ROOT/'keys.c').read_text()
        start = keys.index('Key_Event (int key, int ascii, qbool down)')
        self.assertGreater(keys.index('CL_GraphicsMenu_KeyEvent(key, down)', start),
                           keys.index('keydown[key] = 0;', start))
        code = (ROOT/'cl_attract.c').read_text()
        self.assertIn('CL_GraphicsMenu_Editing()', code)
        self.assertIn('CL_GraphicsMenu_Context()', code)
        self.assertIn('CL_GraphicsMenu_Open()', code)
        self.assertIn('CL_GraphicsMenu_BootConfig()', code)
        self.assertIn('cl_graphics_menu.o', (ROOT/'makefile.inc').read_text())

if __name__ == '__main__':
    unittest.main()
