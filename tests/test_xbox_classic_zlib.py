"""Exercise the Xbox adapter against nxdk's exact Z_SOLO zlib sources."""

from pathlib import Path
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ZLIB = ROOT / "deps" / "nxdk" / "lib" / "zlib" / "zlib"
ZLIB_SOURCES = [
    "adler32.c",
    "crc32.c",
    "deflate.c",
    "infback.c",
    "inffast.c",
    "inflate.c",
    "inftrees.c",
    "trees.c",
    "zutil.c",
]
HARNESS = r'''
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>
#include <xbox_zlib.h>

static voidpf CustomAlloc(voidpf opaque, uInt items, uInt size)
{
    int *calls = (int *)opaque;
    ++*calls;
    return calloc(items, size);
}

static void CustomFree(voidpf opaque, voidpf address)
{
    int *calls = (int *)opaque;
    ++*calls;
    free(address);
}

int main(void)
{
    static const unsigned char source[] = "classic Xbox raw deflate";
    unsigned char compressed[256];
    unsigned char restored[sizeof(source)];
    z_stream native_stream;
    z_stream stream;
    int custom_calls = 0;

    memset(&native_stream, 0, sizeof(native_stream));
    assert(inflateInit2_(&native_stream, -MAX_WBITS, "1.2.3", sizeof(native_stream)) == Z_STREAM_ERROR);

    memset(&stream, 0, sizeof(stream));
    stream.zalloc = CustomAlloc;
    stream.opaque = &custom_calls;
    assert(Xbox_ZlibInflateInit2_(&stream, -MAX_WBITS, "1.2.3", sizeof(stream)) == Z_STREAM_ERROR);
    assert(stream.zalloc == CustomAlloc);
    assert(stream.zfree == Z_NULL);

    memset(&stream, 0, sizeof(stream));
    stream.zalloc = CustomAlloc;
    stream.zfree = CustomFree;
    stream.opaque = &custom_calls;
    assert(Xbox_ZlibDeflateInit2_(&stream, Z_DEFAULT_COMPRESSION, Z_DEFLATED,
        -MAX_WBITS, 8, Z_DEFAULT_STRATEGY, "1.2.3", sizeof(stream)) == Z_OK);
    assert(stream.zalloc == CustomAlloc);
    assert(stream.zfree == CustomFree);
    stream.next_in = (Bytef *)source;
    stream.avail_in = sizeof(source);
    stream.next_out = compressed;
    stream.avail_out = sizeof(compressed);
    assert(deflate(&stream, Z_FINISH) == Z_STREAM_END);
    {
        uLong compressed_size = stream.total_out;
        assert(deflateEnd(&stream) == Z_OK);
        assert(custom_calls > 0);

        memset(&stream, 0, sizeof(stream));
        assert(Xbox_ZlibInflateInit2_(&stream, -MAX_WBITS, "1.2.3", sizeof(stream)) == Z_OK);
        assert(stream.zalloc != Z_NULL);
        assert(stream.zfree != Z_NULL);
        stream.next_in = compressed;
        stream.avail_in = (uInt)compressed_size;
        stream.next_out = restored;
        stream.avail_out = sizeof(restored);
        assert(inflate(&stream, Z_FINISH) == Z_STREAM_END);
        assert(stream.total_out == sizeof(source));
        assert(memcmp(restored, source, sizeof(source)) == 0);
        assert(inflateEnd(&stream) == Z_OK);
    }
    return 0;
}
'''


class ClassicZlibTests(unittest.TestCase):
    def test_adapter_satisfies_pinned_zsolo_allocator_contract(self):
        compiler = shlex.split(os.environ.get("CC", "cc"))
        self.assertTrue(compiler and shutil.which(compiler[0]), "A host C compiler is required")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            harness = temp / "harness.c"
            executable = temp / "zlib-adapter-test"
            harness.write_text(HARNESS, encoding="utf-8")
            build = subprocess.run(
                [
                    *compiler,
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-DZ_SOLO",
                    "-I",
                    str(ZLIB),
                    "-I",
                    str(ROOT / "xbox" / "classic" / "include"),
                    str(ROOT / "xbox" / "classic" / "zlib_xbox.c"),
                    *[str(ZLIB / source) for source in ZLIB_SOURCES],
                    str(harness),
                    "-o",
                    str(executable),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(executable)], capture_output=True, text=True, timeout=5)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
