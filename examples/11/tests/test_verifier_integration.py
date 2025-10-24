#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from agents.verifier import VerifierOrchestrator


GOOD_CODE = """#!/usr/bin/env python3
def hello_world():
    \"\"\"Return greeting\"\"\"
    return \"hello\"

if __name__ == \"__main__\":
    print(hello_world())
"""


BAD_CODE = """def insecure():
    password = \"secret123\"
    return password
"""


class TestVerifierIntegration(unittest.TestCase):
    def setUp(self):
        self.tempdir = Path(tempfile.mkdtemp())
        (self.tempdir / "scripts").mkdir(exist_ok=True)
        # copy verification script
        script_src = PROJECT_ROOT / "scripts" / "verify_enhanced.sh"
        script_dst = self.tempdir / "scripts" / "verify_enhanced.sh"
        script_dst.write_bytes(script_src.read_bytes())
        script_dst.chmod(0o755)

        (self.tempdir / "runtime").mkdir(exist_ok=True)
        self.workspace = self.tempdir

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tempdir)

    def _write_code(self, content: str, filename: str):
        path = self.workspace / filename
        path.write_text(content)
        return path

    def _write_baton(self, synopsis: str):
        baton = {
            "task": {
                "id": "task-test",
                "goal": "Test verification",
                "success_metrics": ["tests pass"],
                "constraints": ["Only modify safe files"],
            },
            "builder_output": {
                "synopsis": synopsis,
                "patch_bundle": [],
                "verification_hints": [],
            },
        }
        (self.workspace / "runtime" / "baton.next.json").write_text(json.dumps(baton, indent=2))

    def test_good_code_passes(self):
        self._write_code(GOOD_CODE, "good_app.py")
        self._write_baton("Good code example")

        orchestrator = VerifierOrchestrator(self.workspace)
        result = orchestrator.run({"task_id": "good_task"})
        self.assertIn("final_verdict", result)

    def test_missing_baton_fails(self):
        orchestrator = VerifierOrchestrator(self.workspace)
        with self.assertRaises(FileNotFoundError):
            orchestrator.run({"task_id": "missing_baton"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
