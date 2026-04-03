#include "solver.hpp"
#include <algorithm>
#include <chrono>
#include <cstring>
#include <iostream>
#include <random>

using namespace std;
using namespace std::chrono;

// ============================================================
// Construction
// ============================================================
RectangleSolver::RectangleSolver(const Instance& inst_,
    BranchHeuristic h, int time_limit_ms_, bool use_ls)
    : inst(inst_), heuristic(h), time_limit_ms(time_limit_ms_),
      use_local_search(use_ls)
{
    reset_stats();
}

// ============================================================
// Stats
// ============================================================
void RectangleSolver::reset_stats() {
    stat_recursive_calls = 0;
    stat_backtracks = 0;
    stat_placements_tried = 0;
    stat_pruned_area = 0;
    stat_pruned_infeasible = 0;
    stat_pruned_symmetry = 0;
    stat_local_search_calls = 0;
    stat_local_search_successes = 0;
    stat_max_depth = 0;
}

bool RectangleSolver::deadline_reached() const {
    auto now = duration_cast<microseconds>(
        steady_clock::now().time_since_epoch()).count();
    return (now >= deadline_us);
}

void RectangleSolver::update_stats_depth(int depth) {
    if (depth > stat_max_depth) stat_max_depth = depth;
}

// ============================================================
// Heuristic comparisons
// ============================================================
bool RectangleSolver::heuristic_compare_area(const Rect& a, const Rect& b) {
    int area_a = a.w * a.h, area_b = b.w * b.h;
    if (area_a != area_b) return area_a > area_b;
    int mx_a = max(a.w, a.h), mx_b = max(b.w, b.h);
    if (mx_a != mx_b) return mx_a > mx_b;
    return a.id < b.id;
}

bool RectangleSolver::heuristic_compare_maxdim(const Rect& a, const Rect& b) {
    int mx_a = max(a.w, a.h), mx_b = max(b.w, b.h);
    if (mx_a != mx_b) return mx_a > mx_b;
    int area_a = a.w * a.h, area_b = b.w * b.h;
    if (area_a != area_b) return area_a > area_b;
    return a.id < b.id;
}

bool RectangleSolver::heuristic_compare_candidates(const Rect& a, const Rect& b) {
    int ca = 0, cb = 0;
    for (const auto& anc : anchors) {
        if (a.w <= inst.W - anc.x && a.h <= inst.H - anc.y) ++ca;
        if (b.w <= inst.W - anc.x && b.h <= inst.H - anc.y) ++cb;
        if (a.h <= inst.W - anc.x && a.w <= inst.H - anc.y) ++ca;
        if (b.h <= inst.W - anc.x && b.w <= inst.H - anc.y) ++cb;
    }
    if (ca != cb) return ca < cb;
    return heuristic_compare_area(a, b);
}

void RectangleSolver::compute_ordering() {
    ordering.resize(unplaced.size());
    iota(ordering.begin(), ordering.end(), 0);
    switch (heuristic) {
        case BranchHeuristic::AREA_DESC:
            sort(ordering.begin(), ordering.end(),
                [&](int a, int b){ return heuristic_compare_area(unplaced[a], unplaced[b]); });
            break;
        case BranchHeuristic::MAX_DIM_DESC:
            sort(ordering.begin(), ordering.end(),
                [&](int a, int b){ return heuristic_compare_maxdim(unplaced[a], unplaced[b]); });
            break;
        case BranchHeuristic::FEWEST_CANDIDATES:
            sort(ordering.begin(), ordering.end(),
                [&](int a, int b){ return heuristic_compare_candidates(unplaced[a], unplaced[b]); });
            break;
    }
}

// ============================================================
// Placement checks — strict non-overlap (no shared interior)
// ============================================================
bool RectangleSolver::can_place(const Rect& r, int anchor_idx, bool try_rotate) {
    const AnchorPoint& anc = anchors[anchor_idx];
    int w = try_rotate ? r.h : r.w;
    int h = try_rotate ? r.w : r.h;
    if (anc.x + w > inst.W || anc.y + h > inst.H) return false;
    for (const auto& pl : placed) {
        // Strict non-overlap: require at least one dimension to be strictly separated
        // x2 >= x1 + w1  OR  x1 >= x2 + w2  OR
        // y2 >= y1 + h1  OR  y1 >= y2 + h2
        // Using strict > for the separation to ensure proper containment
        if (!(anc.x + w <= pl.x || anc.x >= pl.x + pl.pw ||
              anc.y + h <= pl.y || anc.y >= pl.y + pl.ph)) {
            return false;
        }
    }
    return true;
}

// ============================================================
// Anchor management
// ============================================================

// Add new anchor points from a placed rectangle.
// Two candidate anchors: right edge and top edge.
static void maybe_add_anchor(vector<AnchorPoint>& anchors,
                             const Instance& inst,
                             int x, int y) {
    if (x >= 0 && x < inst.W && y >= 0 && y < inst.H) {
        anchors.push_back({x, y});
    }
}

