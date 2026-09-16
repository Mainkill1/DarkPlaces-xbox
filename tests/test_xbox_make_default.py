from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class XboxMakeDefaultGoalTests(unittest.TestCase):
    def test_default_goal_builds_artifacts_instead_of_only_verifying_nxdk(self) -> None:
        makefile = (ROOT / "xbox/Makefile").read_text(encoding="utf-8")
        declaration = ".DEFAULT_GOAL := all"
        self.assertIn(
            declaration,
            makefile,
            "xbox/Makefile must explicitly keep the nxdk 'all' target as the default",
        )
        self.assertLess(
            makefile.index(declaration),
            makefile.index("verify-nxdk:"),
            "the default goal must be selected before the verification target is declared",
        )


if __name__ == "__main__":
    unittest.main()
