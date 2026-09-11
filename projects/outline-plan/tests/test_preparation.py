"""Consistency checks for preparation examples, not P1 product or model tests."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

def read(name):
    return json.loads((ROOT / "preparation" / name).read_text(encoding="utf-8"))

class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.p = read("defaults.example.json")
        self.e = read("experiments.example.json")

    def test_defaults_do_not_claim_approval_or_site_dimensions(self):
        self.assertFalse(self.p["user_confirmed"])
        self.assertIsNone(self.p["geometry_dimensions_m"])
        self.assertEqual(self.p["engineering_compliance"], "NOT_CHECKED")

    def test_floor_count_and_unique_ids(self):
        self.assertEqual(self.p["floor_count"], len(self.p["floors"]))
        self.assertEqual(len({f["floor_id"] for f in self.p["floors"]}), self.p["floor_count"])

    def test_building_counts_are_not_per_floor_duplicates(self):
        for key in ("office_workstations", "racks", "machine_rooms", "meeting_rooms", "meeting_seats", "control_seats"):
            self.assertEqual(sum(f[key] for f in self.p["floors"]), self.p["totals"][key], key)
        self.assertEqual(sum(f["office_rooms"] for f in self.p["floors"]), self.p["totals"]["offices"])

    def test_rack_groups_match_every_floor(self):
        groups = self.p["rack_groups"]
        self.assertEqual(len({g["room_id"] for g in groups}), len(groups))
        for f in self.p["floors"]:
            row = [g for g in groups if g["floor_id"] == f["floor_id"]]
            self.assertEqual(len(row), f["machine_rooms"])
            self.assertEqual(sum(g["racks"] for g in row), f["racks"])

    def test_office_groups_match_every_floor(self):
        for f in self.p["floors"]:
            row = [g for g in self.p["office_groups"] if g["floor_id"] == f["floor_id"]]
            self.assertEqual(len(row), f["office_rooms"])
            self.assertEqual(sum(g["workstations"] for g in row), f["office_workstations"])

    def test_model_example_has_no_fake_scores(self):
        self.assertEqual(self.e["status"], "NOT_RUN")
        self.assertIsNone(self.e["metrics"])
        self.assertEqual(self.e["outputs"], [])
        self.assertIsNone(self.e["input_snapshot_id"])

    def test_render_only_freezes_geometry(self):
        for profile in self.e["profiles"]:
            if profile["mode"] == "render_only":
                self.assertEqual(profile["planner"], "frozen_layout")
        self.assertTrue(self.e["requires_frozen_input"])

    def test_attempt_count_and_serial_policy(self):
        expected = len(self.e["render_comparison_profile_ids"]) * len(self.e["seeds"]) * len(self.e["floor_ids"])
        self.assertEqual(expected, self.e["render_comparison_attempts_if_all_compatible"])
        self.assertEqual(self.e["concurrency"], 1)
        self.assertEqual(self.e["batch_size"], 1)
        self.assertEqual(self.e["network_policy"], "LOCAL_ONLY")

    def test_preparation_documents_exist(self):
        for name in ("P1_DEVELOPMENT_SPEC.md", "MODELS_PREPARATION.md"):
            self.assertTrue((ROOT / "docs" / name).is_file())

    def test_task_dependencies_are_complete_and_acyclic(self):
        tasks = read("task_plan.json")["tasks"]
        by_id = {t["id"]: t for t in tasks}
        self.assertEqual(len(tasks), len(by_id))
        def visit(key, stack):
            self.assertIn(key, by_id)
            self.assertNotIn(key, stack)
            for dep in by_id[key]["depends_on"]:
                visit(dep, stack | {key})
        for task in tasks:
            self.assertIn(task["status"], {"REVIEW", "TODO"})
            visit(task["id"], set())

if __name__ == "__main__":
    unittest.main()
