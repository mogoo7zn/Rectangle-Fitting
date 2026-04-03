#include "solver.hpp"
#include "../common/instance_io.hpp"
#include <iostream>
#include <fstream>
#include <cstring>

void print_usage(const char* prog) {
    std::cerr << "Usage: " << prog << " <input.json> [options]\n"
              << "Options:\n"
              << "  -o FILE      output solution JSON\n"
              << "  -t MS        timeout in milliseconds (default 30000)\n"
              << "  -H TYPE      heuristic: area|dim|candidates (default area)\n"
              << "  --no-ls      disable local search\n"
              << "  --no-rot     disable rotation\n";
}

int main(int argc, char** argv) {
    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    const char* input_path = argv[1];
    const char* output_path = nullptr;
    int timeout_ms = 30000;
    BranchHeuristic heur = BranchHeuristic::AREA_DESC;
    bool use_ls = true;
    bool allow_rotation = true;

    for (int i = 2; i < argc; ++i) {
        if (strcmp(argv[i], "-o") == 0 && i+1 < argc) {
            output_path = argv[++i];
        } else if (strcmp(argv[i], "-t") == 0 && i+1 < argc) {
            timeout_ms = atoi(argv[++i]);
        } else if (strcmp(argv[i], "-H") == 0 && i+1 < argc) {
            ++i;
            if (strcmp(argv[i], "area") == 0) heur = BranchHeuristic::AREA_DESC;
            else if (strcmp(argv[i], "dim") == 0) heur = BranchHeuristic::MAX_DIM_DESC;
            else if (strcmp(argv[i], "candidates") == 0) heur = BranchHeuristic::FEWEST_CANDIDATES;
            else { std::cerr << "Unknown heuristic: " << argv[i] << "\n"; return 1; }
        } else if (strcmp(argv[i], "--no-ls") == 0) {
            use_ls = false;
        } else if (strcmp(argv[i], "--no-rot") == 0) {
            allow_rotation = false;
        } else {
            std::cerr << "Unknown option: " << argv[i] << "\n";
            print_usage(argv[0]);
            return 1;
        }
    }

    Instance inst = read_instance(input_path);
    if (inst.W == 0) { std::cerr << "Failed to load instance\n"; return 1; }
    inst.allow_rotation = allow_rotation;

    RectangleSolver solver(inst, heur, timeout_ms, use_ls);
    Solution sol = solver.solve();

    if (output_path) {
        write_solution_json(output_path, sol, inst);
    } else {
        write_solution_json(std::cout, sol, inst);
    }

    std::cerr << "Result: " << (sol.sat ? "sat" : "unsat")
              << "  Runtime: " << sol.runtime_ms << " ms\n";
    std::cerr << "Stats: recursive=" << sol.recursive_calls
              << " backtracks=" << sol.backtracks
              << " placements=" << sol.placements_tried
              << " max_depth=" << sol.max_depth << "\n";

    return 0;
}
