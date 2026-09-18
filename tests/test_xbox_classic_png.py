"""Exercise the Xbox PNG decoder against nxdk's pinned libpng and zlib."""

from pathlib import Path
import binascii
import os
import shlex
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib


ROOT = Path(__file__).resolve().parents[1]
PNG = ROOT / "deps" / "nxdk" / "lib" / "libpng" / "libpng"
ZLIB = ROOT / "deps" / "nxdk" / "lib" / "zlib" / "zlib"
PNG_SOURCES = [
    "png.c", "pngerror.c", "pngget.c", "pngmem.c", "pngpread.c",
    "pngread.c", "pngrio.c", "pngrtran.c", "pngrutil.c", "pngset.c",
    "pngtrans.c", "pngwio.c", "pngwrite.c", "pngwtran.c", "pngwutil.c",
]
ZLIB_SOURCES = [
    "adler32.c", "crc32.c", "deflate.c", "infback.c", "inffast.c",
    "inflate.c", "inftrees.c", "trees.c", "zutil.c",
]


def chunk(kind, payload):
    crc = binascii.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)


def png(width, height, depth, color_type, raw, *, interlace=0, extra=()):
    ihdr = struct.pack(">IIBBBBB", width, height, depth, color_type, 0, 0, interlace)
    body = b"".join(chunk(kind, payload) for kind, payload in extra)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + body
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


HARNESS = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <xbox_png.h>

static unsigned char *ReadFile(const char *path, size_t *size)
{
    FILE *file = fopen(path, "rb");
    unsigned char *data;
    long length;
    assert(file != NULL);
    assert(fseek(file, 0, SEEK_END) == 0);
    length = ftell(file);
    assert(length >= 0);
    assert(fseek(file, 0, SEEK_SET) == 0);
    data = malloc((size_t)length);
    assert(data != NULL);
    assert(fread(data, 1, (size_t)length, file) == (size_t)length);
    fclose(file);
    *size = (size_t)length;
    return data;
}

static void *Allocate(void *opaque, size_t size)
{
    int *live = opaque;
    ++*live;
    return malloc(size);
}

static void Release(void *opaque, void *address)
{
    int *live = opaque;
    if (address != NULL)
    {
        --*live;
        free(address);
    }
}

static void Check(const char *path, unsigned int width, unsigned int height,
    const unsigned char *expected, size_t expected_size)
{
    xbox_png_image_t image = {0};
    unsigned char *data;
    size_t size;
    char error[160] = {0};
    int live = 0;
    data = ReadFile(path, &size);
    assert(Xbox_PngDecodeBGRA(data, size, Allocate, Release, &live,
        &image, error, sizeof(error)));
    assert(image.width == width);
    assert(image.height == height);
    assert(image.size == expected_size);
    if (memcmp(image.pixels, expected, expected_size) != 0)
    {
        size_t index;
        fprintf(stderr, "pixel mismatch in %s\nactual: ", path);
        for (index = 0; index < expected_size; ++index)
            fprintf(stderr, "%u ", image.pixels[index]);
        fprintf(stderr, "\nexpected: ");
        for (index = 0; index < expected_size; ++index)
            fprintf(stderr, "%u ", expected[index]);
        fprintf(stderr, "\n");
        abort();
    }
    assert(live == 1);
    Release(&live, image.pixels);
    assert(live == 0);
    free(data);
}

static void Reject(const char *path)
{
    xbox_png_image_t image = {0};
    unsigned char *data;
    size_t size;
    char error[160] = {0};
    int live = 0;
    data = ReadFile(path, &size);
    assert(!Xbox_PngDecodeBGRA(data, size, Allocate, Release, &live,
        &image, error, sizeof(error)));
    assert(image.pixels == NULL);
    assert(error[0] != '\0');
    assert(live == 0);
    free(data);
}

int main(int argc, char **argv)
{
    static const unsigned char rgb[] = {0, 0, 255, 255, 0, 255, 0, 255};
    static const unsigned char rgba[] = {255, 0, 0, 40, 30, 20, 10, 50};
    static const unsigned char palette[] = {0, 0, 255, 128, 255, 0, 0, 255};
    static const unsigned char adam7[] = {
        0, 0, 255, 255, 0, 255, 0, 255,
        255, 0, 0, 255, 255, 255, 255, 255
    };
    assert(argc == 7);
    Check(argv[1], 2, 1, rgb, sizeof(rgb));
    Check(argv[2], 2, 1, rgba, sizeof(rgba));
    Check(argv[3], 2, 1, palette, sizeof(palette));
    Check(argv[4], 2, 2, adam7, sizeof(adam7));
    Reject(argv[5]);
    Reject(argv[6]);
    return 0;
}
'''


class ClassicPngTests(unittest.TestCase):
    def test_typed_decoder_handles_formats_interlace_and_errors(self):
        compiler = shlex.split(os.environ.get("CC", "cc"))
        self.assertTrue(compiler and shutil.which(compiler[0]), "A host C compiler is required")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            fixtures = [
                png(2, 1, 8, 2, b"\0\xff\0\0\0\xff\0"),
                png(2, 1, 8, 6, b"\0\0\0\xff\x28\x0a\x14\x1e\x32"),
                png(2, 1, 8, 3, b"\0\0\1", extra=(
                    (b"PLTE", b"\xff\0\0\0\0\xff"),
                    (b"tRNS", b"\x80\xff"),
                )),
                # Adam7 pass rows: p00, p10, then p01+p11.
                png(2, 2, 8, 2,
                    b"\0\xff\0\0" + b"\0\0\xff\0" +
                    b"\0\0\0\xff\xff\xff\xff", interlace=1),
            ]
            paths = []
            for index, data in enumerate(fixtures):
                path = temp / f"valid-{index}.png"
                path.write_bytes(data)
                paths.append(path)
            invalid = temp / "invalid.png"
            invalid.write_bytes(b"not a png")
            truncated = temp / "truncated.png"
            truncated.write_bytes(fixtures[0][:-7])
            harness = temp / "harness.c"
            executable = temp / "png-decoder-test"
            harness.write_text(HARNESS, encoding="utf-8")
            build = subprocess.run(
                [
                    *compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-Wno-error=maybe-uninitialized",
                    "-DZ_SOLO", "-I", str(PNG),
                    "-I", str(PNG.parent), "-I", str(ZLIB),
                    "-I", str(ROOT / "xbox" / "classic" / "include"),
                    str(ROOT / "xbox" / "classic" / "png_decode_xbox.c"),
                    *[str(PNG / source) for source in PNG_SOURCES],
                    *[str(ZLIB / source) for source in ZLIB_SOURCES],
                    str(harness), "-o", str(executable),
                ], capture_output=True, text=True, timeout=90,
            )
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run(
                [str(executable), *map(str, paths), str(invalid), str(truncated)],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
