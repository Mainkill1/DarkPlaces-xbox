"""Executable tests of the real attract policy and SDL controller adapter."""
from pathlib import Path
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

POLICY = r'''
#include <assert.h>
#include <limits.h>
#include <string.h>
#include "xbox/attract_policy.h"

int main(void)
{
    dp_attract_t s;
    dp_button_gate_t gate = {0};
    unsigned index = 99;
    int track = 0;
    size_t consumed = 0;
    DP_Attract_Init(&s);
    assert(!DP_Attract_Active(&s));
    assert(!DP_Attract_Start(&s, 0));
    assert(s.state == DP_ATTRACT_FAILED);
    assert(!DP_Attract_Start(&s, 9));
    assert(DP_Attract_Start(&s, 2));
    assert(DP_Attract_TakeNext(&s, &index) && index == 0);
    assert(!DP_Attract_TakeNext(&s, &index));
    DP_Attract_Loaded(&s, true);
    assert(s.state == DP_ATTRACT_PLAYING);
    DP_Attract_Ended(&s, true);
    assert(DP_Attract_TakeNext(&s, &index) && index == 1);
    DP_Attract_Loaded(&s, true);
    DP_Attract_Ended(&s, true);
    assert(s.loops == 1 && s.index == 0);
    assert(DP_Attract_TakeNext(&s, &index) && index == 0);
    DP_Attract_Stop(&s);
    assert(s.state == DP_ATTRACT_MANUAL && !DP_Attract_Active(&s));
    DP_Attract_Loaded(&s, true); /* stale completion cannot restart stopped work */
    DP_Attract_Ended(&s, true);
    assert(!DP_Attract_TakeNext(&s, &index));
    assert(DP_Attract_Start(&s, 1));
    assert(DP_Attract_TakeNext(&s, &index));
    DP_Attract_Loaded(&s, false);
    assert(s.state == DP_ATTRACT_FAILED && !DP_Attract_TakeNext(&s, &index));
    assert(DP_Attract_Start(&s, 1));
    assert(DP_Attract_TakeNext(&s, &index));
    DP_Attract_Loaded(&s, true);
    DP_Attract_Ended(&s, false);
    assert(s.state == DP_ATTRACT_FAILED);
    /* A held boot/hotplug button is not a new takeover press. */
    assert(DP_ButtonGate_Update(&gate, false, 0, 0) == 0);
    assert(DP_ButtonGate_Update(&gate, true, 12, 1) == 0);
    assert(!gate.armed);
    assert(DP_ButtonGate_Update(&gate, true, 12, 1) == 0);
    assert(DP_ButtonGate_Update(&gate, true, 12, 0) == 0 && gate.armed);
    assert(DP_ButtonGate_Update(&gate, true, 12, 4) == 4);
    assert(DP_ButtonGate_Update(&gate, true, 12, 4) == 0);
    DP_ButtonGate_Reset(&gate);
    assert(DP_ButtonGate_Update(&gate, true, 12, 4) == 0);
    assert(DP_ButtonGate_Update(&gate, true, 12, 0) == 0);
    assert(DP_ButtonGate_Update(&gate, true, 12, 8) == 8);
    assert(DP_ButtonGate_Update(&gate, false, 0, 0) == 0 && !gate.armed);
    assert(DP_ButtonGate_Update(&gate, true, 55, 8) == 0);
    assert(DP_ButtonGate_Update(&gate, true, 55, 0) == 0);
    assert(DP_ButtonGate_Update(&gate, true, 55, 2) == 2);
    /* Bounded parser: no EOF loop, overflow, or partial integer acceptance. */
    assert(DP_DemoTrackHeader("-1\nabc", 6, &track, &consumed));
    assert(track == -1 && consumed == 3);
    assert(DP_DemoTrackHeader("0\n", 2, &track, &consumed) && track == 0);
    assert(DP_DemoTrackHeader("12\r\n", 4, &track, &consumed) && track == 12);
    assert(!DP_DemoTrackHeader("", 0, &track, &consumed));
    assert(!DP_DemoTrackHeader("-1", 2, &track, &consumed));
    assert(!DP_DemoTrackHeader("\n", 1, &track, &consumed));
    assert(!DP_DemoTrackHeader("-\n", 2, &track, &consumed));
    assert(!DP_DemoTrackHeader("x\n", 2, &track, &consumed));
    assert(!DP_DemoTrackHeader("999999999999999\n", 16, &track, &consumed));
    assert(!DP_DemoTrackHeader("2147483648\n", 11, &track, &consumed));
    assert(DP_DemoTrackHeader("2147483647\n", 11, &track, &consumed) && track == INT_MAX);
    assert(DP_DemoTrackHeader("-2147483648\n", 12, &track, &consumed) && track == INT_MIN);
    assert(DP_DemoPathValid("demos/bench1.dem"));
    assert(!DP_DemoPathValid("../bad.dem"));
    assert(!DP_DemoPathValid("a;quit.dem"));
    assert(!DP_DemoPathValid("/absolute.dem"));
    assert(!DP_DemoPathValid("demos//bad.dem"));
    assert(!DP_DemoPathValid("a\\b.dem"));
    assert(!DP_DemoPathValid("not-a-demo.pk3"));
    return 0;
}
'''

