#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build a deterministic low-memory TGA override PK3 for the Xbox release."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import zipfile

MAX_SOURCE_BYTES = 64 * 1024 * 1024
MANIFEST_NAME = "xbox-lowmem-manifest.json"
ZIP_TIME = (1980, 1, 1, 0, 0, 0)


class TexturePackError(ValueError):
    """A source texture or PK3 cannot be converted safely."""


@dataclass(frozen=True)
class TgaImage:
    width: int
    height: int
    mode: str
    pixels: bytes

    def __post_init__(self) -> None:
        channels = {"L": 1, "RGB": 3, "RGBA": 4}.get(self.mode)
        if channels is None:
            raise TexturePackError(f"unsupported pixel mode: {self.mode}")
        if self.width <= 0 or self.height <= 0:
            raise TexturePackError("TGA dimensions must be positive")
        if len(self.pixels) != self.width * self.height * channels:
            raise TexturePackError("pixel buffer does not match TGA dimensions")


def _read_tga_pixels(data: bytes, offset: int, count: int, channels: int, rle: bool) -> list[bytes]:
    result: list[bytes] = []
    if not rle:
        end = offset + count * channels
        if end > len(data):
            raise TexturePackError("truncated TGA pixel data")
        return [data[pos:pos + channels] for pos in range(offset, end, channels)]
    while len(result) < count:
        if offset >= len(data):
            raise TexturePackError("truncated TGA RLE packet")
        packet = data[offset]
        offset += 1
        length = (packet & 0x7F) + 1
        if len(result) + length > count:
            raise TexturePackError("TGA RLE packet exceeds image dimensions")
        if packet & 0x80:
            if offset + channels > len(data):
                raise TexturePackError("truncated TGA RLE pixel")
            pixel = data[offset:offset + channels]
            offset += channels
            result.extend([pixel] * length)
        else:
            end = offset + length * channels
            if end > len(data):
                raise TexturePackError("truncated TGA raw packet")
            result.extend(data[pos:pos + channels] for pos in range(offset, end, channels))
            offset = end
    return result


def decode_tga(data: bytes) -> TgaImage:
    if len(data) < 18:
        raise TexturePackError("truncated TGA header")
    id_length, color_map_type, image_type = data[0], data[1], data[2]
    width = int.from_bytes(data[12:14], "little")
    height = int.from_bytes(data[14:16], "little")
    depth, descriptor = data[16], data[17]
    if color_map_type != 0:
        raise TexturePackError("color-mapped TGA is not supported by the low-memory converter")
    formats = {
        (2, 24): ("RGB", 3, False),
        (2, 32): ("RGBA", 4, False),
        (3, 8): ("L", 1, False),
        (10, 24): ("RGB", 3, True),
        (10, 32): ("RGBA", 4, True),
        (11, 8): ("L", 1, True),
    }
    try:
        mode, channels, rle = formats[(image_type, depth)]
    except KeyError as exc:
        raise TexturePackError(f"unsupported TGA type/depth: {image_type}/{depth}") from exc
    if width <= 0 or height <= 0 or descriptor & 0xC0:
        raise TexturePackError("invalid TGA dimensions or interleave mode")
    offset = 18 + id_length
    if offset > len(data):
        raise TexturePackError("truncated TGA image identifier")
    file_pixels = _read_tga_pixels(data, offset, width * height, channels, rle)
    top_origin = bool(descriptor & 0x20)
    right_origin = bool(descriptor & 0x10)
    output = bytearray(width * height * channels)
    for file_index, pixel in enumerate(file_pixels):
        file_y, file_x = divmod(file_index, width)
        y = file_y if top_origin else height - 1 - file_y
        x = width - 1 - file_x if right_origin else file_x
        if mode in ("RGB", "RGBA"):
            pixel = bytes((pixel[2], pixel[1], pixel[0])) + pixel[3:]
        target = (y * width + x) * channels
        output[target:target + channels] = pixel
    return TgaImage(width, height, mode, bytes(output))


