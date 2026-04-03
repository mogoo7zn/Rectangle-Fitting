#!/usr/bin/env python3
"""Tests for Z3 solver."""

import sys
import json
import subprocess
from pathlib import Path

Z3 = Path(__file__).parent.parent / "src" / "z3_solver" / "solver_z3.py"
DATA = Path(__file__).parent.parent / "data" / "manual"

def run_z3(input_path):
    result = subprocess.run(
        ["/home/lcy/Workspace/Formalization/final/.venv/bin/python3", str(Z3), str(input_path), "-q"],
        capture_output=True, text=True, timeout=10
    )
    return json.loads(result.stdout)

def test_tiny_sat():
    r = run_z3(DATA / "tiny_sat.json")
    assert r["result"] == "sat", f"Expected sat, got {r['result']}"
    assert len(r["rectangles"]) == 2
    print(f"  tiny_sat: {r['result']} ({r['runtime_ms']:.3f}ms) OK")

def test_tiny_unsat():
    r = run_z3(DATA / "tiny_unsat.json")
    assert r["result"] == "unsat", f"Expected unsat, got {r['result']}"
    print(f"  tiny_unsat: {r['result']} OK")

def test_medium_sat():
    r = run_z3(DATA / "medium_sat.json")
    assert r["result"] == "sat", f"Expected sat, got {r['result']}"
    print(f"  medium_sat: {r['result']} ({r['runtime_ms']:.3f}ms) OK")

def test_medium_unsat():
    r = run_z3(DATA / "medium_unsat.json")
    assert r["result"] == "unsat", f"Expected unsat, got {r['result']}"
    print(f"  medium_unsat: {r['result']} OK")

def test_hard_sat():
    r = run_z3(DATA / "hard_sat1.json")
    assert r["result"] == "sat", f"Expected sat, got {r['result']}"
    print(f"  hard_sat: {r['result']} ({r['runtime_ms']:.3f}ms) OK")

def test_rotation_needed():
    r = run_z3(DATA / "rotation_needed.json")
    assert r["result"] == "sat", f"Expected sat, got {r['result']}"
    print(f"  rotation_needed: {r['result']} OK")

def test_no_rotation():
    r = run_z3(DATA / "no_rotation.json")
    assert r["result"] == "sat", f"Expected sat, got {r['result']}"
    print(f"  no_rotation: {r['result']} OK")

if __name__ == "__main__":
    print("Running Z3 solver tests...")
    test_tiny_sat()
    test_tiny_unsat()
    test_medium_sat()
    test_medium_unsat()
    test_hard_sat()
    test_rotation_needed()
    test_no_rotation()
    print("\nAll Z3 tests passed!")