SDL_TEST = r'''
#include <assert.h>
#include <stdio.h>
#include <math.h>
#include <SDL.h>
#include "xbox/controller_sdl.h"
/* The adapter supports the old nxdk SDL; virtual devices are a host-test facility. */
#if !SDL_VERSION_ATLEAST(2,0,14)
extern int SDL_JoystickAttachVirtual(SDL_JoystickType, int, int, int);
extern int SDL_JoystickDetachVirtual(int);
extern int SDL_JoystickSetVirtualAxis(SDL_Joystick*, int, Sint16);
extern int SDL_JoystickSetVirtualButton(SDL_Joystick*, int, Uint8);
extern int SDL_JoystickSetVirtualHat(SDL_Joystick*, int, Uint8);
#endif
static SDL_Joystick *create_pad(int *index)
{
    char guid[33], mapping[512];
    SDL_Joystick *joy;
    *index = SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER, 6, 10, 1);
    assert(*index >= 0);
    SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(*index), guid, sizeof(guid));
    snprintf(mapping, sizeof(mapping),
        "%s,Original Xbox test,a:b0,b:b1,x:b2,y:b3,leftshoulder:b4,rightshoulder:b5,"
        "back:b6,start:b7,leftstick:b8,rightstick:b9,dpup:h0.1,dpright:h0.2,dpdown:h0.4,"
        "dpleft:h0.8,leftx:a0,lefty:a1,lefttrigger:a2,rightx:a3,righty:a4,righttrigger:a5,", guid);
    assert(SDL_GameControllerAddMapping(mapping) >= 0);
    joy = SDL_JoystickOpen(*index);
    assert(joy);
    assert(SDL_JoystickSetVirtualAxis(joy, 2, -32768) == 0);
    assert(SDL_JoystickSetVirtualAxis(joy, 5, -32768) == 0);
    return joy;
}
int main(void)
{
    dp_pad_sample_t s;
    SDL_Joystick *joy;
    int index;
    SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, "1");
    assert(DP_ControllerSDL_Init() == 0);
    assert(DP_ControllerSDL_Init() == 0);
    DP_ControllerSDL_Poll(&s);
    assert(!s.connected && s.buttons == 0);
    joy = create_pad(&index);
    DP_ControllerSDL_Poll(&s);
    assert(s.connected && s.buttons == 0);
    assert(s.axis[4] == 0 && s.axis[5] == 0);
    SDL_JoystickSetVirtualButton(joy, 0, 1);
    SDL_JoystickSetVirtualButton(joy, 4, 1); /* White -> left shoulder */
    SDL_JoystickSetVirtualButton(joy, 5, 1); /* Black -> right shoulder */
    SDL_JoystickSetVirtualHat(joy, 0, SDL_HAT_UP | SDL_HAT_LEFT);
    SDL_JoystickSetVirtualAxis(joy, 0, 32767);
    SDL_JoystickSetVirtualAxis(joy, 1, -32768);
    SDL_JoystickSetVirtualAxis(joy, 3, -32768);
    SDL_JoystickSetVirtualAxis(joy, 4, 32767);
    SDL_JoystickSetVirtualAxis(joy, 2, 32767);
    DP_ControllerSDL_Poll(&s);
    assert(s.buttons & (1u << DP_PAD_A));
    assert(s.buttons & (1u << DP_PAD_WHITE));
    assert(s.buttons & (1u << DP_PAD_BLACK));
    assert(s.buttons & (1u << DP_PAD_UP));
    assert(s.buttons & (1u << DP_PAD_LEFT));
    assert(s.buttons & (1u << DP_PAD_LT));
    assert(!(s.buttons & (1u << DP_PAD_RT)));
    assert(s.axis[0] == 1 && s.axis[1] == 1 && s.axis[2] == -1 && s.axis[3] == -1);
    /* Unplugging clears all buttons and axes, with no stale handle use. */
    assert(SDL_JoystickDetachVirtual(index) == 0);
    SDL_JoystickClose(joy);
    DP_ControllerSDL_Poll(&s);
    assert(!s.connected && s.buttons == 0 && s.axis[0] == 0);
    joy = create_pad(&index);
    DP_ControllerSDL_Poll(&s);
    assert(s.connected && s.buttons == 0);
    SDL_JoystickDetachVirtual(index);
    SDL_JoystickClose(joy);
    DP_ControllerSDL_Poll(&s);
    DP_ControllerSDL_Shutdown();
    DP_ControllerSDL_Shutdown();
    return 0;
}
'''

