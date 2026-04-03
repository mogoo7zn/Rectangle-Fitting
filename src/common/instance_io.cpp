#include "instance_io.hpp"
#include <fstream>
#include <sstream>
#include <iostream>
#include <algorithm>
#include <cctype>

static std::string trim(const std::string& s) {
    size_t a = 0, b = s.size();
    while (a < b && std::isspace((unsigned char)s[a])) ++a;
    while (b > a && std::isspace((unsigned char)s[b-1])) --b;
    return s.substr(a, b-a);
}

static bool read_token(std::istream& is, std::string& tok) {
    tok.clear();
    char c;
    while (is.get(c)) {
        if (std::isspace((unsigned char)c)) continue;
        if (c == '{' || c == '}' || c == '[' || c == ']' ||
            c == ':' || c == ',' || c == '"') {
            tok = c;
            return true;
        }
        tok += c;
        while (is.get(c) && !std::isspace((unsigned char)c) &&
               c != '{' && c != '}' && c != '[' && c != ']' &&
               c != ':' && c != ',' && c != '"') {
            tok += c;
        }
        if (is) is.putback(c);
        return true;
    }
    return false;
}

Instance read_instance(const std::string& path) {
    std::ifstream f(path);
    if (!f) { std::cerr << "Cannot open " << path << "\n"; return Instance(); }
    std::stringstream ss;
    ss << f.rdbuf();
    std::string content = ss.str();
    f.close();

    Instance inst;
    inst.allow_rotation = true;

    // parse container
    size_t cW = content.find("\"W\"");
    size_t cH = content.find("\"H\"");
    if (cW != std::string::npos) {
        size_t p = content.find_first_of("0123456789", cW+3);
        if (p != std::string::npos) {
            int val = 0;
            while (p < content.size() && std::isdigit((unsigned char)content[p])) {
                val = val*10 + (content[p]-'0'); ++p;
            }
            inst.W = val;
        }
    }
    if (cH != std::string::npos) {
        size_t p = content.find_first_of("0123456789", cH+3);
        if (p != std::string::npos) {
            int val = 0;
            while (p < content.size() && std::isdigit((unsigned char)content[p])) {
                val = val*10 + (content[p]-'0'); ++p;
            }
            inst.H = val;
        }
    }

    // parse allow_rotation
    size_t ar = content.find("\"allow_rotation\"");
    if (ar != std::string::npos) {
        size_t tc = content.find("true", ar);
        size_t fc = content.find("false", ar);
        if (tc != std::string::npos && (fc == std::string::npos || tc < fc)) {
            inst.allow_rotation = true;
        } else if (fc != std::string::npos) {
            inst.allow_rotation = false;
        }
    }

    // parse rectangles
    size_t rpos = content.find("\"rectangles\"");
    if (rpos != std::string::npos) {
        size_t start = content.find('[', rpos);
        size_t end = content.find(']', rpos);
        if (start != std::string::npos && end != std::string::npos) {
            std::string rects_str = content.substr(start+1, end-start-1);
            size_t pos = 0;
            while (pos < rects_str.size()) {
                size_t obj_start = rects_str.find('{', pos);
                if (obj_start == std::string::npos) break;
                size_t obj_end = rects_str.find('}', obj_start);
                if (obj_end == std::string::npos) break;
                std::string obj = rects_str.substr(obj_start+1, obj_end-obj_start-1);
                
                Rect rect;
                rect.id = 0; rect.w = 0; rect.h = 0;
                
                size_t p2 = 0;
                while (p2 < obj.size()) {
                    size_t ck = obj.find("\"", p2);
                    if (ck == std::string::npos) break;
                    size_t colon = obj.find(":", ck);
                    size_t q2 = obj.find("\"", ck+1);
                    if (colon == std::string::npos || q2 == std::string::npos || q2 > colon) break;
                    std::string key = obj.substr(ck+1, q2-ck-1);
                    
                    size_t val_start = obj.find_first_of("0123456789", colon);
                    if (val_start == std::string::npos) { p2 = obj_end; break; }
                    int val = 0;
                    while (val_start < obj.size() && std::isdigit((unsigned char)obj[val_start])) {
                        val = val*10 + (obj[val_start]-'0'); ++val_start;
                    }
                    
                    if (key == "id") rect.id = val;
                    else if (key == "w") rect.w = val;
                    else if (key == "h") rect.h = val;
                    p2 = val_start;
                }
                
                if (rect.id > 0 && rect.w > 0 && rect.h > 0) {
                    rect.pw = rect.w; rect.ph = rect.h; rect.rotated = false;
                    inst.rectangles.push_back(rect);
                }
                pos = obj_end + 1;
            }
        }
    }
    return inst;
}

void write_solution_json(std::ostream& os, const Solution& sol, const Instance& inst) {
    os << "{\n";
    os << "  \"result\": \"" << (sol.sat ? "sat" : "unsat") << "\",\n";
    os << "  \"runtime_ms\": " << sol.runtime_ms << ",\n";
    if (sol.sat) {
        os << "  \"rectangles\": [\n";
        for (size_t i = 0; i < sol.rects.size(); ++i) {
            const Rect& r = sol.rects[i];
            os << "    {\"id\": " << r.id
               << ", \"x\": " << r.x << ", \"y\": " << r.y
               << ", \"w\": " << r.pw << ", \"h\": " << r.ph
               << ", \"rotated\": " << (r.rotated ? "true" : "false") << "}";
            if (i+1 < sol.rects.size()) os << ",";
            os << "\n";
        }
        os << "  ],\n";
    }
    os << "  \"stats\": {\n";
    os << "    \"recursive_calls\": " << sol.recursive_calls << ",\n";
    os << "    \"backtracks\": " << sol.backtracks << ",\n";
    os << "    \"placements_tried\": " << sol.placements_tried << ",\n";
    os << "    \"pruned_by_area\": " << sol.pruned_by_area << ",\n";
    os << "    \"pruned_by_infeasible\": " << sol.pruned_by_infeasible << ",\n";
    os << "    \"pruned_by_symmetry\": " << sol.pruned_by_symmetry << ",\n";
    os << "    \"local_search_calls\": " << sol.local_search_calls << ",\n";
    os << "    \"local_search_successes\": " << sol.local_search_successes << ",\n";
    os << "    \"max_depth\": " << sol.max_depth << "\n";
    os << "  }\n}\n";
}

void write_solution_json(const std::string& path, const Solution& sol, const Instance& inst) {
    std::ofstream f(path);
    write_solution_json(f, sol, inst);
    f.close();
}
