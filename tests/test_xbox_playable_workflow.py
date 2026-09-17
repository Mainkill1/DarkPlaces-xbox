from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "xbox-playable.yml"


class XboxPlayableWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_does_not_depend_on_expiring_content_artifacts(self):
        for obsolete in (
            "35155351439",
            "nexuiz-part00",
            "nexuiz-part01",
            "nexuiz-part02",
            "actions/download-artifact",
        ):
            self.assertNotIn(obsolete, self.text)

    def test_uses_canonical_release_wrapper(self):
        self.assertIn("make -C xbox/release bootstrap", self.text)
        self.assertIn("make -C xbox/release all", self.text)
        self.assertIn("xbox/release/out/", self.text)

    def test_workflow_does_not_duplicate_dependency_commits(self):
        # Exact revisions belong to release-inputs.json/versions.mk, not YAML.
        self.assertNotIn("DP_CLASSIC_REV", self.text)
        self.assertNotIn("PBGL_REV", self.text)
        self.assertNotIn("OGG_REV", self.text)
        self.assertNotIn("VORBIS_REV", self.text)


if __name__ == "__main__":
    unittest.main()
