from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class XboxMakeScopedFlagsTests(unittest.TestCase):
    def test_strict_application_flags_do_not_modify_nxdk_library_builds(self) -> None:
        makefile = (ROOT / "xbox/Makefile").read_text(encoding="utf-8")

        self.assertIn("DP_XBOX_APP_CFLAGS :=", makefile)
        self.assertIn("APP_OBJS := $(SRCS:.c=.obj)", makefile)
        self.assertIn(
            "$(APP_OBJS): CFLAGS += $(DP_XBOX_APP_CFLAGS)",
            makefile,
            "strict warnings and port metadata must be target-specific to repository sources",
        )

        global_strict_flags = re.findall(
            r"^CFLAGS\s*\+=.*(?:-Wall|-Wextra|-Werror).*$",
            makefile,
            flags=re.MULTILINE,
        )
        self.assertEqual(
            [],
            global_strict_flags,
            "global strict flags leak into nxdk and third-party runtime sources",
        )


if __name__ == "__main__":
    unittest.main()
