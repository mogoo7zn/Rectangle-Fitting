# Rectangle Fitting Solver

形式化方法导引课程大作业：分别使用 Z3 SMT 求解器和自定义算法实现 Rectangle Fitting（矩形装箱/矩形布局）问题求解。

## 项目结构

```
project/
├── README.md                  # 本文件
├── report.md                  # 实验报告
├── requirements.txt           # Python 依赖
├── CMakeLists.txt             # C++ 构建配置
├── src/
│   ├── common/
│   │   ├── instance_io.hpp    # C++ 实例/解数据结构
│   │   ├── instance_io.cpp    # C++ I/O 实现
│   │   └── instance_io.py    # Python I/O 工具
│   ├── z3_solver/
│   │   └── solver_z3.py       # Z3 SMT 求解器实现
│   ├── custom_solver/
│   │   ├── solver.hpp         # 自定义求解器头文件
│   │   ├── solver.cpp         # 主搜索算法实现
│   │   ├── main.cpp           # C++ 程序入口
│   │   ├── state.cpp          # 状态管理
│   │   ├── heuristics.cpp     # 启发式算法
│   │   └── local_search.cpp   # 局部搜索模块
│   └── tools/
│       ├── gen_cases.py       # 测试数据集生成器
│       ├── benchmark.py        # 基准测试脚本
│       ├── visualize.py        # 可视化脚本
│       └── summarize_results.py # 结果汇总脚本
├── data/
│   ├── manual/                # 手工测试用例
│   └── generated/             # 自动生成测试用例
├── docs/
│   ├── design.md              # 算法详细设计
│   └── benchmark.md           # 测试集与性能分析
└── results/
    ├── raw/                   # 原始 CSV 结果
    ├── tables/                # 汇总表格
    └── figures/               # 可视化图片
```

## 环境配置

### Python 环境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### C++ 编译

```bash
mkdir build && cd build
cmake ..
make -j$(nproc)
```

## 输入格式

统一使用 JSON 格式：

```json
{
  "container": {"W": 20, "H": 15},
  "allow_rotation": true,
  "rectangles": [
    {"id": 1, "w": 4, "h": 6},
    {"id": 2, "w": 3, "h": 5}
  ]
}
```

## 运行方式

### Z3 求解器

```bash
# 基本用法
python3 src/z3_solver/solver_z3.py data/manual/tiny_sat.json

# 指定输出文件
python3 src/z3_solver/solver_z3.py data/manual/medium_sat.json -o output.json

# 禁用旋转
python3 src/z3_solver/solver_z3.py data/manual/medium_sat.json --no-rotation

# 禁用对称性破缺优化
python3 src/z3_solver/solver_z3.py data/manual/medium_sat.json --no-symmetry

# 设置超时（毫秒）
python3 src/z3_solver/solver_z3.py data/manual/hard_sat.json --timeout 10000
```

### 自定义求解器

```bash
# 基本用法
./build/solver_custom data/manual/tiny_sat.json

# 指定输出文件
./build/solver_custom data/manual/medium_sat.json -o output.json

# 选择启发式（area | dim | candidates）
./build/solver_custom data/manual/hard_sat.json -H dim

# 禁用局部搜索
./build/solver_custom data/manual/hard_sat.json --no-ls

# 设置超时
./build/solver_custom data/manual/hard_sat.json -t 10000

# 禁用旋转
./build/solver_custom data/manual/medium_sat.json --no-rot
```

### 生成测试用例

```bash
# 生成三档测试集（easy / medium / hard）
python3 src/tools/gen_cases.py -o data/generated

# 指定随机种子
python3 src/tools/gen_cases.py -o data/generated --seed 2024
```

### 基准测试

```bash
# 运行全部求解器对比
python3 src/tools/benchmark.py \
    --input-dir data/generated \
    --output results/raw/benchmark_results.csv

# 指定求解器
python3 src/tools/benchmark.py \
    --input-dir data/generated \
    --solvers z3,custom \
    --repeats 3 \
    --timeout 30000
```

### 可视化

```bash
# 可视化解结果
python3 src/tools/visualize.py data/manual/medium_sat.json \
    --solution output.json \
    -o results/figures/medium_sat.png
```

### 结果汇总

```bash
python3 src/tools/summarize_results.py results/raw/benchmark_results.csv \
    -o results/tables
```

## 完整流程示例

```bash
# 1. 创建虚拟环境并安装依赖
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. 编译 C++ 求解器
mkdir -p build && cd build && cmake .. && make -j4 && cd ..

# 3. 生成测试集
python3 src/tools/gen_cases.py -o data/generated

# 4. 运行基准测试
python3 src/tools/benchmark.py \
    --input-dir data/generated \
    --output results/raw/benchmark_results.csv \
    --repeats 1

# 5. 汇总结果
python3 src/tools/summarize_results.py results/raw/benchmark_results.csv \
    -o results/tables

# 6. 可视化部分解
python3 src/tools/visualize.py data/manual/hard_sat.json -o results/figures/hard_sat.png
```

## 输出格式

Z3 和自定义求解器均输出以下 JSON 格式：

```json
{
  "result": "sat",
  "runtime_ms": 15.234,
  "rectangles": [
    {"id": 1, "x": 0, "y": 0, "w": 4, "h": 6, "rotated": false},
    {"id": 2, "x": 4, "y": 0, "w": 5, "h": 3, "rotated": true}
  ],
  "stats": {
    "recursive_calls": 1234,
    "backtracks": 456,
    "placements_tried": 2345,
    "pruned_by_area": 100,
    "pruned_by_infeasible": 50,
    "pruned_by_symmetry": 10,
    "local_search_calls": 5,
    "local_search_successes": 2,
    "max_depth": 10
  }
}
```

## 测试用例说明

- `data/manual/` : 手工设计的小规模精确样例
  - `tiny_sat.json` - 极简可满足实例
  - `tiny_unsat.json` - 明显不可满足实例
  - `medium_sat.json` - 中等可满足实例
  - `medium_unsat.json` - 中等不可满足实例
  - `hard_sat.json` - 较难可满足实例
  - `rotation_needed.json` - 必须旋转才能满足的实例
  - `no_rotation.json` - 禁用旋转的对照实例

- `data/generated/` : 自动生成的测试集（easy / medium / hard）
