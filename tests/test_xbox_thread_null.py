"""Compile and execute the real null-thread backend, not copied expressions."""
from pathlib import Path
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = r'''
#include <assert.h>
#include "thread.h"

int main(void)
{
    Thread_Atomic ref = {2};
    Thread_SpinLock lock = 0;
    assert(Thread_Init() == 0);
    assert(!Thread_HasThreads());
    assert(!Thread_AtomicDecRef(&ref));
    assert(Thread_AtomicGet(&ref) == 1);
    assert(Thread_AtomicDecRef(&ref));
    assert(Thread_AtomicGet(&ref) == 0);
    Thread_AtomicIncRef(&ref);
    assert(Thread_AtomicGet(&ref) == 1);
    assert(Thread_AtomicSet(&ref, 7) == 1);
    assert(Thread_AtomicAdd(&ref, 3) == 7);
    assert(Thread_AtomicGet(&ref) == 10);
    assert(Thread_AtomicAdd(&ref, -2) == 10);
    assert(Thread_AtomicGet(&ref) == 8);
    assert(Thread_AtomicTryLock(&lock));
    Thread_AtomicLock(&lock);
    Thread_AtomicUnlock(&lock);
    assert(Thread_CreateMutex() == NULL);
    assert(Thread_CreateCond() == NULL);
    assert(Thread_CreateThread(NULL, NULL) == NULL);
    assert(Thread_CreateBarrier(1) == NULL);
    assert(Thread_LockMutex(NULL) == -1);
    assert(Thread_CondWait(NULL, NULL) == -1);
    assert(Thread_WaitThread(NULL, 7) == 7);
    Thread_Shutdown();
    return 0;
}
'''


class NullThreadBackendTests(unittest.TestCase):
    def check_backend(self, defines):
        compiler = shlex.split(os.environ.get("CC", "cc"))
        self.assertTrue(compiler and shutil.which(compiler[0]), "A host C compiler is required")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            harness = root / "harness.c"
            harness.write_text(HARNESS, encoding="utf-8")
            executable = root / "thread-test"
            build = subprocess.run(
                [*compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter",
                 *defines, "-I", str(ROOT), str(ROOT / "thread_null.c"), str(harness),
                 "-o", str(executable)], capture_output=True, text=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(executable)], capture_output=True, text=True, timeout=5)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_reference_count_and_single_thread_contract(self):
        self.check_backend([])

    def test_xbox_feature_defines_do_not_add_desktop_dependencies(self):
        self.check_backend(["-DDP_PLATFORM_XBOX=1", "-DDP_SMALLMEMORY=1"])


if __name__ == "__main__":
    unittest.main()