def _half_scale(image: TgaImage) -> TgaImage:
    channels = {"L": 1, "RGB": 3, "RGBA": 4}[image.mode]
    new_width = (image.width + 1) // 2
    new_height = (image.height + 1) // 2
    output = bytearray(new_width * new_height * channels)
    for out_y in range(new_height):
        for out_x in range(new_width):
            samples: list[bytes] = []
            for y in range(out_y * 2, min(out_y * 2 + 2, image.height)):
                for x in range(out_x * 2, min(out_x * 2 + 2, image.width)):
                    start = (y * image.width + x) * channels
                    samples.append(image.pixels[start:start + channels])
            if image.mode == "RGBA":
                alpha_sum = sum(pixel[3] for pixel in samples)
                alpha = (alpha_sum + len(samples) // 2) // len(samples)
                if alpha_sum:
                    color = [
                        (sum(pixel[c] * pixel[3] for pixel in samples) + alpha_sum // 2) // alpha_sum
                        for c in range(3)
                    ]
                else:
                    color = [0, 0, 0]
                pixel_out = bytes((*color, alpha))
            else:
                pixel_out = bytes(
                    (sum(pixel[c] for pixel in samples) + len(samples) // 2) // len(samples)
                    for c in range(channels)
                )
            target = (out_y * new_width + out_x) * channels
            output[target:target + channels] = pixel_out
    return TgaImage(new_width, new_height, image.mode, bytes(output))


def downscale_to_limit(image: TgaImage, max_dimension: int) -> TgaImage:
    if max_dimension <= 0:
        raise TexturePackError("maximum dimension must be positive")
    while image.width > max_dimension or image.height > max_dimension:
        image = _half_scale(image)
    return image


def encode_tga(image: TgaImage) -> bytes:
    depth = {"L": 8, "RGB": 24, "RGBA": 32}[image.mode]
    header = bytearray(18)
    header[2] = 3 if image.mode == "L" else 2
    header[12:14] = image.width.to_bytes(2, "little")
    header[14:16] = image.height.to_bytes(2, "little")
    header[16] = depth
    header[17] = 0x20 | (8 if image.mode == "RGBA" else 0)
    if image.mode == "L":
        body = image.pixels
    else:
        channels = depth // 8
        converted = bytearray(len(image.pixels))
        for pos in range(0, len(image.pixels), channels):
            pixel = image.pixels[pos:pos + channels]
            converted[pos:pos + channels] = bytes((pixel[2], pixel[1], pixel[0])) + pixel[3:]
        body = bytes(converted)
    return bytes(header) + body


def _safe_virtual_path(name: str) -> str:
    if not name or "\\" in name or "\x00" in name:
        raise TexturePackError(f"unsafe PK3 path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise TexturePackError(f"unsafe PK3 path: {name!r}")
    return path.as_posix()


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, ZIP_TIME)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_pack(pk3_paths: list[Path], output_path: Path, max_dimension: int = 512) -> dict:
    if not pk3_paths:
        raise TexturePackError("at least one source PK3 is required")
    effective: dict[str, tuple[str, Path, str, int, int, int]] = {}
    for raw_path in pk3_paths:
        pack_path = Path(raw_path)
        try:
            with zipfile.ZipFile(pack_path) as zf:
                seen: set[str] = set()
                for info in zf.infolist():
                    if info.is_dir() or not info.filename.casefold().endswith(".tga"):
                        continue
                    name = _safe_virtual_path(info.filename)
                    folded = name.casefold()
                    if folded in seen:
                        raise TexturePackError(f"case/duplicate TGA collision in {pack_path.name}: {name}")
                    seen.add(folded)
                    if info.file_size < 18 or info.file_size > MAX_SOURCE_BYTES:
                        raise TexturePackError(f"TGA source size is unsafe: {pack_path.name}:{name}")
                    try:
                        with zf.open(info) as stream:
                            header = stream.read(18)
                    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                        raise TexturePackError(
                            f"cannot read TGA header {pack_path.name}:{name}: {exc}"
                        ) from exc
                    if len(header) != 18:
                        raise TexturePackError(f"truncated TGA header: {pack_path.name}:{name}")
                    width = int.from_bytes(header[12:14], "little")
                    height = int.from_bytes(header[14:16], "little")
                    effective[folded] = (
                        name, pack_path, info.filename, info.file_size, width, height
                    )
        except (OSError, zipfile.BadZipFile) as exc:
            raise TexturePackError(f"cannot inspect source PK3 {pack_path}: {exc}") from exc

    assets: list[tuple[str, bytes, dict]] = []
    for name, pack_path, member, declared_size, width, height in sorted(
        effective.values(), key=lambda item: item[0].casefold()
    ):
        if width <= max_dimension and height <= max_dimension:
            continue
        try:
            with zipfile.ZipFile(pack_path) as zf:
                source = zf.read(member)
        except (OSError, KeyError, zipfile.BadZipFile, RuntimeError) as exc:
            raise TexturePackError(f"cannot read source TGA {pack_path.name}:{name}: {exc}") from exc
        if len(source) != declared_size:
            raise TexturePackError(f"source TGA size changed while reading: {pack_path.name}:{name}")
        try:
            image = decode_tga(source)
        except TexturePackError as exc:
            raise TexturePackError(f"cannot convert oversized {pack_path.name}:{name}: {exc}") from exc
        converted_image = downscale_to_limit(image, max_dimension)
        converted = encode_tga(converted_image)
        record = {
            "path": name,
            "source_pack": pack_path.name,
            "source_bytes": len(source),
            "source_sha256": _sha256(source),
            "source_dimensions": [image.width, image.height],
            "output_bytes": len(converted),
            "output_sha256": _sha256(converted),
            "output_dimensions": [converted_image.width, converted_image.height],
            "mode": converted_image.mode,
        }
        assets.append((name, converted, record))

    manifest = {
        "schema_version": 1,
        "profile": "stock64",
        "max_dimension": max_dimension,
        "filter": "repeated-2x2-box-premultiplied-alpha",
        "entry_storage": "stored",
        "asset_count": len(assets),
        "assets": [record for _, _, record in assets],
    }
    manifest_bytes = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.tmp-{os.getpid()}")
    try:
        with zipfile.ZipFile(temporary, "w", allowZip64=True) as zf:
            for name, payload, _ in assets:
                zf.writestr(_zip_info(name), payload)
            zf.writestr(_zip_info(MANIFEST_NAME), manifest_bytes)
        os.replace(temporary, output_path)
    except (OSError, zipfile.BadZipFile) as exc:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise TexturePackError(f"cannot publish low-memory PK3: {exc}") from exc
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-dimension", type=int, default=512)
    parser.add_argument("pk3", nargs="+", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = build_pack(args.pk3, args.output, args.max_dimension)
    except TexturePackError as exc:
        print(f"low-memory texture pack error: {exc}", file=sys.stderr)
        return 2
    print(f"generated {args.output}: {manifest['asset_count']} downscaled TGA assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