void RectangleSolver::add_anchors_from_placement(const Rect& r) {
    int old_size = (int)anchors.size();
    maybe_add_anchor(anchors, inst, r.x + r.pw, r.y);
    maybe_add_anchor(anchors, inst, r.x, r.y + r.ph);
    // Deduplicate
    sort(anchors.begin() + old_size, anchors.end());
    anchors.erase(unique(anchors.begin() + old_size, anchors.end()), anchors.end());
    // Merge old and new halves (new anchors are at the end)
    inplace_merge(anchors.begin(), anchors.begin() + old_size, anchors.end());
}

// Restore anchors to a given previous size (for backtracking)
static void restore_anchors(vector<AnchorPoint>& anchors, size_t prev_size) {
    if (anchors.size() > prev_size) anchors.resize(prev_size);
}

// ============================================================
// Pruning
// ============================================================
bool RectangleSolver::prune_by_area(int depth) {
    int remaining_area = inst.W * inst.H;
    for (const auto& r : placed) remaining_area -= r.pw * r.ph;
    int needed_area = 0;
    for (size_t i = depth; i < unplaced.size(); ++i)
        needed_area += unplaced[i].w * unplaced[i].h;
    if (needed_area > remaining_area) {
        ++stat_pruned_area;
        return true;
    }
    return false;
}

bool RectangleSolver::prune_by_infeasible(int depth) {
    for (size_t i = depth; i < unplaced.size(); ++i) {
        const Rect& r = unplaced[i];
        bool can_fit = false;
        for (size_t ai = 0; ai < anchors.size(); ++ai) {
            if (can_place(r, (int)ai, false)) { can_fit = true; break; }
            if (inst.allow_rotation && can_place(r, (int)ai, true)) { can_fit = true; break; }
        }
        if (!can_fit) {
            ++stat_pruned_infeasible;
            return true;
        }
    }
    return false;
}

bool RectangleSolver::prune_by_symmetry(int depth, const Rect& r) {
    (void)r;
    // Fix the first (largest area) rectangle at (0,0)
    if (placed.empty() && depth == 0) {
        if (!anchors.empty() && (anchors[0].x > 0 || anchors[0].y > 0)) {
            ++stat_pruned_symmetry;
            return true;
        }
    }
    return false;
}

// ============================================================
// Local search
// ============================================================
bool RectangleSolver::local_search_from_partial() {
    ++stat_local_search_calls;
    auto now = duration_cast<microseconds>(
        steady_clock::now().time_since_epoch()).count();

    vector<Rect> saved_placed = placed;
    vector<Rect> saved_unplaced = unplaced;
    vector<AnchorPoint> saved_anchors = anchors;

    mt19937 rng(12345 + (int)(now & 0xFFFF));

    for (int attempt = 0; attempt < 20; ++attempt) {
        vector<Rect> trial_placed = saved_placed;
        vector<Rect> trial_unplaced = saved_unplaced;
        vector<AnchorPoint> trial_anchors = saved_anchors;
        shuffle(trial_unplaced.begin(), trial_unplaced.end(), rng);

        bool ok = true;
        for (const Rect& r : trial_unplaced) {
            bool placed_r = false;
            // Shuffle anchors to avoid bias
            vector<int> order(trial_anchors.size());
            iota(order.begin(), order.end(), 0);
            shuffle(order.begin(), order.end(), rng);

            for (int ai : order) {
                const AnchorPoint& anc = trial_anchors[ai];
                // Try non-rotated
                {
                    int w = r.w, h = r.h;
                    if (anc.x + w <= inst.W && anc.y + h <= inst.H) {
                        bool overlap = false;
                        for (const auto& pl : trial_placed) {
                            if (!(anc.x + w <= pl.x || anc.x >= pl.x + pl.pw ||
                                  anc.y + h <= pl.y || anc.y >= pl.y + pl.ph)) {
                                overlap = true; break;
                            }
                        }
                        if (!overlap) {
                            Rect pr = r; pr.x = anc.x; pr.y = anc.y;
                            pr.pw = w; pr.ph = h; pr.rotated = false;
                            trial_placed.push_back(pr);
                            maybe_add_anchor(trial_anchors, inst, pr.x + pr.pw, pr.y);
                            maybe_add_anchor(trial_anchors, inst, pr.x, pr.y + pr.ph);
                            sort(trial_anchors.begin(), trial_anchors.end());
                            trial_anchors.erase(unique(trial_anchors.begin(), trial_anchors.end()), trial_anchors.end());
                            placed_r = true; break;
                        }
                    }
                }
                // Try rotated
                if (!placed_r && inst.allow_rotation && r.w != r.h) {
                    int w = r.h, h = r.w;
                    if (anc.x + w <= inst.W && anc.y + h <= inst.H) {
                        bool overlap = false;
                        for (const auto& pl : trial_placed) {
                            if (!(anc.x + w <= pl.x || anc.x >= pl.x + pl.pw ||
                                  anc.y + h <= pl.y || anc.y >= pl.y + pl.ph)) {
                                overlap = true; break;
                            }
                        }
                        if (!overlap) {
                            Rect pr = r; pr.x = anc.x; pr.y = anc.y;
                            pr.pw = w; pr.ph = h; pr.rotated = true;
                            trial_placed.push_back(pr);
                            maybe_add_anchor(trial_anchors, inst, pr.x + pr.pw, pr.y);
                            maybe_add_anchor(trial_anchors, inst, pr.x, pr.y + pr.ph);
                            sort(trial_anchors.begin(), trial_anchors.end());
                            trial_anchors.erase(unique(trial_anchors.begin(), trial_anchors.end()), trial_anchors.end());
                            placed_r = true; break;
                        }
                    }
                }
            }
            if (!placed_r) { ok = false; break; }
        }
        if (ok) {
            ++stat_local_search_successes;
            found_solution = true;
            best_sol.sat = true;
            best_sol.rects = trial_placed;
            return true;
        }
    }
    return false;
}