class XboxAutoplayTests(unittest.TestCase):
    def compile_run(self, source, files, extra=()):
        for file in files:
            self.assertTrue((ROOT / file).is_file(), f"Missing implementation: {file}")
        cc = shlex.split(os.environ.get("CC", "cc"))
        self.assertTrue(shutil.which(cc[0]))
        with tempfile.TemporaryDirectory() as temp:
            t = Path(temp)
            (t / "test.c").write_text(source)
            build = subprocess.run([*cc, "-std=c11", "-O1", "-Wall", "-Wextra", "-Werror",
                                    "-I", str(ROOT), str(t / "test.c"),
                                    *[str(ROOT / f) for f in files], *extra,
                                    "-o", str(t / "test")], capture_output=True, text=True, timeout=40)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(t / "test")], capture_output=True, text=True, timeout=15,
                                 env=dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy"))
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_no_input_loop_failure_takeover_hotplug_and_header_parser(self):
        self.compile_run(POLICY, ["xbox/attract_policy.c"])

    def test_actual_engine_adapter_boot_loop_takeover_resume_and_failures(self):
        self.compile_run((ROOT / "tests/autoplay_engine_harness.c").read_text(),
                         ["cl_attract.c", "xbox/attract_policy.c"],
                         ["-DCONFIG_MENU", "-Wno-missing-field-initializers",
                          "-I", str(ROOT / "tests"),
                          "-include", str(ROOT / "tests/autoplay_engine_stubs.h")])

    def test_sdl_controller_real_virtual_device_and_original_layout(self):
        if os.environ.get("DP_TEST_SDL_CFLAGS"):
            flags = shlex.split(os.environ["DP_TEST_SDL_CFLAGS"])
        elif shutil.which("sdl2-config"):
            flags = shlex.split(subprocess.check_output(["sdl2-config", "--cflags", "--libs"], text=True))
        else:
            if os.environ.get("DP_REQUIRE_SDL_TESTS"):
                self.fail("SDL2 development headers and runtime are required")
            self.skipTest("SDL2 dev files unavailable; required by autoplay CI")
        self.compile_run(SDL_TEST, ["xbox/controller_sdl.c"], flags)

if __name__ == '__main__':
    unittest.main()
