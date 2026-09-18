"""Exercise deferred nxdk socket startup without requiring the Xbox network stack."""

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
#include "xbox_network_gate.h"

int main(void)
{
    xbox_network_gate_t gate;

    Xbox_NetworkGateInit(&gate);
    assert(Xbox_NetworkGateCanOpen(&gate, XBOX_NETWORK_STARTING) == 0);
    assert(Xbox_NetworkGateTakeReadyRetry(&gate, XBOX_NETWORK_STARTING) == 0);
    assert(Xbox_NetworkGateTakeReadyRetry(&gate, XBOX_NETWORK_READY) == 1);
    assert(Xbox_NetworkGateTakeReadyRetry(&gate, XBOX_NETWORK_READY) == 0);

    Xbox_NetworkGateInit(&gate);
    assert(Xbox_NetworkGateCanOpen(&gate, XBOX_NETWORK_READY) == 1);
    assert(Xbox_NetworkGateTakeReadyRetry(&gate, XBOX_NETWORK_READY) == 0);

    Xbox_NetworkGateInit(&gate);
    assert(Xbox_NetworkGateCanOpen(&gate, XBOX_NETWORK_FAILED) == 0);
    assert(Xbox_NetworkGateTakeReadyRetry(&gate, XBOX_NETWORK_FAILED) == 0);
    return 0;
}
'''


class ClassicNetworkGateTests(unittest.TestCase):
    def test_network_gate_defers_socket_and_retries_once_after_ready(self):
        compiler = shlex.split(os.environ.get("CC", "cc"))
        self.assertTrue(compiler and shutil.which(compiler[0]), "A host C compiler is required")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            harness = temp / "harness.c"
            executable = temp / "network-gate-test"
            harness.write_text(HARNESS, encoding="utf-8")
            build = subprocess.run(
                [
                    *compiler,
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-I",
                    str(ROOT / "xbox" / "classic" / "include"),
                    str(ROOT / "xbox" / "classic" / "network_gate_xbox.c"),
                    str(harness),
                    "-o",
                    str(executable),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(executable)], capture_output=True, text=True, timeout=5)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
