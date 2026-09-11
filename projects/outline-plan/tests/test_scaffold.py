"""These tests do not load any model or produce building deliverables."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ScaffoldTest(unittest.TestCase):
    def test_capabilities_are_explicit(self):
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        r = subprocess.run([sys.executable, "-m", "autoplan_outline", "--capabilities"], env=env, capture_output=True, text=True, check=True)
        result = json.loads(r.stdout)
        self.assertEqual(result["project"], "P1")
        self.assertFalse(result["inference_implemented"])
        self.assertFalse(result["production_ready"])

    def test_project_manifest(self):
        value = json.loads((ROOT / "project.json").read_text())
        self.assertEqual(value["id"], "P1")
        self.assertFalse(value["model_inference_verified"])

if __name__ == "__main__":
    unittest.main()
