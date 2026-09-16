from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class XboxMakeToolPathTests(unittest.TestCase):
    def test_makefile_exports_pinned_nxdk_wrappers_before_including_sdk_rules(self) -> None:
        makefile = (ROOT / "xbox/Makefile").read_text(encoding="utf-8")
        path_export = "export PATH := $(NXDK_DIR)/bin:$(PATH)"
        include = "include $(NXDK_DIR)/Makefile"

        self.assertIn(
            path_export,
            makefile,
            "xbox/Makefile must expose nxdk-cc, nxdk-link, and related wrappers",
        )
        self.assertLess(
            makefile.index(path_export),
            makefile.index(include),
            "nxdk wrapper PATH must be exported before the SDK makefile is included",
        )


if __name__ == "__main__":
    unittest.main()
