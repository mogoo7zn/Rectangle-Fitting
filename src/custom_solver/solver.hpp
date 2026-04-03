#ifndef SOLVER_HPP
#define SOLVER_HPP

#include "../common/instance_io.hpp"
#include <vector>
#include <set>
#include <map>

enum class BranchHeuristic {
    AREA_DESC,        // largest area first
    MAX_DIM_DESC,     // larger max dimension first
    FEWEST_CANDIDATES // fewest placement options first (dynamic)
};

struct AnchorPoint {
    int x, y;
    bool operator<(AnchorPoint const& other) const {
        if (x != other.x) return x < other.x;
        return y < other.y;
    }
    bool operator==(AnchorPoint const& other) const {
        return x == other.x && y == other.y;
    }
};

class RectangleSolver {
public:
    Instance inst;
    BranchHeuristic heuristic;
    int time_limit_ms;
    bool use_local_search;

    RectangleSolver(const Instance& inst_, BranchHeuristic h = BranchHeuristic::AREA_DESC,
                    int time_limit_ms_ = 30000, bool use_ls = true);

    Solution solve();

    // stats (public for easy access)
    long long stat_recursive_calls;
    long long stat_backtracks;
    long long stat_placements_tried;
    long long stat_pruned_area;
    long long stat_pruned_infeasible;
    long long stat_pruned_symmetry;
    long long stat_local_search_calls;
    long long stat_local_search_successes;
    int stat_max_depth;

private:
    std::vector<Rect> unplaced;
    std::vector<Rect> placed;
    std::vector<AnchorPoint> anchors;
    std::vector<int> ordering;
    bool found_solution;
    Solution best_sol;
    int64_t deadline_us;
    int64_t last_progress_us;

    void reset_stats();
    bool deadline_reached() const;
    void update_stats_depth(int depth);

    // Core recursive search
    bool search(int depth);

    // Placement checks
    bool can_place(const Rect& r, int anchor_idx, bool try_rotate);

    // Anchor management
    void add_anchors_from_placement(const Rect& r);

    // Pruning
    bool prune_by_area(int depth);
    bool prune_by_infeasible(int depth);
    bool prune_by_symmetry(int depth, const Rect& r);

    // Heuristics
    void compute_ordering();
    static bool heuristic_compare_area(const Rect& a, const Rect& b);
    static bool heuristic_compare_maxdim(const Rect& a, const Rect& b);
    bool heuristic_compare_candidates(const Rect& a, const Rect& b);

    // Local search
    bool local_search_from_partial();
};

#endif // SOLVER_HPP