// ============================================================
// Main search
// ============================================================
bool RectangleSolver::search(int depth) {
    if (deadline_reached()) return false;
    ++stat_recursive_calls;
    update_stats_depth(depth);

    if (depth == (int)unplaced.size()) {
        found_solution = true;
        best_sol.sat = true;
        best_sol.rects = placed;
        return true;
    }

    const Rect& r = unplaced[depth];

    // Pruning
    if (prune_by_area(depth)) return false;
    if (prune_by_infeasible(depth)) return false;
    if (prune_by_symmetry(depth, r)) return false;

    // Trigger local search when stuck
    if (use_local_search && depth > 3 && stat_recursive_calls > 1000) {
        auto now = duration_cast<microseconds>(
            steady_clock::now().time_since_epoch()).count();
        if (now - last_progress_us > 500000) {
            last_progress_us = now;
            if (local_search_from_partial()) return true;
        }
    }

    // Try each anchor point
    for (size_t ai = 0; ai < anchors.size(); ++ai) {
        // Save anchor count BEFORE placing (needed for backtracking)
        size_t saved_anchor_count = anchors.size();

        // Try non-rotated
        if (can_place(r, (int)ai, false)) {
            Rect pr;
            const AnchorPoint& anc = anchors[ai];
            pr = r; pr.x = anc.x; pr.y = anc.y;
            pr.pw = r.w; pr.ph = r.h; pr.rotated = false;
            placed.push_back(pr);
            add_anchors_from_placement(pr);
            ++stat_placements_tried;
            if (search(depth + 1)) return true;
            // Backtrack: restore exact state
            placed.pop_back();
            restore_anchors(anchors, saved_anchor_count);
            ++stat_backtracks;
        }

        // Try rotated
        if (inst.allow_rotation && r.w != r.h) {
            if (can_place(r, (int)ai, true)) {
                Rect pr;
                const AnchorPoint& anc = anchors[ai];
                pr = r; pr.x = anc.x; pr.y = anc.y;
                pr.pw = r.h; pr.ph = r.w; pr.rotated = true;
                placed.push_back(pr);
                add_anchors_from_placement(pr);
                ++stat_placements_tried;
                if (search(depth + 1)) return true;
                placed.pop_back();
                restore_anchors(anchors, saved_anchor_count);
                ++stat_backtracks;
            }
        }
    }

    return false;
}

// ============================================================
// Public solve
// ============================================================
Solution RectangleSolver::solve() {
    reset_stats();
    unplaced = inst.rectangles;
    placed.clear();
    anchors.clear();
    anchors.push_back({0, 0});
    found_solution = false;
    best_sol = Solution();

    // Sort by heuristic (pre-place largest first)
    switch (heuristic) {
        case BranchHeuristic::AREA_DESC:
            sort(unplaced.begin(), unplaced.end(), heuristic_compare_area);
            break;
        case BranchHeuristic::MAX_DIM_DESC:
            sort(unplaced.begin(), unplaced.end(), heuristic_compare_maxdim);
            break;
        case BranchHeuristic::FEWEST_CANDIDATES:
            sort(unplaced.begin(), unplaced.end(), heuristic_compare_area);
            break;
    }

    auto start = steady_clock::now();
    deadline_us = duration_cast<microseconds>(start.time_since_epoch()).count()
                  + (int64_t)time_limit_ms * 1000;
    last_progress_us = duration_cast<microseconds>(start.time_since_epoch()).count();

    // Quick area check
    int total_area = inst.total_area();
    if (total_area > inst.W * inst.H) {
        auto end = steady_clock::now();
        best_sol.runtime_ms = duration_cast<microseconds>(end - start).count() / 1000.0;
        best_sol.sat = false;
    } else {
        search(0);
        auto end = steady_clock::now();
        best_sol.runtime_ms = duration_cast<microseconds>(end - start).count() / 1000.0;
    }

    best_sol.recursive_calls = stat_recursive_calls;
    best_sol.backtracks = stat_backtracks;
    best_sol.placements_tried = stat_placements_tried;
    best_sol.pruned_by_area = stat_pruned_area;
    best_sol.pruned_by_infeasible = stat_pruned_infeasible;
    best_sol.pruned_by_symmetry = stat_pruned_symmetry;
    best_sol.local_search_calls = stat_local_search_calls;
    best_sol.local_search_successes = stat_local_search_successes;
    best_sol.max_depth = stat_max_depth;

    return best_sol;
}
