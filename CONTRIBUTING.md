# Contributing

## 开发环境

### 依赖

- Python 3.10+
- z3-solver
- C++17 编译器 (g++ / clang++)
- CMake 3.15+

### 安装依赖

```bash
# Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# C++ 编译
mkdir build && cd build
cmake ..
make -j$(nproc)
```

## 代码规范

- Python: 遵循 PEP 8，使用 4 空格缩进
- C++: 遵循 C++17 标准，注释使用英语或中文
- 所有核心函数必须有文档字符串或注释

## 测试

```bash
# 运行 Python 测试
python3 tests/test_z3.py
python3 tests/test_custom.py

# 基准测试
python3 src/tools/gen_cases.py -o data/generated
python3 src/tools/benchmark.py --input-dir data/generated \
    --output results/raw/benchmark_results.csv
```

## 提交流程

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/xxx`)
3. 编写代码并测试
4. 提交 (`git commit -m 'Add: xxx'`)
5. 推送到你的 Fork
6. 创建 Pull Request
