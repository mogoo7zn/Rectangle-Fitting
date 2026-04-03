#!/usr/bin/env python3
"""
Rectangle Fitting Solver using Z3 SMT Solver.

Implements the SMT modeling from the course PPT:
- Variables for each rectangle position (x_i, y_i) and actual size (w_i, h_i)
- Rotation constraints
- Boundary constraints
- Non-overlap (disjoint) constraints via complementary case splitting
"""

import sys
import json
import time
import argparse
from z3 import Solver, Int, Bool, Or, And, Not, sat, unsat


class Z3RectSolver:
    def __init__(self, inst: dict, allow_rotation: bool = True,
                 symmetry_breaking: bool = True, area_check: bool = True):
        self.inst = inst
        self.W = inst["container"]["W"]
        self.H = inst["container"]["H"]
        self.allow_rotation = allow_rotation and inst.get("allow_rotation", True)
        self.symmetry_breaking = symmetry_breaking
        self.area_check = area_check
        self.rects = inst["rectangles"]
        self.n = len(self.rects)
        # Store built variables as instance attributes so solve() can access them
        self.xs, self.ys, self.ws, self.hs = [], [], [], []
        self.rotated_bools = []
        self.solver = None  # set by build() if SMT formula is constructed

    def _quick_area_check(self):
        """If total area of small rects exceeds container area -> unsat."""
        total = sum(r["w"] * r["h"] for r in self.rects)
        return total <= self.W * self.H

    def build(self):
        """Build the SMT formula and store variables as instance attributes."""
        if self.area_check and not self._quick_area_check():
            return False  # unsat

        solver = Solver()

        for i, r in enumerate(self.rects):
            Wi, Hi = r["w"], r["h"]
            xi = Int(f"x_{i}")
            yi = Int(f"y_{i}")
            wi = Int(f"w_{i}")
            hi = Int(f"h_{i}")
            ri = Bool(f"r_{i}")

            self.xs.append(xi)
            self.ys.append(yi)
            self.ws.append(wi)
            self.hs.append(hi)
            self.rotated_bools.append(ri)

            # Boundary: xi >= 0, yi >= 0
            solver.add(xi >= 0)
            solver.add(yi >= 0)

            # Rotation constraint
            if self.allow_rotation:
                solver.add(
                    Or(
                        And(wi == Wi, hi == Hi, Not(ri)),
                        And(wi == Hi, hi == Wi, ri)
                    )
                )
            else:
                solver.add(And(wi == Wi, hi == Hi, Not(ri)))

            # Fit inside container
            solver.add(xi + wi <= self.W)
            solver.add(yi + hi <= self.H)

        # Non-overlap constraints: for all i < j
        for i in range(self.n):
            for j in range(i + 1, self.n):
                xi, yi, wi, hi = self.xs[i], self.ys[i], self.ws[i], self.hs[i]
                xj, yj, wj, hj = self.xs[j], self.ys[j], self.ws[j], self.hs[j]

                # Disjoint: no overlap in either dimension
                # xj >= xi+wi  OR  xi >= xj+wj  OR
                # yj >= yi+hi  OR  yi >= yj+hj
                solver.add(
                    Or(
                        xj >= xi + wi,
                        xi >= xj + wj,
                        yj >= yi + hi,
                        yi >= yj + hj
                    )
                )

        # Symmetry breaking: only apply when there is a UNIQUE largest rectangle
        if self.symmetry_breaking and self.n > 0:
            areas = [(r["w"] * r["h"], i) for i, r in enumerate(self.rects)]
            max_area = max(a[0] for a in areas)
            max_rects = [i for a, i in areas if a == max_area]
            # Only break symmetry when the largest rectangle is unique
            if len(max_rects) == 1:
                max_idx = max_rects[0]
                solver.add(self.xs[max_idx] == 0)
                solver.add(self.ys[max_idx] == 0)

            # Break ties for same-size rectangles by id ordering
            for i in range(self.n):
                for j in range(i + 1, self.n):
                    ri, rj = self.rects[i], self.rects[j]
                    Wi, Hi = ri["w"], ri["h"]
                    Wj, Hj = rj["w"], rj["h"]
                    if Wi == Wj and Hi == Hj:
                        # Impose: (xi < xj) OR (xi == xj AND yi <= yj) OR (yi < yj)
                        solver.add(
                            Or(
                                self.xs[i] < self.xs[j],
                                And(self.xs[i] == self.xs[j], self.ys[i] <= self.ys[j]),
                                self.ys[i] < self.ys[j]
                            )
                        )

        self.solver = solver
        return True  # sat possible

    def solve(self, timeout_ms: int = 30000) -> dict:
        """Solve and return result dict."""
        # If build() found area check failed, return unsat directly
        if self.solver is None:
            return {"result": "unsat", "runtime_ms": 0.0, "rectangles": []}
        self.solver.set(timeout=timeout_ms)
        start = time.perf_counter()
        result = self.solver.check()
        elapsed = (time.perf_counter() - start) * 1000.0

        out = {
            "result": "sat" if result == sat else ("unsat" if result == unsat else "unknown"),
            "runtime_ms": round(elapsed, 3),
            "rectangles": []
        }

        if result == sat:
            model = self.solver.model()
            for i, r in enumerate(self.rects):
                out["rectangles"].append({
                    "id": r["id"],
                    "x": model.eval(self.xs[i]).as_long(),
                    "y": model.eval(self.ys[i]).as_long(),
                    "w": model.eval(self.ws[i]).as_long(),
                    "h": model.eval(self.hs[i]).as_long(),
                    "rotated": is_true(model.eval(self.rotated_bools[i]))
                })
        return out


def is_true(z3_bool):
    """Convert z3 Bool to Python bool."""
    return str(z3_bool) == "True"


def main():
    parser = argparse.ArgumentParser(description="Rectangle Fitting with Z3")
    parser.add_argument("input", help="Input JSON file")
    parser.add_argument("--no-rotation", action="store_true", help="Disable rotation")
    parser.add_argument("--no-symmetry", action="store_true", help="Disable symmetry breaking")
    parser.add_argument("--no-area-check", action="store_true", help="Disable area quick check")
    parser.add_argument("-o", "--output", help="Output JSON file")
    parser.add_argument("--timeout", type=int, default=30000, help="Timeout in ms")
    parser.add_argument("-q", "--quiet", action="store_true", help="Only output result")
    args = parser.parse_args()

    with open(args.input) as f:
        inst = json.load(f)

    allow_rot = not args.no_rotation
    sym_break = not args.no_symmetry
    area_chk = not args.no_area_check

    z3solver = Z3RectSolver(inst, allow_rotation=allow_rot,
                            symmetry_breaking=sym_break, area_check=area_chk)
    z3solver.build()

    result = z3solver.solve(timeout_ms=args.timeout)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
    else:
        print(json.dumps(result, indent=2))

    if not args.quiet:
        print(f"\nResult: {result['result']}")
        print(f"Runtime: {result['runtime_ms']:.3f} ms")
        if result["result"] == "sat":
            print(f"Placed {len(result['rectangles'])} rectangles")


if __name__ == "__main__":
    main()
