import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "xbox" / "verify_release_tree.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("verify_release_tree", TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load verify_release_tree.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_disc(root: Path) -> Path:
    disc = root / "disc"
    data = disc / "data"
    data.mkdir(parents=True)
    files = {
        "data/data20091001.pk3": b"PK3!",
        "data/zzzz-xbox-lowmem.pk3": b"DERIVED!",
        "data/autoexec.cfg": b"exec xbox-defaults.cfg\n",
        "data/xbox-defaults.cfg": b"joy_enable 1\n",
    }
    manifest_files = []
    for relative, payload in files.items():
        path = disc / relative
        path.write_bytes(payload)
        manifest_files.append({
            "path": relative,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
    identity = {
        "schema_version": 3,
        "release": "nexuiz-xbox-2.5.2",
        "content_profile": "stock64",
        "source_file": "nexuiz-252.zip",
        "source_sha256": "a" * 64,
        "data_prefix": "Nexuiz/data/",
        "source_file_count": len(files),
        "staged_file_count": len(files),
        "staged_bytes": sum(len(v) for v in files.values()),
        "derived_content": {
            "path": "data/zzzz-xbox-lowmem.pk3",
            "profile": "stock64",
            "max_dimension": 256,
            "external_lightmap_dimension": 64,
            "filter": "repeated-2x2-box-premultiplied-alpha",
            "entry_storage": "stored",
            "asset_count": 121,
            "bytes": len(files["data/zzzz-xbox-lowmem.pk3"]),
            "sha256": hashlib.sha256(files["data/zzzz-xbox-lowmem.pk3"]).hexdigest(),
        },
        "files": sorted(manifest_files, key=lambda row: row["path"]),
    }
    content = json.dumps(identity, sort_keys=True, indent=2) + "\n"
    (disc / "CONTENT-IDENTITY.json").write_text(content, encoding="utf-8")
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    (disc / "BUILD-IDENTITY.txt").write_text(
        "release=nexuiz-xbox-2.5.2\ncontent_profile=stock64\n"
        "content_identity_sha256=" + content_hash + "\n",
        encoding="utf-8",
    )
    xbe = bytearray(b"XBEH" + b"\x00" * 4092)
    xbe[0x124:0x128] = (0x5).to_bytes(4, "little")
    (disc / "default.xbe").write_bytes(xbe)
    return disc


class XboxVerifyReleaseTreeTests(unittest.TestCase):
    def test_valid_tree_reconciles_manifest_and_xbe(self):
        tool = load_tool()
        with tempfile.TemporaryDirectory() as td:
            summary = tool.verify_tree(make_disc(Path(td)))
            self.assertEqual(summary["data_files"], 4)
            self.assertEqual(summary["pk3_files"], 2)

    def test_manifest_drift_is_rejected(self):
        tool = load_tool()
        with tempfile.TemporaryDirectory() as td:
            disc = make_disc(Path(td))
            (disc / "data" / "data20091001.pk3").write_bytes(b"changed")
            with self.assertRaises(tool.ReleaseTreeError):
                tool.verify_tree(disc)

    def test_derived_pack_identity_is_required_and_reconciled(self):
        tool = load_tool()
        with tempfile.TemporaryDirectory() as td:
            disc = make_disc(Path(td))
            identity_path = disc / "CONTENT-IDENTITY.json"
            identity = json.loads(identity_path.read_text(encoding="utf-8"))
            identity["derived_content"]["sha256"] = "0" * 64
            identity_path.write_text(
                json.dumps(identity, sort_keys=True, indent=2) + "\n", encoding="utf-8"
            )
            content_hash = hashlib.sha256(identity_path.read_bytes()).hexdigest()
            (disc / "BUILD-IDENTITY.txt").write_text(
                "release=nexuiz-xbox-2.5.2\ncontent_profile=stock64\n"
                "content_identity_sha256=" + content_hash + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(tool.ReleaseTreeError, "derived"):
                tool.verify_tree(disc)

    def test_dev128_tree_has_its_own_bounded_override(self):
        tool = load_tool()
        with tempfile.TemporaryDirectory() as td:
            disc = make_disc(Path(td))
            override = disc / "data" / "zzzz-xbox-lowmem.pk3"
            override.rename(disc / "data" / "zzzz-xbox-dev128.pk3")
            identity_path = disc / "CONTENT-IDENTITY.json"
            identity = json.loads(identity_path.read_text(encoding="utf-8"))
            identity["content_profile"] = "dev128"
            identity["derived_content"]["path"] = "data/zzzz-xbox-dev128.pk3"
            identity["derived_content"]["profile"] = "dev128"
            identity["derived_content"]["max_dimension"] = 512
            identity["derived_content"]["external_lightmap_dimension"] = 128
            for row in identity["files"]:
                if row["path"] == "data/zzzz-xbox-lowmem.pk3":
                    row["path"] = "data/zzzz-xbox-dev128.pk3"
            identity_path.write_text(
                json.dumps(identity, sort_keys=True, indent=2) + "\n", encoding="utf-8"
            )
            content_hash = hashlib.sha256(identity_path.read_bytes()).hexdigest()
            (disc / "BUILD-IDENTITY.txt").write_text(
                "release=nexuiz-xbox-2.5.2\ncontent_profile=dev128\n"
                "content_identity_sha256=" + content_hash + "\n",
                encoding="utf-8",
            )
            xbe = bytearray((disc / "default.xbe").read_bytes())
            xbe[0x124:0x128] = (0x1).to_bytes(4, "little")
            (disc / "default.xbe").write_bytes(xbe)
            summary = tool.verify_tree(disc)
            self.assertEqual(summary["data_files"], 4)
            self.assertEqual(summary["pk3_files"], 2)

    def test_dev128_rejects_xbe_with_64_mib_runtime_limit(self):
        tool = load_tool()
        with tempfile.TemporaryDirectory() as td:
            disc = make_disc(Path(td))
            identity_path = disc / "CONTENT-IDENTITY.json"
            identity = json.loads(identity_path.read_text(encoding="utf-8"))
            identity["content_profile"] = "dev128"
            identity["derived_content"]["path"] = "data/zzzz-xbox-dev128.pk3"
            identity["derived_content"]["profile"] = "dev128"
            identity["derived_content"]["max_dimension"] = 512
            identity["derived_content"]["external_lightmap_dimension"] = 128
            (disc / "data/zzzz-xbox-lowmem.pk3").rename(
                disc / "data/zzzz-xbox-dev128.pk3"
            )
            for row in identity["files"]:
                if row["path"] == "data/zzzz-xbox-lowmem.pk3":
                    row["path"] = "data/zzzz-xbox-dev128.pk3"
            identity_path.write_text(json.dumps(identity, sort_keys=True, indent=2) + "\n")
            content_hash = hashlib.sha256(identity_path.read_bytes()).hexdigest()
            (disc / "BUILD-IDENTITY.txt").write_text(
                "release=nexuiz-xbox-2.5.2\ncontent_profile=dev128\n"
                "content_identity_sha256=" + content_hash + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(tool.ReleaseTreeError, "64 MiB runtime limit"):
                tool.verify_tree(disc)


if __name__ == "__main__":
    unittest.main()
