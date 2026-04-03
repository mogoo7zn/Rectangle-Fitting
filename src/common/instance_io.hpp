#ifndef INSTANCE_IO_HPP
#define INSTANCE_IO_HPP

#include <string>
#include <vector>
#include <ostream>

struct Rect {
    int id;
    int w, h;       // original size
    int x, y;       // placed position
    int pw, ph;     // placed size (considering rotation)
    bool rotated;
    Rect() : id(0), w(0), h(0), x(0), y(0), pw(0), ph(0), rotated(false) {}
    Rect(int _id, int _w, int _h) : id(_id), w(_w), h(_h), x(0), y(0), pw(_w), ph(_h), rotated(false) {}
    int area() const { return w * h; }
};

struct Instance {
    int W, H;
    bool allow_rotation;
    std::vector<Rect> rectangles;
    Instance() : W(0), H(0), allow_rotation(true) {}
    int total_area() const {
        int s = 0;
        for (auto &r : rectangles) s += r.w * r.h;
        return s;
    }
};

struct Solution {
    bool sat;
    std::vector<Rect> rects;
    double runtime_ms;
    // statistics for custom solver
    long long recursive_calls;
    long long backtracks;
    long long placements_tried;
    long long pruned_by_area;
    long long pruned_by_infeasible;
    long long pruned_by_symmetry;
    long long local_search_calls;
    long long local_search_successes;
    int max_depth;
    Solution() : sat(false), runtime_ms(0), recursive_calls(0), backtracks(0),
        placements_tried(0), pruned_by_area(0), pruned_by_infeasible(0),
        pruned_by_symmetry(0), local_search_calls(0), local_search_successes(0), max_depth(0) {}
};

// Read from JSON format instance
Instance read_instance(const std::string& path);
void write_solution_json(std::ostream& os, const Solution& sol, const Instance& inst);
void write_solution_json(const std::string& path, const Solution& sol, const Instance& inst);

#endif // INSTANCE_IO_HPP
