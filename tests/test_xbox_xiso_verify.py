import hashlib
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "xbox" / "verify_xiso.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("verify_xiso", TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load verify_xiso.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def entry(name: str, sector: int, size: int, attrs: int = 0x80, left: int = 0, right: int = 0) -> bytes:
    raw = name.encode("ascii")
    record = struct.pack("<HHIIBB", left, right, sector, size, attrs, len(raw)) + raw
    return record + b"\xff" * ((-len(record)) & 3)


def write_at(image: bytearray, offset: int, payload: bytes) -> None:
    end = offset + len(payload)
    if end > len(image):
        image.extend(b"\x00" * (end - len(image)))
    image[offset:end] = payload


def build_fixture(path: Path, corrupt_payload: bool = False) -> tuple[Path, dict[str, bytes]]:
    sector = 2048
    image = bytearray(40 * sector)
    magic = b"MICROSOFT*XBOX*MEDIA"

    # Root table: default.xbe -> CONTENT-IDENTITY.json -> data.
    root_sector = 34
    root = bytearray(b"\xff" * sector)
    write_at(root, 0, entry("default.xbe", 36, 4096, right=8))
    write_at(root, 8 * 4, entry("CONTENT-IDENTITY.json", 38, 4, right=18))
    write_at(root, 18 * 4, entry("data", 35, sector, attrs=0x10))

    data = bytearray(b"\xff" * sector)
    pk3 = b"PK3!"
    write_at(data, 0, entry("data20091001.pk3", 39, len(pk3)))

    descriptor = bytearray(sector)
    descriptor[0:20] = magic
    descriptor[20:28] = struct.pack("<II", root_sector, sector)
    descriptor[0x7EC:0x800] = magic
    write_at(image, 32 * sector, descriptor)
    write_at(image, root_sector * sector, root)
    write_at(image, 35 * sector, data)
    xbe = bytearray(b"XBEH" + b"\x00" * 4092)
    xbe[0x124:0x128] = (0x1).to_bytes(4, "little")
    write_at(image, 36 * sector, xbe)
    write_at(image, 38 * sector, b"{}\n\n")
    write_at(image, 39 * sector, b"BAD!" if corrupt_payload else pk3)
    path.write_bytes(image)

    expected = {
        "CONTENT-IDENTITY.json": b"{}\n\n",
        "data/data20091001.pk3": pk3,
    }
    return path, expected


class XboxXisoVerifyTests(unittest.TestCase):
    def test_parser_finds_root_and_nested_files_and_hashes_payloads(self):
        tool = load_tool()
        with tempfile.TemporaryDirectory() as td:
            iso, expected = build_fixture(Path(td) / "test.iso")
            files = tool.read_xdvdfs(iso)
            self.assertEqual(files["default.xbe"].size, 4096)
            self.assertEqual(files["data/data20091001.pk3"].size, 4)
            for name, payload in expected.items():
                self.assertEqual(tool.hash_extent(iso, files[name]), hashlib.sha256(payload).hexdigest())

    def test_verify_rejects_changed_file_payload(self):
        tool = load_tool()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            iso, _ = build_fixture(root / "test.iso", corrupt_payload=True)
            disc = root / "disc"
            (disc / "data").mkdir(parents=True)
            xbe = bytearray(b"XBEH" + b"\x00" * 4092)
            xbe[0x124:0x128] = (0x1).to_bytes(4, "little")
            (disc / "default.xbe").write_bytes(xbe)
            (disc / "CONTENT-IDENTITY.json").write_bytes(b"{}\n\n")
            (disc / "data" / "data20091001.pk3").write_bytes(b"PK3!")
            with self.assertRaises(tool.XisoError):
                tool.verify_image(iso, disc)

    def test_verify_rejects_packaged_xbe_with_different_memory_flags(self):
        tool = load_tool()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            iso, _ = build_fixture(root / "test.iso")
            disc = root / "disc"
            (disc / "data").mkdir(parents=True)
            xbe = bytearray(b"XBEH" + b"\x00" * 4092)
            xbe[0x124:0x128] = (0x5).to_bytes(4, "little")
            (disc / "default.xbe").write_bytes(xbe)
            (disc / "CONTENT-IDENTITY.json").write_bytes(b"{}\n\n")
            (disc / "data" / "data20091001.pk3").write_bytes(b"PK3!")
            with self.assertRaisesRegex(tool.XisoError, "memory flags"):
                tool.verify_image(iso, disc)

    def test_verify_rejects_other_packaged_xbe_mutation(self):
        tool = load_tool()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            iso, _ = build_fixture(root / "test.iso")
            disc = root / "disc"
            (disc / "data").mkdir(parents=True)
            xbe = bytearray(b"XBEH" + b"\x00" * 4092)
            xbe[0x124:0x128] = (0x1).to_bytes(4, "little")
            (disc / "default.xbe").write_bytes(xbe)
            (disc / "CONTENT-IDENTITY.json").write_bytes(b"{}\n\n")
            (disc / "data" / "data20091001.pk3").write_bytes(b"PK3!")
            image = bytearray(iso.read_bytes())
            image[36 * 2048 + 0x200] = 0x7F
            iso.write_bytes(image)
            with self.assertRaisesRegex(tool.XisoError, "default.xbe payload"):
                tool.verify_image(iso, disc)

    def test_verify_accepts_only_extract_xiso_media_patch(self):
        tool = load_tool()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            iso, _ = build_fixture(root / "test.iso")
            disc = root / "disc"
            (disc / "data").mkdir(parents=True)
            xbe = bytearray(b"XBEH" + b"\x00" * 4092)
            xbe[0x124:0x128] = (0x1).to_bytes(4, "little")
            xbe[0x200:0x208] = b"\xe8\xca\xfd\xff\xff\x85\xc0\x7d"
            (disc / "default.xbe").write_bytes(xbe)
            (disc / "CONTENT-IDENTITY.json").write_bytes(b"{}\n\n")
            (disc / "data" / "data20091001.pk3").write_bytes(b"PK3!")
            image = bytearray(iso.read_bytes())
            image[36 * 2048 + 0x200:36 * 2048 + 0x208] = b"\xe8\xca\xfd\xff\xff\x85\xc0\xeb"
            iso.write_bytes(image)
            self.assertEqual(tool.verify_image(iso, disc)["files"], 3)


if __name__ == "__main__":
    unittest.main()
