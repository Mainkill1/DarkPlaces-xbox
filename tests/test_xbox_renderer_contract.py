from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class XboxRendererContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        path = ROOT / relative
        self.assertTrue(path.is_file(), f"missing renderer contract file: {relative}")
        return path.read_text(encoding="utf-8")

    def test_renderpath_and_mode_specific_native_profile_exist(self) -> None:
        vid = self.read("vid.h")
        profile = self.read("xbox/game/profile.h")
        makefile = self.read("xbox/game/Makefile")

        self.assertIn("RENDERPATH_XBOX", vid)
        self.assertIn("-DDP_XBOX_NATIVE_RENDERER=1", makefile)
        self.assertIn("#define DP_XBOX_CAP_RENDERER 0", profile)
        self.assertNotIn("#define DP_XBOX_NATIVE_RENDERER 1", profile)

    def test_native_and_bootstrap_backends_are_mutually_exclusive(self) -> None:
        makefile = self.read("xbox/game/Makefile")
        sources = self.read("xbox/game/sources.mk")

        self.assertIn("XBOX_RENDERER ?= bootstrap", makefile)
        self.assertIn("ifeq ($(XBOX_RENDERER),native)", makefile)
        self.assertIn("else ifeq ($(XBOX_RENDERER),bootstrap)", makefile)
        self.assertIn("XBOX_RENDERER must be native or bootstrap", makefile)
        self.assertIn("DP_XBOX_BOOTSTRAP_VIDEO_SRCS", sources)
        self.assertIn("DP_XBOX_NATIVE_RENDER_SRCS", sources)
        self.assertIn("DP_XBOX_BOOTSTRAP_SOURCES", sources)
        self.assertIn("DP_XBOX_NATIVE_SOURCES", sources)

    def test_native_manifest_has_required_owners_and_no_desktop_backend(self) -> None:
        sources = self.read("xbox/game/sources.mk")
        native = sources.split("DP_XBOX_NATIVE_RENDER_SRCS :=", 1)[1].split("\n\n", 1)[0]
        for required in (
            "vid_xbox.c",
            "r_xbox_stats.c",
            "r_xbox_backend.c",
            "r_xbox_texture.c",
            "r_xbox_program.c",
            "r_xbox_material.c",
            "r_xbox_draw2d.c",
            "r_xbox_world.c",
            "r_xbox_models.c",
        ):
            self.assertIn(required, native)
        for prohibited in (
            "vid_xbox_bootstrap.c",
            "gl_backend.c",
            "gl_textures.c",
        ):
            self.assertNotIn(prohibited, native)

    def test_diagnostics_do_not_link_the_production_renderer(self) -> None:
        for relative in ("xbox/Makefile", "xbox/inputcheck/Makefile"):
            text = self.read(relative)
            self.assertNotIn("r_xbox_", text)
            self.assertNotIn("vid_xbox.c", text)

    def test_renderer_statistics_contract_matches_required_fields(self) -> None:
        header = self.read("r_xbox_stats.h")
        for field in (
            "frame_number",
            "draw_calls",
            "triangles",
            "state_changes",
            "texture_binds",
            "texture_uploads",
            "texture_upload_bytes",
            "dynamic_vertex_bytes",
            "dynamic_index_bytes",
            "multipass_draws",
            "fallback_draws",
            "unsupported_materials",
            "invalid_draws",
            "ring_stalls",
            "gpu_waits",
            "vblank_waits",
            "texture_resident_bytes",
            "texture_peak_bytes",
        ):
            self.assertIn(field, header)

    def test_source_audit_accepts_each_explicit_mode(self) -> None:
        audit = ROOT / "tools/xbox/audit_renderer_sources.py"
        self.assertTrue(audit.is_file())
        for mode in ("bootstrap", "native"):
            result = subprocess.run(
                [
                    sys.executable,
                    str(audit),
                    "--root",
                    str(ROOT),
                    "--manifest",
                    str(ROOT / "xbox/game/sources.mk"),
                    "--mode",
                    mode,
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn(f'"mode": "{mode}"', result.stdout)
            self.assertIn('"compile_link_runtime_verified": false', result.stdout)


if __name__ == "__main__":
    unittest.main()
