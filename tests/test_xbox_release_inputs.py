import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "xbox"
sys.path.insert(0, str(TOOLS))

import release_inputs  # noqa: E402

OGG_136_COMMIT = "be05b13e98b048f0b5a0f5fa8ce514d56db5f822"
NEXUIZ_252_BYTES = 931253731


class ReleaseInputsTests(unittest.TestCase):
    def make_lock(self, root: Path) -> Path:
        payload = b"release"
        lock = {
            "schema_version": 1,
            "release": "nexuiz-xbox-2.5.2",
            "repositories": {
                "nxdk": {"repository": "XboxDev/nxdk", "commit": "2" * 40, "path": "deps/nxdk"},
                "darkplaces": {"repository": "DarkPlacesEngine/DarkPlaces", "commit": "3" * 40, "path": "deps/darkplaces-classic"},
                "pbgl": {"repository": "fgsfdsfgs/pbgl", "commit": "4" * 40, "path": "deps/pbgl"},
                "ogg": {"repository": "xiph/ogg", "commit": "5" * 40, "path": "deps/ogg"},
                "vorbis": {"repository": "xiph/vorbis", "commit": "6" * 40, "path": "deps/vorbis"},
            },
            "content": {
                "filename": "nexuiz-252.zip",
                "url": "https://example.invalid/nexuiz-252.zip",
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "md5": hashlib.md5(payload).hexdigest(),
            },
        }
        path = root / "release-inputs.json"
        path.write_text(json.dumps(lock), encoding="utf-8")
        return path

    def test_load_lock_accepts_exact_schema(self):
        with tempfile.TemporaryDirectory() as td:
            lock = release_inputs.load_lock(self.make_lock(Path(td)))
        self.assertEqual(lock["release"], "nexuiz-xbox-2.5.2")
        self.assertEqual(set(lock["repositories"]), {"nxdk", "darkplaces", "pbgl", "ogg", "vorbis"})

    def test_load_lock_rejects_non_commit_revision(self):
        with tempfile.TemporaryDirectory() as td:
            path = self.make_lock(Path(td))
            lock = json.loads(path.read_text(encoding="utf-8"))
            lock["repositories"]["nxdk"]["commit"] = "master"
            path.write_text(json.dumps(lock), encoding="utf-8")
            with self.assertRaises(release_inputs.ReleaseInputError):
                release_inputs.load_lock(path)

    def test_load_lock_rejects_invalid_content_size(self):
        with tempfile.TemporaryDirectory() as td:
            path = self.make_lock(Path(td))
            lock = json.loads(path.read_text(encoding="utf-8"))
            lock["content"]["bytes"] = 0
            path.write_text(json.dumps(lock), encoding="utf-8")
            with self.assertRaises(release_inputs.ReleaseInputError):
                release_inputs.load_lock(path)

    def test_verify_file_accepts_expected_sha256(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "nexuiz-252.zip"
            path.write_bytes(b"release")
            release_inputs.verify_file(path, hashlib.sha256(b"release").hexdigest())

    def test_verify_file_rejects_changed_archive(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "nexuiz-252.zip"
            path.write_bytes(b"changed")
            with self.assertRaises(release_inputs.ReleaseInputError):
                release_inputs.verify_file(path, hashlib.sha256(b"release").hexdigest())

    def test_verify_content_checks_size_sha256_and_historical_md5(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "nexuiz-252.zip"
            path.write_bytes(b"release")
            release_inputs.verify_content(
                path,
                len(b"release"),
                hashlib.sha256(b"release").hexdigest(),
                hashlib.md5(b"release").hexdigest(),
            )
            with self.assertRaises(release_inputs.ReleaseInputError):
                release_inputs.verify_content(
                    path,
                    len(b"release") + 1,
                    hashlib.sha256(b"release").hexdigest(),
                    hashlib.md5(b"release").hexdigest(),
                )
            with self.assertRaises(release_inputs.ReleaseInputError):
                release_inputs.verify_content(
                    path,
                    len(b"release"),
                    hashlib.sha256(b"release").hexdigest(),
                    "0" * 32,
                )

    def test_repository_lock_in_repo_matches_versions_and_nxdk_pin(self):
        lock = release_inputs.load_lock(ROOT / "xbox" / "release" / "release-inputs.json")
        versions = (ROOT / "xbox" / "classic" / "versions.mk").read_text(encoding="utf-8")
        nxdk = (ROOT / "xbox" / "nxdk.version").read_text(encoding="utf-8").strip()
        self.assertEqual(lock["repositories"]["nxdk"]["commit"], nxdk)
        self.assertEqual(lock["repositories"]["ogg"]["commit"], OGG_136_COMMIT)
        self.assertEqual(lock["content"]["bytes"], NEXUIZ_252_BYTES)
        self.assertIn(f"DP_CLASSIC_REV := {lock['repositories']['darkplaces']['commit']}", versions)
        self.assertIn(f"PBGL_REV := {lock['repositories']['pbgl']['commit']}", versions)
        self.assertIn(f"OGG_REV := {lock['repositories']['ogg']['commit']}", versions)
        self.assertIn(f"VORBIS_REV := {lock['repositories']['vorbis']['commit']}", versions)
        self.assertIn(f"NEXUIZ_252_BYTES := {lock['content']['bytes']}", versions)
        self.assertIn(f"NEXUIZ_252_SHA256 := {lock['content']['sha256']}", versions)
        self.assertIn(f"NEXUIZ_252_MD5 := {lock['content']['md5']}", versions)


if __name__ == "__main__":
    unittest.main()
