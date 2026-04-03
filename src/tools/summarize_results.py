#!/usr/bin/env python3
"""
Summarize benchmark results: generate CSV and Markdown tables.
"""

import json
import csv
import argparse
from pathlib import Path
from collections import defaultdict
import statistics

def load_csv(path: Path):
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def summarize(path: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = load_csv(path)
    if not rows:
        print("No data to summarize")
        return
    
    # Group by instance, take median runtime per solver
    by_instance = defaultdict(lambda: defaultdict(list))
    for r in rows:
        solver = r["solver"]
        inst = r["instance"]
        by_instance[inst][solver].append(float(r["runtime_ms"]) if r["runtime_ms"] else 0.0)
    
    # Build summary table
    summary = []
    for inst, by_solver in sorted(by_instance.items()):
        row = {"instance": inst}
        for solver, times in by_solver.items():
            med = statistics.median(times)
            row[f"{solver}_runtime_ms"] = round(med, 3)
            row[f"{solver}_result"] = "sat" if any(
                rows2["result"] == "sat" for rows2 in rows 
                if rows2["instance"] == inst and rows2["solver"] == solver
            ) else "unsat"
        summary.append(row)
    
    # Write summary CSV
    summary_csv = output_dir / "summary.csv"
    if summary:
        all_keys = set()
        for row in summary:
            all_keys.update(row.keys())
        cols = sorted(all_keys)
        with open(summary_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=cols)
            writer.writeheader()
            writer.writerows(summary)
    
    # Build category comparison table
    by_cat_solver = defaultdict(lambda: defaultdict(list))
    for r in rows:
        cat = r.get("category", "unknown")
        solver = r["solver"]
        if r["runtime_ms"]:
            by_cat_solver[cat][solver].append(float(r["runtime_ms"]))
    
    cat_lines = ["## Category Summary\n\n",
                 "| Category | Solver | Count | Median(ms) | Mean(ms) | Min(ms) | Max(ms) |"]
    cat_lines.append("|----------|--------|-------|------------|----------|---------|---------|")
    
    for cat in sorted(by_cat_solver.keys()):
        for solver in sorted(by_cat_solver[cat].keys()):
            times = by_cat_solver[cat][solver]
            if not times:
                continue
            med = statistics.median(times)
            mean = statistics.mean(times)
            mn = min(times)
            mx = max(times)
            cat_lines.append(
                f"| {cat} | {solver} | {len(times)} | {med:.3f} | {mean:.3f} | {mn:.3f} | {mx:.3f} |"
            )
    
    # Build solver comparison
    if "z3_runtime_ms" in (summary[0] if summary else {}):
        comp_lines = ["\n## Z3 vs Custom Solver Comparison\n\n",
                      "| Instance | Z3(ms) | Custom(ms) | Winner | Speedup |"]
        comp_lines.append("|----------|--------|------------|--------|---------|")
        for row in summary:
            inst = row["instance"]
            z3t = row.get("z3_runtime_ms")
            cust = row.get("custom_runtime_ms")
            if z3t and cust:
                if z3t < cust:
                    winner = "Z3"
                    speedup = cust / z3t if z3t > 0 else "inf"
                elif cust < z3t:
                    winner = "Custom"
                    speedup = z3t / cust if cust > 0 else "inf"
                else:
                    winner = "Tie"
                    speedup = "1.0x"
                comp_lines.append(
                    f"| {inst} | {z3t} | {cust} | {winner} | {speedup}x |"
                )
    
    # Generate full markdown
    md = []
    md.append("# Rectangle Fitting Benchmark Results\n\n")
    md.append(f"Generated from: `{path}`\n\n")
    md.append(f"Total instances: {len(by_instance)}\n\n")
    md.append("".join(cat_lines))
    if "z3_runtime_ms" in (summary[0] if summary else {}):
        md.append("".join(comp_lines))
    md.append("\n\n## Statistics Summary\n\n")
    md.append("| Solver | # SAT | # UNSAT | # Timeout | Avg Runtime(ms) |\n")
    md.append("|--------|-------|---------|-----------|------------------|\n")
    for solver in ["z3", "custom"]:
        sats = sum(1 for r in rows if r["solver"] == solver and r["result"] == "sat")
        unsats = sum(1 for r in rows if r["solver"] == solver and r["result"] == "unsat")
        timeouts = sum(1 for r in rows if r["result"] == "timeout")
        times = [float(r["runtime_ms"]) for r in rows if r["solver"] == solver and r["runtime_ms"]]
        avg = statistics.mean(times) if times else 0
        md.append(f"| {solver} | {sats} | {unsats} | {timeouts} | {avg:.3f} |\n")
    
    # Add custom solver detailed stats
    custom_rows = [r for r in rows if r["solver"] == "custom" and r.get("recursive_calls")]
    if custom_rows:
        md.append("\n## Custom Solver Detailed Statistics\n\n")
        md.append("| Instance | Recursive Calls | Backtracks | Placements Tried | "
                  "Pruned Area | Pruned Infeasible | LS Calls | Max Depth |\n")
        md.append("|----------|------------------|------------|------------------|"
                  "-------------|-------------------|----------|----------|\n")
        for r in custom_rows:
            md.append(f"| {r['instance']} | {r.get('recursive_calls',0)} | "
                      f"{r.get('backtracks',0)} | {r.get('placements_tried',0)} | "
                      f"{r.get('pruned_area',0)} | {r.get('pruned_infeasible',0)} | "
                      f"{r.get('local_search_calls',0)} | {r.get('max_depth',0)} |\n")
    
    md_path = output_dir / "benchmark_report.md"
    with open(md_path, "w") as f:
        f.write("".join(md))
    
    print(f"Summary CSV: {summary_csv}")
    print(f"Report MD:   {md_path}")


def main():
    parser = argparse.ArgumentParser(description="Summarize benchmark results")
    parser.add_argument("csv", help="Input CSV from benchmark.py")
    parser.add_argument("-o", "--output-dir", default="results/tables",
                        help="Output directory for summaries")
    args = parser.parse_args()
    summarize(Path(args.csv), Path(args.output_dir))

if __name__ == "__main__":
    main()
