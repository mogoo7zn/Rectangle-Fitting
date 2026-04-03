#!/usr/bin/env python3
"""Tests for custom C++ solver."""

import sys
import json
import subprocess
from pathlib import Path

CUSTOM = Path(__file__).parent.parent / "build" / "solver_custom"
DATA = Path(__file__).parent.parent / "data" / "manual"

def run_custom(input_path, extra_args=None):
    args = [str(CUSTOM), str(input_path)]
    if extra_args:
        args.extend(extra_args)
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"  ERROR: {result.stderr[:200]}")
        return {"result": "error", "error": result.stderr}

def test_tiny_sat():
    r = run_custom(DATA / "tiny_sat.json")
    assert r["result"] == "sat", f"Expected sat, got {r['result']}"
    print(f"  tiny_sat: {r['result']} ({r['runtime_ms']:.3f}ms) OK")

def test_tiny_unsat():
    r = run_custom(DATA / "tiny_unsat.json")
    assert r["result"] == "unsat", f"Expected unsat, got {r['result']}"
    print(f"  tiny_unsat: {r['result']} OK")

def test_medium_sat():
    r = run_custom(DATA / "medium_sat.json")
    assert r["result"] == "sat", f"Expected sat, got {r['result']}"
    stats = r.get("stats", {})
    print(f"  medium_sat: {r['result']} ({r['runtime_ms']:.3f}ms) "
          f"calls={stats.get('recursive_calls',0)} OK")

def test_medium_unsat():
    r = run_custom(DATA / "medium_unsat.json")
    assert r["result"] == "unsat", f"Expected unsat, got {r['result']}"
    print(f"  medium_unsat: {r['result']} OK")

def test_hard_sat():
    r = run_custom(DATA / "hard_sat1.json", ["-t", "30000"])
    assert r["result"] == "sat", f"Expected sat, got {r['result']}"
    stats = r.get("stats", {})
    print(f"  hard_sat: {r['result']} ({r['runtime_ms']:.3f}ms) "
          f"calls={stats.get('recursive_calls',0)} OK")

def test_rotation_needed():
    r = run_custom(DATA / "rotation_needed.json")
    assert r["result"] == "sat", f"Expected sat, got {r['result']}"
    print(f"  rotation_needed: {r['result']} OK")

def test_heuristics():
    for heur in ["area", "dim"]:
        r = run_custom(DATA / "medium_sat.json", ["-H", heur])
        assert r["result"] == "sat", f"Expected sat with heur={heur}, got {r['result']}"
        print(f"  heuristic {heur}: {r['result']} OK")

if __name__ == "__main__":
    if not CUSTOM.exists():
        print(f"ERROR: {CUSTOM} not found. Compile with: mkdir build && cd build && cmake .. && make")
        sys.exit(1)
    print("Running custom solver tests...")
    test_tiny_sat()
    test_tiny_unsat()
    test_medium_sat()
    test_medium_unsat()
    test_hard_sat()
    test_rotation_needed()
    test_heuristics()
    print("\nAll custom solver tests passed!")
