"""The staged content profile must be checked against physical RAM before autoplay."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "xbox" / "classic" / "memory_profile_xbox.c"


class ContentProfileGateTests(unittest.TestCase):
    def test_runtime_command_rejects_mismatched_content(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('Cmd_AddCommand("xbox_expect_content_profile"', source)
        self.assertIn('"Xbox content profile mismatch disc=', source)
        self.assertIn('"Xbox content profile mismatch: disc=', source)
        self.assertIn('detected=%llu MiB', source)
        self.assertIn('Xbox_MemoryProfilePolicy()', source)

    def test_presented_frame_reports_physical_headroom(self):
        source = SOURCE.read_text(encoding="utf-8")
        video = (ROOT / "xbox" / "classic" / "vid_xbox.c").read_text(encoding="utf-8")
        self.assertIn("void Xbox_MemoryTracePresentedFrame(void)", source)
        self.assertIn("available_pages=%llu", source)
        self.assertIn("low_water_pages=%llu", source)
        self.assertIn("Xbox_MemoryTracePresentedFrame();", video)


if __name__ == "__main__":
    unittest.main()
