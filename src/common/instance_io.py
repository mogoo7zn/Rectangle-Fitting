#!/usr/bin/env python3
"""Python utilities for reading/writing instance JSON and solution JSON."""

import json
from pathlib import Path
from typing import Dict, Any, List


def read_instance(path: str) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def write_instance(path: str, inst: Dict[str, Any]):
    with open(path, "w") as f:
        json.dump(inst, f, indent=2)


def read_solution(path: str) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def write_solution(path: str, sol: Dict[str, Any]):
    with open(path, "w") as f:
        json.dump(sol, f, indent=2)


def compute_stats(inst: Dict[str, Any]) -> Dict[str, Any]:
    """Compute basic statistics of an instance."""
    W, H = inst["container"]["W"], inst["container"]["H"]
    rects = inst.get("rectangles", [])
    total_area = sum(r["w"] * r["h"] for r in rects)
    container_area = W * H
    return {
        "n_rectangles": len(rects),
        "container_W": W,
        "container_H": H,
        "total_area": total_area,
        "container_area": container_area,
        "area_ratio": total_area / container_area if container_area > 0 else 0,
        "allow_rotation": inst.get("allow_rotation", True),
    }
