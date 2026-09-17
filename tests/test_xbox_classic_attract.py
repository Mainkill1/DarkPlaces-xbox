from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
VID = ROOT / "xbox" / "classic" / "vid_xbox.c"
MAKE = ROOT / "xbox" / "classic" / "Makefile"
STAGER = ROOT / "tools" / "xbox" / "stage_classic_release.py"


class ClassicAttractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vid = VID.read_text(encoding="utf-8")
        cls.make = MAKE.read_text(encoding="utf-8")
        cls.stager = STAGER.read_text(encoding="utf-8")

    def test_reuses_tested_button_gate_policy(self):
        self.assertIn("../attract_policy.h", self.vid)
        self.assertIn("DP_ButtonGate_Update", self.vid)
        self.assertIn("xbox/attract_policy.c", self.make)

    def test_takeover_stops_demo_loop_and_opens_menu(self):
        self.assertIn("cls.demonum = -1", self.vid)
        self.assertIn("CL_Disconnect()", self.vid)
        self.assertIn("MR_ToggleMenu_f()", self.vid)
        self.assertIn("XBOX_ATTRACT_TAKEOVER", self.vid)

    def test_takeover_consumes_held_button_until_release(self):
        self.assertIn("attract_consume_until_release", self.vid)
        self.assertIn("if (!buttonmask)", self.vid)

    def test_stick_axes_do_not_trigger_takeover(self):
        # The takeover mask must be built only from buttons and trigger thresholds.
        start = self.vid.index("static uint32_t Xbox_ButtonMask")
        end = self.vid.index("static void Xbox_OpenController", start)
        body = self.vid[start:end]
        self.assertNotIn("LEFTX", body)
        self.assertNotIn("LEFTY", body)
        self.assertNotIn("RIGHTX", body)
        self.assertNotIn("RIGHTY", body)

    def test_start_restarts_only_a_manually_stopped_attract_session(self):
        self.assertIn("attract_manual_stop", self.vid)
        self.assertIn('Cbuf_AddText("xbox_demo_start\\n")', self.vid)
        self.assertIn("XBOX_ATTRACT_RESTART", self.vid)

    def test_staged_defaults_define_single_reusable_playlist_alias(self):
        self.assertIn('alias xbox_demo_start', self.stager)
        self.assertIn("xbox_demo_start", self.stager)
        self.assertNotIn("\nstartdemos demos/bench1", self.stager)

    def test_classic_bindings_match_approved_original_xbox_semantics(self):
        expected = (
            "bind JOY1 +jump",
            "bind JOY2 +crouch",
            "bind JOY3 dropweapon",
            "bind JOY4 weaplast",
            "bind JOY5 weapprev",
            "bind JOY6 weapnext",
            "bind JOY7 +hook",
            "bind JOY8 +zoom",
            "bind AUX1 +attack2",
            "bind AUX2 +attack",
            "bind AUX3 +showscores",
            "bind AUX4 +show_info",
            "bind AUX5 weapprev",
            "bind AUX6 weapnext",
        )
        for binding in expected:
            self.assertIn(binding, self.stager)
        self.assertNotIn("bind JOY4 _weapprev", self.stager)


if __name__ == "__main__":
    unittest.main()
