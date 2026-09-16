"""Behavioral tests use generated assets, never a redistributed game archive."""
import hashlib
import json
from pathlib import Path
import subprocess
import struct
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/xbox/nexuiz_prepare.py"


def digest(data):
    return hashlib.sha256(data).hexdigest()


class NexuizPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "source"
        self.data.mkdir()
        self.entries = {
            "maps/test.bsp": b"generated test geometry, not a real BSP",
            "docs/license.txt": b"Generated fixture: CC0-1.0",
            "default.cfg": b"echo fixture\n",
        }
        self.archive = self.data / "fixture.pk3"
        self.write_pack(self.entries)
        self.selection = {
            "schema_version": 1,
            "release": "nexuiz-classic-2.5.2",
            "profile": "test-preparation",
            "max_asset_bytes": 1024,
            "max_total_bytes": 4096,
            "sources": [{"file": "fixture.pk3", "sha256": digest(self.archive.read_bytes()),
                         "origin": "generated test fixture, not Nexuiz content"}],
            "assets": [{"path": name, "source": "fixture.pk3", "sha256": digest(payload),
                        "license": "CC0-1.0", "attribution": "Generated test fixture",
                        "notice": "docs/license.txt"}
                       for name, payload in self.entries.items()],
        }

    def write_pack(self, entries, compression=zipfile.ZIP_DEFLATED):
        with zipfile.ZipFile(self.archive, "w", compression=compression) as pack:
            for name, payload in entries.items():
                pack.writestr(name, payload)

    def run_tool(self, *args, success=True):
        result = subprocess.run([sys.executable, str(TOOL), *map(str, args)],
                                capture_output=True, text=True, timeout=15)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertNotIn("Traceback", result.stderr)
        return result

    def stage(self, output="out", success=True):
        path = self.root / "selection.json"
        path.write_text(json.dumps(self.selection), encoding="utf-8")
        return self.run_tool("stage", "--data-dir", self.data,
                             "--selection", path, "--output", self.root / output,
                             success=success)

    def test_inventory_records_pack_and_asset_hashes(self):
        target = self.root / "inventory.json"
        self.run_tool("inventory", "--data-dir", self.data, "--output", target)
        report = json.loads(target.read_text())
        self.assertEqual(report["release"], "nexuiz-classic-2.5.2")
        source = report["sources"][0]
        self.assertEqual(source["sha256"], digest(self.archive.read_bytes()))
        files = {a["path"]: a for a in source["assets"]}
        self.assertEqual(files["maps/test.bsp"]["sha256"], digest(self.entries["maps/test.bsp"]))
        self.assertFalse(report["xbox_ready"])

    def test_stage_is_deterministic_and_preserves_selected_bytes(self):
        self.stage("a")
        self.selection["assets"].reverse()
        self.stage("b")
        for filename in ("data/xboxprep.pk3", "manifest.json"):
            self.assertEqual((self.root / "a" / filename).read_bytes(),
                             (self.root / "b" / filename).read_bytes())
        with zipfile.ZipFile(self.root / "a/data/xboxprep.pk3") as pack:
            self.assertEqual(pack.namelist(), sorted(self.entries))
            for entry in pack.infolist():
                self.assertEqual(entry.compress_type, zipfile.ZIP_STORED)
                self.assertEqual(pack.read(entry), self.entries[entry.filename])
                self.assertEqual(entry.date_time, (1980, 1, 1, 0, 0, 0))
        manifest = json.loads((self.root / "a/manifest.json").read_text())
        self.assertFalse(manifest["xbox_ready"])
        self.assertEqual(manifest["conversion"], "none-byte-preserving")
        self.assertEqual(manifest["selected_bytes"], sum(map(len, self.entries.values())))
        self.assertEqual(manifest["package_sha256"], digest((self.root / "a/data/xboxprep.pk3").read_bytes()))

    def test_changed_source_rejected_without_output(self):
        self.archive.write_bytes(self.archive.read_bytes() + b"changed")
        result = self.stage(success=False)
        self.assertIn("source hash mismatch", result.stderr)
        self.assertFalse((self.root / "out").exists())

    def test_wrong_asset_hash_rejected_without_output(self):
        self.selection["assets"][0]["sha256"] = "0" * 64
        self.assertIn("asset hash mismatch", self.stage(success=False).stderr)
        self.assertFalse((self.root / "out").exists())

    def test_missing_selected_asset_fails(self):
        self.selection["assets"][0]["path"] = "maps/missing.bsp"
        self.assertIn("missing asset", self.stage(success=False).stderr)

    def test_license_and_notice_required(self):
        for field in ("license", "attribution", "notice"):
            with self.subTest(field=field):
                previous = self.selection["assets"][0].pop(field)
                self.stage(success=False)
                self.selection["assets"][0][field] = previous
        self.selection["assets"][0]["notice"] = "missing.txt"
        self.assertIn("notice", self.stage(success=False).stderr)

    def test_caps_are_enforced(self):
        self.selection["max_asset_bytes"] = 4
        self.assertIn("asset budget", self.stage(success=False).stderr)
        self.selection["max_asset_bytes"] = 1024
        self.selection["max_total_bytes"] = 8
        self.assertIn("total budget", self.stage(success=False).stderr)

    def test_existing_output_is_not_modified(self):
        self.stage()
        sentinel = self.root / "out/keep.txt"
        sentinel.write_text("keep")
        self.stage(success=False)
        self.assertEqual(sentinel.read_text(), "keep")

    def test_selected_case_collision_fails(self):
        item = dict(self.selection["assets"][0])
        item["path"] = item["path"].upper()
        self.selection["assets"].append(item)
        self.assertIn("collision", self.stage(success=False).stderr)

    def test_archive_traversal_and_case_collisions_fail(self):
        for entries in ({"../escape": b"x"}, {"A.txt": b"a", "a.txt": b"b"},
                        {"bad\\name": b"x"}, {"/absolute": b"x"},
                        {"a/./b": b"x"}, {"x" * 128: b"x"}):
            with self.subTest(entries=entries):
                self.write_pack(entries)
                self.run_tool("inventory", "--data-dir", self.data,
                              "--output", self.root / "invalid.json", success=False)

    def test_non_pk3_and_symlink_source_rejected(self):
        self.selection["sources"][0]["file"] = "../fixture.pk3"
        self.stage(success=False)
        self.selection["sources"][0]["file"] = "fixture.zip"
        self.stage(success=False)

    def test_unsupported_compression_and_archive_symlinks_rejected(self):
        self.write_pack({"file.txt": b"data"}, zipfile.ZIP_BZIP2)
        self.run_tool("inventory", "--data-dir", self.data,
                      "--output", self.root / "invalid.json", success=False)
        with zipfile.ZipFile(self.archive, "w") as pack:
            info = zipfile.ZipInfo("link.txt")
            info.create_system = 3
            info.external_attr = (0o120777 << 16)
            pack.writestr(info, "../outside")
        self.run_tool("inventory", "--data-dir", self.data,
                      "--output", self.root / "invalid.json", success=False)

    def test_duplicate_json_keys_and_bad_schema_fail_cleanly(self):
        path = self.root / "invalid.json"
        for content in ('{"schema_version":1,"schema_version":1}', '[]', '{broken'):
            with self.subTest(content=content):
                path.write_text(content)
                self.run_tool("stage", "--data-dir", self.data, "--selection", path,
                              "--output", self.root / "out", success=False)

    def test_missing_data_dir_fails_cleanly(self):
        self.run_tool("inventory", "--data-dir", self.root / "missing",
                      "--output", self.root / "report.json", success=False)

    def test_cross_pack_override_is_reported_not_silently_chosen(self):
        with zipfile.ZipFile(self.data / "patch.pk3", "w") as pack:
            pack.writestr("default.cfg", b"changed")
        target = self.root / "inventory.json"
        self.run_tool("inventory", "--data-dir", self.data, "--output", target)
        report = json.loads(target.read_text())
        self.assertEqual(report["cross_pack_paths"]["default.cfg"], ["fixture.pk3", "patch.pk3"])


    def test_external_license_notice_is_hashed_and_packaged(self):
        notice = self.root / "COPYING.txt"
        notice.write_bytes(b"Generated external license notice")
        self.selection["notices"] = [{"file": "COPYING.txt", "path": "licenses/copying.txt",
                                      "sha256": digest(notice.read_bytes()), "origin": "fixture"}]
        for asset in self.selection["assets"]:
            asset["notice"] = "licenses/copying.txt"
        self.stage()
        with zipfile.ZipFile(self.root / "out/data/xboxprep.pk3") as pack:
            self.assertEqual(pack.read("licenses/copying.txt"), notice.read_bytes())
        manifest = json.loads((self.root / "out/manifest.json").read_text())
        self.assertEqual(manifest["notices"][0]["sha256"], digest(notice.read_bytes()))
        self.assertEqual(manifest["selected_bytes"], sum(map(len, self.entries.values())) + notice.stat().st_size)
        notice.write_bytes(b"changed")
        self.assertIn("notice hash mismatch", self.stage("changed", success=False).stderr)
        self.assertFalse((self.root / "changed").exists())

    def test_notice_path_and_size_are_checked(self):
        self.selection["notices"] = [{"file": "../outside", "path": "licenses/test.txt",
                                      "sha256": "0" * 64, "origin": "fixture"}]
        self.assertIn("invalid virtual path", self.stage(success=False).stderr)

    def test_source_symlink_is_rejected(self):
        original = self.root / "original.pk3"
        self.archive.rename(original)
        try:
            self.archive.symlink_to(original)
        except OSError as exc:
            self.skipTest(f"This platform cannot create symlinks: {exc}")
        self.assertIn("non-symlink", self.stage(success=False).stderr)

    def test_invalid_deflate_stream_has_no_traceback(self):
        self.write_pack({"file.txt": b"payload" * 10})
        payload = bytearray(self.archive.read_bytes())
        name_len, extra_len = struct.unpack_from("<HH", payload, 26)
        payload[30 + name_len + extra_len] = 0xFF
        self.archive.write_bytes(payload)
        self.run_tool("inventory", "--data-dir", self.data,
                      "--output", self.root / "corrupt.json", success=False)

    def test_invalid_limits_and_release_fail_cleanly(self):
        for value in (True, 0, -1, "1024", 2**31):
            with self.subTest(value=value):
                self.selection["max_asset_bytes"] = value
                self.assertIn("asset budget", self.stage(success=False).stderr)
        self.selection["max_asset_bytes"] = 1024
        self.selection["release"] = "nexuiz-commercial"
        self.assertIn("release", self.stage(success=False).stderr)

    def test_inventory_will_not_overwrite_source_archive(self):
        before = self.archive.read_bytes()
        self.run_tool("inventory", "--data-dir", self.data,
                      "--output", self.archive, success=False)
        self.assertEqual(self.archive.read_bytes(), before)

if __name__ == "__main__":
    unittest.main()
