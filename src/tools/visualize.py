#!/usr/bin/env python3
"""
Visualize rectangle fitting solutions.
Draws the container with placed rectangles labeled by id and size.
"""

import json
import sys
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

def visualize(input_path: Path, output_path: Path, solution_path: Path = None,
              show: bool = False, title: str = None):
    """Render rectangle fitting layout as PNG."""
    
    with open(input_path) as f:
        inst = json.load(f)
    
    W, H = inst["container"]["W"], inst["container"]["H"]
    rects = inst.get("rectangles", [])
    allow_rot = inst.get("allow_rotation", True)
    
    # Load solution if provided
    solution_rects = None
    if solution_path and solution_path.exists():
        with open(solution_path) as f:
            sol = json.load(f)
            solution_rects = sol.get("rectangles", [])
    
    # Determine which rects to draw
    draw_rects = solution_rects if solution_rects else rects
    
    fig, ax = plt.subplots(1, 1, figsize=(max(8, W/2), max(6, H/2)))
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect('equal')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    
    # Draw container background
    container = patches.Rectangle((0, 0), W, H, linewidth=2, 
                                   edgecolor='black', facecolor='#f0f0f0')
    ax.add_patch(container)
    
    # Color palette
    colors = plt.cm.tab20.colors + plt.cm.Set3.colors
    
    placed_info = []
    for i, r in enumerate(draw_rects):
        if solution_rects:
            x, y = r.get("x", 0), r.get("y", 0)
            w, h = r.get("w", r.get("pw", r["w"])), r.get("h", r.get("ph", r["h"]))
            rot = r.get("rotated", False)
        else:
            x, y = 0, 0
            w, h = r.get("w", 4), r.get("h", 3)
            rot = False
        
        color = colors[i % len(colors)]
        rect_patch = patches.Rectangle((x, y), w, h, linewidth=1,
                                        edgecolor='black', facecolor=color, alpha=0.8)
        ax.add_patch(rect_patch)
        
        # Label
        label = f"id={r['id']}"
        if rot:
            label += " R"
        if solution_rects:
            label += f"\n{w}×{h}"
        
        cx, cy = x + w/2, y + h/2
        fontsize = min(10, max(6, min(w, h) * 1.5))
        if w >= 2 and h >= 1.5:
            ax.text(cx, cy, label, ha='center', va='center',
                    fontsize=fontsize, fontweight='bold')
        elif w >= 1:
            ax.text(cx, cy, f"{r['id']}", ha='center', va='center',
                    fontsize=fontsize, fontweight='bold')
        
        placed_info.append((x, y, w, h, r["id"]))
    
    # Add grid
    ax.set_xticks(range(W+1))
    ax.set_yticks(range(H+1))
    ax.grid(True, alpha=0.3)
    ax.set_facecolor('#e8e8e8')
    
    instance_name = input_path.stem
    solver_name = solution_path.stem if solution_path else "original"
    ax.set_title(title or f"Rectangle Fitting: {instance_name} ({W}×{H})")
    
    # Legend info
    total_area = sum(r["w"]*r["h"] for r in inst.get("rectangles", []))
    fill_ratio = total_area / (W*H) if W*H > 0 else 0
    info_text = f"Rects: {len(draw_rects)}  Fill: {fill_ratio:.1%}"
    if solution_rects:
        info_text += f"  Status: {sol.get('result', '?')}"
        info_text += f"  Time: {sol.get('runtime_ms', 0):.1f}ms"
    ax.text(W + 0.2, H - 0.5, info_text, fontsize=9, va='top')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()
    plt.close()
    print(f"Visualization saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Visualize rectangle fitting solutions")
    parser.add_argument("input", help="Input instance JSON")
    parser.add_argument("-o", "--output", help="Output PNG path")
    parser.add_argument("-s", "--solution", help="Solution JSON from solver")
    parser.add_argument("--show", action="store_true", help="Show plot interactively")
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent.parent / "results" / "figures" / f"{input_path.stem}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    solution_path = Path(args.solution) if args.solution else None
    visualize(input_path, output_path, solution_path, show=args.show)


if __name__ == "__main__":
    main()
