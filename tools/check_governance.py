#!/usr/bin/env python3
"""Validate development records only; never claim model or engineering acceptance."""
from pathlib import Path
import hashlib
import json
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def validate_contract(kind, value):
    schema = load("contracts/pipeline.schema.json")
    schema["$ref"] = "#/$defs/" + kind
    Draft202012Validator(schema).validate(value)

def check():
    errors = []
    schema = load("contracts/pipeline.schema.json")
    Draft202012Validator.check_schema(schema)
    for kind in ("FootprintSpec", "PlanRevision", "EditRequest"):
        validate_contract(kind, load("contracts/fixtures/" + kind + ".json"))
    validate_contract("BenchmarkRun", load("benchmarks/run.example.json"))
    projects = [load("projects/" + x + "/project.json") for x in ("outline-plan", "region-edit", "plan-delivery")]
    assert {x["id"] for x in projects} == {"P1", "P2", "P3"}
    assert all(x["contract_version"] == "0.1.0" for x in projects)
    tasks = load("governance/backlog.json")["tasks"]
    by_id = {t["id"]: t for t in tasks}
    assert len(by_id) == len(tasks), "Duplicate task ID"
    def visit(key, stack):
        assert key in by_id, "Missing dependency: " + key
        assert key not in stack, "Dependency cycle: " + key
        for dep in by_id[key]["depends_on"]:
            visit(dep, stack | {key})
    for task in tasks:
        visit(task["id"], set())
        assert task["status"] in {"TODO", "READY", "IN_PROGRESS", "BLOCKED", "REVIEW", "DONE", "DEFERRED"}
        assert task["acceptance"] and task["owner_role"]
        if task["status"] in {"READY", "IN_PROGRESS", "DONE"}:
            assert all(by_id[d]["status"] == "DONE" for d in task["depends_on"]), "Unmet task dependency"
        if task["status"] == "DONE":
            assert task["evidence"], "DONE without evidence"
            for p in task["evidence"]:
                assert (ROOT / p).is_file(), "Missing evidence file"
    registry = load("benchmarks/models.json")
    models = {m["id"]:m for m in registry["models"]}
    assert len(models) == len(registry["models"]), "Duplicate model ID"
    for project, row in load("benchmarks/matrix.json")["projects"].items():
        for key in row["candidate_ids"]:
            assert key in models and project in models[key]["projects"], "Incompatible registry entry"
    imported = load("projects/plan-delivery/IMPORT.json")
    vendor = ROOT / "projects/plan-delivery/vendor"
    blocked = imported.get("blocked_files", {})
    for relative, spec in imported["files"].items():
        path = vendor / relative
        if relative in blocked:
            assert not path.exists(), "Resolved file requires clearing the recorded blocker"
            assert blocked[relative]["expected_sha256"] == spec["sha256"]
            continue
        assert path.is_file(), "Missing original Skill file: " + relative
        data = path.read_bytes()
        assert len(data) == spec["bytes"] and hashlib.sha256(data).hexdigest() == spec["sha256"], "Changed vendor: " + relative
    print(json.dumps({"status":"PASS", "scope":"governance, schemas, registry, source integrity only", "tasks":len(tasks), "models":len(models), "model_inference_executed":False, "vendor_import_complete":not bool(blocked), "blocked_vendor_files":list(blocked)}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(check())
