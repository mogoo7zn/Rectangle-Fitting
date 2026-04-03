#!/usr/bin/env python3
"""
Benchmark script: run both Z3 and custom solver on test instances.
"""

import sys
import json
import time
import subprocess
import argparse
import csv
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Optional

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# We'll import z3 solver directly
# __file__ = .../src/tools/benchmark.py
# parent = .../src/tools/  → parent.parent = .../src/  → parent.parent.parent = project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
Z3_SCRIPT = PROJECT_ROOT / "src" / "z3_solver" / "solver_z3.py"
CUSTOM_BINARY = PROJECT_ROOT / "build" / "solver_custom"

PYTHON = str(PROJECT_ROOT / ".venv/bin/python3")

def run_z3(input_path: Path, timeout_ms: int = 30000,
           allow_rotation: bool = True,
           extra_flags: Optional[List[str]] = None) -> dict:
    """Run Z3 solver and parse output."""
    flags = [str(Z3_SCRIPT), str(input_path)]
    if not allow_rotation:
        flags.append("--no-rotation")
    if extra_flags:
        flags.extend(extra_flags)

    flags.extend(["-q"])  # quiet

    try:
        result = subprocess.run(
            [PYTHON] + flags,
            capture_output=True, text=True, timeout=max(timeout_ms/1000+5, 10)
        )
        out = result.stdout.strip()
        if out:
            try:
                data = json.loads(out)
                return {
                    "result": data.get("result", "unknown"),
                    "runtime_ms": data.get("runtime_ms", 0.0),
                    "rectangles": data.get("rectangles", []),
                    "success": True,
                    "error": None
                }
            except json.JSONDecodeError:
                return {"result": "error", "runtime_ms": 0, "success": False, 
                        "error": f"parse error: {out[:200]}"}
        else:
            return {"result": "error", "runtime_ms": 0, "success": False,
                    "error": f"no output: {result.stderr[:200]}"}
    except subprocess.TimeoutExpired:
        return {"result": "timeout", "runtime_ms": timeout_ms, "success": True,
                "error": None}
    except Exception as e:
        return {"result": "error", "runtime_ms": 0, "success": False, "error": str(e)}


def run_custom(input_path: Path, timeout_ms: int = 30000,
               allow_rotation: bool = True,
               heuristic: str = "area",
               extra_flags: Optional[List[str]] = None) -> dict:
    """Run custom C++ solver and parse output."""
    if not CUSTOM_BINARY.exists():
        return {"result": "error", "runtime_ms": 0, "success": False,
                "error": "binary not found - compile with cmake && make"}
    
    flags = [str(CUSTOM_BINARY), str(input_path), "-t", str(timeout_ms), "-H", heuristic]
    if not allow_rotation:
        flags.append("--no-rot")
    if extra_flags:
        flags.extend(extra_flags)
    
    try:
        result = subprocess.run(
            flags, capture_output=True, text=True, timeout=max(timeout_ms/1000+5, 10)
        )
        out = result.stdout.strip()
        if out:
            try:
                data = json.loads(out)
                stats = data.get("stats", {})
                return {
                    "result": data.get("result", "unknown"),
                    "runtime_ms": data.get("runtime_ms", 0.0),
                    "rectangles": data.get("rectangles", []),
                    "recursive_calls": stats.get("recursive_calls", 0),
                    "backtracks": stats.get("backtracks", 0),
                    "placements_tried": stats.get("placements_tried", 0),
                    "pruned_area": stats.get("pruned_by_area", 0),
                    "pruned_infeasible": stats.get("pruned_by_infeasible", 0),
                    "pruned_symmetry": stats.get("pruned_by_symmetry", 0),
                    "local_search_calls": stats.get("local_search_calls", 0),
                    "local_search_successes": stats.get("local_search_successes", 0),
                    "max_depth": stats.get("max_depth", 0),
                    "success": True,
                    "error": None
                }
            except json.JSONDecodeError:
                return {"result": "error", "runtime_ms": 0, "success": False,
                        "error": f"parse error: {result.stderr[:200]}"}
        else:
            return {"result": "error", "runtime_ms": 0, "success": False,
                    "error": f"no output: {result.stderr[:200]}"}
    except subprocess.TimeoutExpired:
        return {"result": "timeout", "runtime_ms": timeout_ms, "success": True,
                "error": None}
    except Exception as e:
        return {"result": "error", "runtime_ms": 0, "success": False, "error": str(e)}


def benchmark_instance(inst_path: Path, solvers: List[str], 
                       timeout_ms: int, repeats: int,
                       allow_rotation: bool, heuristic: str) -> List[dict]:
    """Benchmark one instance with given solvers."""
    results = []
    for solver in solvers:
        for rep in range(repeats):
            if solver == "z3":
                r = run_z3(inst_path, timeout_ms, allow_rotation)
                r["solver"] = "z3"
            elif solver == "custom":
                r = run_custom(inst_path, timeout_ms, allow_rotation, heuristic)
                r["solver"] = "custom"
            else:
                continue
            
            r["instance"] = inst_path.name
            r["instance_path"] = str(inst_path)
            r["repeat"] = rep
            r["allow_rotation"] = allow_rotation
            r["heuristic"] = heuristic
            results.append(r)
    return results


