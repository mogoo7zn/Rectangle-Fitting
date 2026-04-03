#!/usr/bin/env python3
"""
Dataset generator for Rectangle Fitting.
Generates easy / medium / hard test instances with controlled difficulty.
"""

import json
import random
import argparse
from pathlib import Path

def generate_random_rects(n, min_size=2, max_size=12, seed=42):
    """Generate n random rectangles with sizes in [min_size, max_size]."""
    rng = random.Random(seed)
    rects = []
    for i in range(n):
        w = rng.randint(min_size, max_size)
        h = rng.randint(min_size, max_size)
        rects.append({"id": i+1, "w": w, "h": h})
    return rects

def try_place_rects(rects, W, H, seed):
    """Try greedy placement to see if SAT instance is plausible."""
    rng = random.Random(seed)
    placed = []
    anchors = [(0, 0)]
    
    for r in rects:
        found = False
        cand = list(anchors)
        rng.shuffle(cand)
        for (x, y) in cand:
            for rot in [(r["w"], r["h"]), (r["h"], r["w"])] if r["w"] != r["h"] else [(r["w"], r["h"])]:
                w, h = rot
                if x + w <= W and y + h <= H:
                    ok = True
                    for p in placed:
                        if not (x + w <= p["x"] or x >= p["x"] + p["pw"] or
                                y + h <= p["y"] or y >= p["y"] + p["ph"]):
                            ok = False
                            break
                    if ok:
                        placed.append({"id": r["id"], "x": x, "y": y, "pw": w, "ph": h,
                                       "w": r["w"], "h": r["h"]})
                        # Add new anchors
                        new_anchors = [(x + w, y), (x, y + h)]
                        for na in new_anchors:
                            if na[0] < W and na[1] < H and na not in anchors:
                                anchors.append(na)
                        found = True
                        break
            if found: break
        if not found:
            return None  # unsat
    return placed

def make_sat_instance(W, H, rects, allow_rotation=True):
    return {
        "container": {"W": W, "H": H},
        "allow_rotation": allow_rotation,
        "rectangles": rects
    }

def make_unsat_instance(total_area, W, H, rects, allow_rotation=True):
    # total_area > W*H already, just return
    return {
        "container": {"W": W, "H": H},
        "allow_rotation": allow_rotation,
        "rectangles": rects
    }

def generate_easy(W=10, H=8, seed=1):
    """Easy: 5-8 rects, mostly fit easily."""
    rng = random.Random(seed)
    n = rng.randint(5, 8)
    rects = []
    sizes = [(3,3),(4,2),(2,4),(3,2),(2,3),(3,4),(4,3),(5,2),(2,5)]
    rng.shuffle(sizes)
    for i in range(n):
        s = sizes[i % len(sizes)]
        rects.append({"id": i+1, "w": s[0], "h": s[1]})
    return make_sat_instance(W, H, rects)

def generate_medium(W=20, H=15, seed=11):
    """Medium: 10-15 rects, need some thought."""
    rng = random.Random(seed)
    n = rng.randint(10, 15)
    rects = generate_random_rects(n, min_size=3, max_size=10, seed=seed)
    return make_sat_instance(W, H, rects)

def generate_hard(W=30, H=25, seed=101):
    """Hard: 20-30 rects, high fill rate."""
    rng = random.Random(seed)
    n = rng.randint(20, 30)
    rects = generate_random_rects(n, min_size=3, max_size=8, seed=seed)
    return make_sat_instance(W, H, rects)

def generate_unsat_easy(W=10, H=8, seed=2):
    """Unsat: area too large."""
    rng = random.Random(seed)
    rects = [{"id": 1, "w": 5, "h": 6}, {"id": 2, "w": 4, "h": 5},
             {"id": 3, "w": 3, "h": 4}]
    return make_unsat_instance(sum(r["w"]*r["h"] for r in rects) + 1, W, H, rects)

def generate_unsat_medium(W=20, H=15, seed=12):
    """Unsat medium."""
    rng = random.Random(seed)
    rects = generate_random_rects(8, min_size=5, max_size=12, seed=seed)
    return make_unsat_instance(sum(r["w"]*r["h"] for r in rects) + 10, W, H, rects)

def generate_unsat_hard(W=30, H=25, seed=102):
    """Unsat hard: near area limit but shape conflicts."""
    rng = random.Random(seed)
    n = rng.randint(15, 20)
    rects = generate_random_rects(n, min_size=4, max_size=9, seed=seed)
    # Adjust container to make it barely unsatisfiable
    return make_unsat_instance(sum(r["w"]*r["h"] for r in rects) + 5, W, H, rects)

def main():
    parser = argparse.ArgumentParser(description="Generate rectangle fitting test cases")
    parser.add_argument("-o", "--output-dir", default="data/generated", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed base")
    args = parser.parse_args()

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    categories = {
        "easy": [
            ("easy_sat_1.json", lambda: generate_easy(10, 8, 1)),
            ("easy_sat_2.json", lambda: generate_easy(12, 10, 2)),
            ("easy_unsat_1.json", lambda: generate_unsat_easy(10, 8, 2)),
        ],
        "medium": [
            ("medium_sat_1.json", lambda: generate_medium(20, 15, 11)),
            ("medium_sat_2.json", lambda: generate_medium(20, 15, 12)),
            ("medium_unsat_1.json", lambda: generate_unsat_medium(20, 15, 12)),
        ],
        "hard": [
            ("hard_sat_1.json", lambda: generate_hard(30, 25, 101)),
            ("hard_sat_2.json", lambda: generate_hard(35, 30, 102)),
            ("hard_unsat_1.json", lambda: generate_unsat_hard(30, 25, 102)),
        ]
    }

    total = 0
    for cat, cases in categories.items():
        catdir = outdir / cat
        catdir.mkdir(exist_ok=True)
        for fname, gen_fn in cases:
            inst = gen_fn()
            path = catdir / fname
            with open(path, "w") as f:
                json.dump(inst, f, indent=2)
            print(f"Generated: {path}")
            total += 1

    # Also generate batch of varied cases
    batch_dir = outdir / "batch"
    batch_dir.mkdir(exist_ok=True)
    for i in range(5):
        for cat, (W, H, n_range) in [("easy", (12, 10, (4,7))), 
                                      ("medium", (20, 15, (10,16))),
                                      ("hard", (30, 25, (20,28)))]:
            rng = random.Random(args.seed + i * 100 + hash(cat) % 1000)
            n = rng.randint(*n_range)
            rects = generate_random_rects(n, min_size=2, max_size=10,
                                          seed=args.seed + i*10 + hash(cat))
            total_area = sum(r["w"] * r["h"] for r in rects)
            container_area = W * H
            # Make some sat, some unsat
            if i % 3 != 0:  # 2/3 sat
                scale = min(1.0, container_area * 0.75 / total_area)
                adjusted = []
                for r in rects:
                    adjusted.append({
                        "id": r["id"],
                        "w": max(1, int(r["w"] * scale)),
                        "h": max(1, int(r["h"] * scale))
                    })
                inst = make_sat_instance(W, H, adjusted)
            else:
                inst = make_unsat_instance(total_area + 1, W, H, rects)
            path = batch_dir / f"batch_{cat}_{i}.json"
            with open(path, "w") as f:
                json.dump(inst, f, indent=2)
            print(f"Generated: {path}")
            total += 1

    print(f"\nTotal generated: {total} instances")

if __name__ == "__main__":
    main()
