import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "xbox"
sys.path.insert(0, str(TOOLS))

import stage_classic_release  # noqa: E402


class ClassicReleaseStagingTests(unittest.TestCase):
    def make_archive(self, root: Path, entries: dict[str, bytes]) -> tuple[Path, str]:
        archive = root / "nexuiz-252.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as zf:
            for name, data in entries.items():
                zf.writestr(name, data)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        return archive, digest

    def test_stage_copies_complete_data_tree_and_writes_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive, digest = self.make_archive(root, {
                "Nexuiz/data/data20091001.pk3": b"pk3-a",
                "Nexuiz/data/data20091001extra.pk3": b"pk3-b",
                "Nexuiz/data/default.cfg": b"original\n",
            })
            disc = root / "disc"
            identity = stage_classic_release.stage_release(archive, disc, digest)
            self.assertEqual((disc / "data" / "data20091001.pk3").read_bytes(), b"pk3-a")
            self.assertEqual((disc / "data" / "default.cfg").read_bytes(), b"original\n")
            defaults = (disc / "data" / "xbox-defaults.cfg").read_text(encoding="utf-8")
            self.assertIn("startdemos demos/bench1", defaults)
            self.assertIn("bind AUX2 +attack", defaults)
            autoexec = (disc / "data" / "autoexec.cfg").read_text(encoding="utf-8")
            self.assertIn("exec xbox-defaults.cfg", autoexec)
            self.assertIn("developer_loading 1", defaults)
            self.assertIn("developer_texturelogging 1", defaults)
            saved = json.loads((disc / "CONTENT-IDENTITY.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["source_sha256"], digest)
            self.assertEqual(saved["data_prefix"], "Nexuiz/data/")
            self.assertEqual(saved["staged_file_count"], identity["staged_file_count"])

    def test_stage_preserves_existing_autoexec_before_xbox_defaults(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive, digest = self.make_archive(root, {
                "Nexuiz/data/data.pk3": b"pk3",
                "Nexuiz/data/autoexec.cfg": b"set oldvalue 1\n",
            })
            disc = root / "disc"
            stage_classic_release.stage_release(archive, disc, digest)
            text = (disc / "data" / "autoexec.cfg").read_text(encoding="utf-8")
            self.assertTrue(text.startswith("set oldvalue 1\n"))
            self.assertTrue(text.rstrip().endswith("exec xbox-defaults.cfg"))

    def test_memory_profile_is_applied_before_autoplay(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive, digest = self.make_archive(
                root, {"Nexuiz/data/data.pk3": b"pk3"}
            )
            disc = root / "disc"
            stage_classic_release.stage_release(archive, disc, digest)
            defaults = (disc / "data" / "xbox-defaults.cfg").read_text(
                encoding="utf-8"
            )
            self.assertIn("xbox_apply_memory_profile", defaults)
            profile = defaults.index("xbox_apply_memory_profile")
            auto_quality = defaults.index("cl_minfps_force 0")
            autoplay = defaults.index("xbox_demo_start")
            self.assertLess(auto_quality, profile)
            self.assertLess(profile, autoplay)

    def test_stage_rejects_archive_sha_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive, _ = self.make_archive(root, {"Nexuiz/data/data.pk3": b"pk3"})
            with self.assertRaises(stage_classic_release.StageError):
                stage_classic_release.stage_release(archive, root / "disc", "0" * 64)

    def test_stage_rejects_multiple_data_roots(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive, digest = self.make_archive(root, {
                "A/data/a.pk3": b"a",
                "B/data/b.pk3": b"b",
            })
            with self.assertRaises(stage_classic_release.StageError):
                stage_classic_release.stage_release(archive, root / "disc", digest)

    def test_stage_rejects_case_collision(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive, digest = self.make_archive(root, {
                "Nexuiz/data/data.pk3": b"a",
                "Nexuiz/data/DATA.PK3": b"b",
            })
            with self.assertRaises(stage_classic_release.StageError):
                stage_classic_release.stage_release(archive, root / "disc", digest)

    def test_stage_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive, digest = self.make_archive(root, {
                "Nexuiz/data/data.pk3": b"a",
                "Nexuiz/data/../outside.cfg": b"bad",
            })
            with self.assertRaises(stage_classic_release.StageError):
                stage_classic_release.stage_release(archive, root / "disc", digest)

    def test_stage_ignores_symlink_outside_selected_data_tree(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "nexuiz-252.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as zf:
                zf.writestr("Nexuiz/data/data.pk3", b"pk3")
                symlink = zipfile.ZipInfo("Nexuiz/Nexuiz.app/Contents/MacOS/libogg.dylib")
                symlink.create_system = 3
                symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
                zf.writestr(symlink, b"libogg.0.dylib")
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()

            identity = stage_classic_release.stage_release(archive, root / "disc", digest)

            self.assertEqual(identity["source_file_count"], 1)
            self.assertEqual((root / "disc" / "data" / "data.pk3").read_bytes(), b"pk3")

    def test_stage_rejects_symlink_inside_selected_data_tree(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "nexuiz-252.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as zf:
                zf.writestr("Nexuiz/data/data.pk3", b"pk3")
                symlink = zipfile.ZipInfo("Nexuiz/data/config.cfg")
                symlink.create_system = 3
                symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
                zf.writestr(symlink, b"../outside.cfg")
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()

            with self.assertRaises(stage_classic_release.StageError):
                stage_classic_release.stage_release(archive, root / "disc", digest)


if __name__ == "__main__":
    unittest.main()
