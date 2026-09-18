import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "xbox"
sys.path.insert(0, str(TOOLS))

import build_lowmem_texture_pack as lowmem  # noqa: E402


def tga(width, height, mode, pixels, *, rle=False, top=True, right=False):
    depths = {"L": 8, "RGB": 24, "RGBA": 32}
    image_type = (11 if mode == "L" else 10) if rle else (3 if mode == "L" else 2)
    descriptor = (0x20 if top else 0) | (0x10 if right else 0) | (8 if mode == "RGBA" else 0)
    header = bytearray(18)
    header[2] = image_type
    header[12:14] = width.to_bytes(2, "little")
    header[14:16] = height.to_bytes(2, "little")
    header[16] = depths[mode]
    header[17] = descriptor
    channels = depths[mode] // 8

    ordered = []
    for file_y in range(height):
        y = file_y if top else height - 1 - file_y
        for file_x in range(width):
            x = width - 1 - file_x if right else file_x
            pixel = pixels[(y * width + x) * channels:(y * width + x + 1) * channels]
            if mode in ("RGB", "RGBA"):
                pixel = bytes((pixel[2], pixel[1], pixel[0])) + pixel[3:]
            ordered.append(pixel)
    if not rle:
        return bytes(header) + b"".join(ordered)
    # A raw RLE packet is enough to exercise packet parsing without obscuring fixtures.
    return bytes(header) + bytes((len(ordered) - 1,)) + b"".join(ordered)


class TgaConversionTests(unittest.TestCase):
    def test_decodes_truecolor_grayscale_rle_and_orientation(self):
        rgb = bytes((255, 0, 0, 0, 255, 0, 0, 0, 255, 10, 20, 30))
        for rle in (False, True):
            for top, right in ((True, False), (False, True)):
                with self.subTest(rle=rle, top=top, right=right):
                    image = lowmem.decode_tga(tga(2, 2, "RGB", rgb, rle=rle, top=top, right=right))
                    self.assertEqual((image.width, image.height, image.mode), (2, 2, "RGB"))
                    self.assertEqual(image.pixels, rgb)
        gray = lowmem.decode_tga(tga(2, 1, "L", bytes((17, 231)), rle=True))
        self.assertEqual((gray.mode, gray.pixels), ("L", bytes((17, 231))))

    def test_half_scale_uses_premultiplied_alpha_and_bounds_odd_dimensions(self):
        # Three fully transparent colored pixels must not darken the sole opaque red pixel.
        pixels = bytes((
            255, 0, 0, 255,   0, 255, 0, 0,
            0, 0, 255, 0,     255, 255, 255, 0,
        ))
        reduced = lowmem.downscale_to_limit(lowmem.TgaImage(2, 2, "RGBA", pixels), 1)
        self.assertEqual((reduced.width, reduced.height), (1, 1))
        self.assertEqual(reduced.pixels, bytes((255, 0, 0, 64)))

        odd = lowmem.downscale_to_limit(
            lowmem.TgaImage(1025, 513, "L", bytes([9]) * (1025 * 513)), 512
        )
        self.assertEqual((odd.width, odd.height), (257, 129))
        self.assertEqual(set(odd.pixels), {9})

    def test_encoding_is_canonical_top_left_uncompressed_tga(self):
        source = lowmem.TgaImage(2, 1, "RGBA", bytes((1, 2, 3, 4, 5, 6, 7, 8)))
        encoded = lowmem.encode_tga(source)
        self.assertEqual(encoded[2], 2)
        self.assertEqual(encoded[16:18], bytes((32, 0x28)))
        self.assertEqual(lowmem.decode_tga(encoded), source)

    def test_rejects_unsupported_or_truncated_input(self):
        unsupported = bytearray(tga(1, 1, "RGB", bytes((1, 2, 3))))
        unsupported[1] = 1
        truncated = tga(2, 1, "RGB", bytes((1, 2, 3, 4, 5, 6)))[:-3]
        for payload in (b"", bytes(unsupported), truncated):
            with self.subTest(length=len(payload)):
                with self.assertRaises(lowmem.TexturePackError):
                    lowmem.decode_tga(payload)


class PackBuilderTests(unittest.TestCase):
    def write_pack(self, path, entries):
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as zf:
            for name, payload in entries.items():
                zf.writestr(name, payload)

    def test_builds_deterministic_stored_override_from_effective_large_assets(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = root / "a.pk3"
            second = root / "b.pk3"
            old = tga(1024, 1, "RGB", bytes((10, 0, 0)) * 1024)
            effective = tga(1024, 1, "RGB", bytes((20, 0, 0)) * 1024)
            small = tga(2, 2, "RGB", bytes((1, 2, 3)) * 4)
            self.write_pack(first, {"textures/large.tga": old, "textures/small.tga": small})
            self.write_pack(second, {"textures/large.tga": effective})

            output_a = root / "one.pk3"
            output_b = root / "two.pk3"
            manifest_a = lowmem.build_pack([first, second], output_a, max_dimension=512)
            manifest_b = lowmem.build_pack([first, second], output_b, max_dimension=512)

            self.assertEqual(output_a.read_bytes(), output_b.read_bytes())
            self.assertEqual(manifest_a, manifest_b)
            self.assertEqual(manifest_a["asset_count"], 1)
            asset = manifest_a["assets"][0]
            self.assertEqual(asset["path"], "textures/large.tga")
            self.assertEqual(asset["source_pack"], "b.pk3")
            self.assertEqual(asset["source_sha256"], hashlib.sha256(effective).hexdigest())
            self.assertEqual(asset["source_dimensions"], [1024, 1])
            self.assertEqual(asset["output_dimensions"], [512, 1])

            with zipfile.ZipFile(output_a) as zf:
                self.assertEqual(zf.namelist(), ["textures/large.tga", "xbox-lowmem-manifest.json"])
                self.assertNotIn("textures/small.tga", zf.namelist())
                for info in zf.infolist():
                    self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                    self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                converted = zf.read("textures/large.tga")
                self.assertEqual(lowmem.decode_tga(converted).pixels[:3], bytes((20, 0, 0)))
                embedded = json.loads(zf.read("xbox-lowmem-manifest.json"))
                self.assertEqual(embedded, manifest_a)

    def test_unsupported_oversized_tga_fails_instead_of_being_omitted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pack = root / "input.pk3"
            bad = bytearray(tga(513, 1, "RGB", bytes((1, 2, 3)) * 513))
            bad[2] = 1
            self.write_pack(pack, {"textures/bad.tga": bytes(bad)})
            with self.assertRaises(lowmem.TexturePackError):
                lowmem.build_pack([pack], root / "output.pk3", max_dimension=512)


if __name__ == "__main__":
    unittest.main()
