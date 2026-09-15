from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class XboxWorkflowPinTests(unittest.TestCase):
    def test_workflow_reads_checkout_revision_from_the_canonical_pin_file(self) -> None:
        workflow = (ROOT / ".github/workflows/xbox-foundation.yml").read_text(
            encoding="utf-8"
        )
        pin = (ROOT / "xbox/nxdk.version").read_text(encoding="utf-8").strip()

        self.assertIn("id: nxdk-pin", workflow)
        self.assertIn('sha="$(cat xbox/nxdk.version)"', workflow)
        self.assertIn("ref: ${{ steps.nxdk-pin.outputs.sha }}", workflow)
        self.assertNotIn(
            f"ref: {pin}",
            workflow,
            "the workflow must not duplicate the canonical nxdk revision",
        )


if __name__ == "__main__":
    unittest.main()
