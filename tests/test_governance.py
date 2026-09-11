"""Negative contract tests are not layout, image-editing, or model tests."""
import copy
import importlib.util
from pathlib import Path
import pytest
from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("governance_check", ROOT / "tools/check_governance.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

def test_repository_records():
    assert g.check() == 0

@pytest.mark.parametrize("kind", ["FootprintSpec", "PlanRevision", "EditRequest"])
def test_synthetic_fixtures_are_explicit(kind):
    assert g.load("contracts/fixtures/" + kind + ".json")["test_only"] is True

@pytest.mark.parametrize("kind", ["FootprintSpec", "PlanRevision", "EditRequest", "BenchmarkRun"])
def test_empty_contract_is_rejected(kind):
    with pytest.raises(ValidationError):
        g.validate_contract(kind, {})

def test_unknown_scale_unit_is_rejected():
    d = g.load("contracts/fixtures/FootprintSpec.json")
    d["world_unit"] = "diagram_units"
    with pytest.raises(ValidationError): g.validate_contract("FootprintSpec", d)

def test_current_geometry_cannot_be_null():
    d = g.load("contracts/fixtures/PlanRevision.json")
    d["geometry"] = None
    with pytest.raises(ValidationError): g.validate_contract("PlanRevision", d)

def test_stale_geometry_can_be_reported_not_hidden():
    d = g.load("contracts/fixtures/PlanRevision.json")
    d["geometry"] = None; d["geometry_status"] = "STALE"
    g.validate_contract("PlanRevision", d)

def test_empty_edit_instruction_rejected():
    d = g.load("contracts/fixtures/EditRequest.json")
    d["instruction"] = ""
    with pytest.raises(ValidationError): g.validate_contract("EditRequest", d)

def test_not_run_cannot_have_scores():
    d = g.load("benchmarks/run.example.json")
    d["metrics"] = {"score": 1.0}
    with pytest.raises(ValidationError): g.validate_contract("BenchmarkRun", d)

def test_success_requires_real_result_reference():
    d = g.load("benchmarks/run.example.json")
    d["execution_status"] = "SUCCEEDED"
    with pytest.raises(ValidationError): g.validate_contract("BenchmarkRun", d)

def test_agent_cannot_skip_from_intake_to_delivery():
    sm = g.load("agent/states.json")
    assert "delivered" not in sm["transitions"]["intake"]
    assert sm["guards"]["delivered"]
    assert sm["implementation"] == "DESIGN_ONLY"

def test_model_registry_does_not_invent_experiments():
    assert all(m["execution_status"] == "NOT_RUN" for m in g.load("benchmarks/models.json")["models"])