def load_instance(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def run_benchmarks(input_dir: Path, solvers: List[str], output_csv: Path,
                    timeout_ms: int, repeats: int, allow_rotation: bool,
                    heuristic: str, max_files: Optional[int] = None):
    """Run all benchmarks."""
    patterns = ["*.json"]
    files = []
    for pat in patterns:
        files.extend(sorted(input_dir.rglob(pat)))
    
    if max_files:
        files = files[:max_files]
    
    print(f"Benchmarking {len(files)} instances with solvers: {solvers}")
    print(f"Timeout: {timeout_ms}ms, Repeats: {repeats}")
    
    all_results = []
    for i, fp in enumerate(files):
        inst = load_instance(fp)
        n_rects = len(inst.get("rectangles", []))
        total_area = sum(r["w"]*r["h"] for r in inst.get("rectangles", []))
        container_area = inst["container"]["W"] * inst["container"]["H"]
        area_ratio = total_area / container_area if container_area > 0 else 0

        print(f"[{i+1}/{len(files)}] {fp.name}  n={n_rects}  area_ratio={area_ratio:.2f}")
        
        for solver in solvers:
            for rep in range(repeats):
                t0 = time.perf_counter()
                if solver == "z3":
                    r = run_z3(fp, timeout_ms, allow_rotation)
                elif solver == "custom":
                    r = run_custom(fp, timeout_ms, allow_rotation, heuristic)
                else:
                    continue
                elapsed = (time.perf_counter() - t0) * 1000

                row = {
                    "instance": fp.name,
                    "category": fp.parent.name,
                    "n_rectangles": n_rects,
                    "container_W": inst["container"]["W"],
                    "container_H": inst["container"]["H"],
                    "total_area": total_area,
                    "container_area": container_area,
                    "area_ratio": round(area_ratio, 4),
                    "allow_rotation": allow_rotation,
                    "solver": solver,
                    "result": r.get("result", "error"),
                    "runtime_ms": r.get("runtime_ms", elapsed),
                    "success": r.get("success", False),
                    "error": r.get("error", ""),
                    "repeat": rep,
                }
                if solver == "custom":
                    st = r.get("stats", r)  # stats nested or flat
                    row["recursive_calls"] = int(st.get("recursive_calls", 0))
                    row["backtracks"] = int(st.get("backtracks", 0))
                    row["placements_tried"] = int(st.get("placements_tried", 0))
                    row["pruned_area"] = int(st.get("pruned_by_area", 0))
                    row["pruned_infeasible"] = int(st.get("pruned_by_infeasible", 0))
                    row["pruned_symmetry"] = int(st.get("pruned_by_symmetry", 0))
                    row["local_search_calls"] = int(st.get("local_search_calls", 0))
                    row["local_search_successes"] = int(st.get("local_search_successes", 0))
                    row["max_depth"] = int(st.get("max_depth", 0))
                all_results.append(row)

    # Write CSV
    if all_results:
        # Use a fixed column list to avoid missing field errors
        cols = [
            "instance", "category", "n_rectangles", "container_W", "container_H",
            "total_area", "container_area", "area_ratio", "allow_rotation",
            "solver", "result", "runtime_ms", "success", "error", "repeat",
            "recursive_calls", "backtracks", "placements_tried",
            "pruned_area", "pruned_infeasible", "pruned_symmetry",
            "local_search_calls", "local_search_successes", "max_depth"
        ]
        with open(output_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_results)
        print(f"\nResults written to: {output_csv}")
    
    return all_results


def main():
    parser = argparse.ArgumentParser(description="Benchmark rectangle fitting solvers")
    parser.add_argument("-i", "--input-dir", default="data/generated",
                        help="Directory containing JSON instances")
    parser.add_argument("-o", "--output", default="results/raw/benchmark_results.csv",
                        help="Output CSV path")
    parser.add_argument("--solvers", default="z3,custom",
                        help="Comma-separated solver list: z3,custom")
    parser.add_argument("--timeout", type=int, default=30000, help="Timeout per run (ms)")
    parser.add_argument("--repeats", type=int, default=1, help="Repeats per instance")
    parser.add_argument("--no-rotation", action="store_true", help="Disable rotation")
    parser.add_argument("--heuristic", default="area",
                        choices=["area","dim","candidates"],
                        help="Custom solver heuristic")
    parser.add_argument("--max-files", type=int, default=None, help="Max files to process")
    args = parser.parse_args()

    solvers = [s.strip() for s in args.solvers.split(",")]
    allow_rot = not args.no_rotation
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    run_benchmarks(
        input_dir=Path(args.input_dir),
        solvers=solvers,
        output_csv=output_path,
        timeout_ms=args.timeout,
        repeats=args.repeats,
        allow_rotation=allow_rot,
        heuristic=args.heuristic,
        max_files=args.max_files
    )

if __name__ == "__main__":
    main()
