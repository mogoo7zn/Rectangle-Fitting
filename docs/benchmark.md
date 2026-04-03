# 测试集设计与性能对比说明

## 1. 测试集设计原则

### 1.1 三档难度

| 难度 | 矩形数量 | 面积占用率 | 特征 | 预期 |
|------|---------|-----------|------|------|
| Easy | 5~10 | 50%~75% | 明显可行布局 | 两个求解器均快速 |
| Medium | 10~20 | 65%~85% | 需一定搜索 | Z3 仍快，Custom 有竞争力 |
| Hard | 20~35 | 80%~98% | 高填充率/对称冲突 | 差异明显 |

### 1.2 实例类型

每个难度级别包含：
- **SAT 实例**：可满足，需找到布局
- **UNSAT 实例**：不可满足（面积超限 or 形状冲突）

### 1.3 可复现性

- 所有实例通过固定随机种子生成
- 同一实例多次运行结果可复现
- 脚本位于 `src/tools/gen_cases.py`

## 2. 性能指标

### 2.1 主要指标

- **求解时间 (runtime_ms)**：从输入到输出的总时间
- **成功率**：在超时前返回正确结果的比例
- **解质量**：SAT 实例是否找到解

### 2.2 自定义算法额外指标

- **递归调用次数**：搜索树规模
- **回溯次数**：搜索复杂度
- **剪枝效率**：各剪枝触发的绝对次数
- **局部搜索贡献**：调用次数与成功率

## 3. 预期实验现象

### Z3 的典型行为

- 小规模（n ≤ 10）：极快（< 50ms），SMT 建模直观
- 中等规模（10 < n ≤ 20）：Z3 仍表现良好
- 大规模（n > 20）：约束数量 O(n²) 增长，Z3 搜索空间剧增

### 自定义算法典型行为

- 基础回溯（无剪枝）：在小规模即可能超时
- 加入剪枝后：在规则化数据（大量相似尺寸）上表现优于 Z3
- 局部搜索：在陷入局部极小时提供跳出机制

## 4. 基准测试脚本使用

```bash
# 基本运行
python3 src/tools/benchmark.py \
    --input-dir data/generated \
    --output results/raw/benchmark.csv

# 多轮重复取中位数
python3 src/tools/benchmark.py \
    --input-dir data/generated \
    --output results/raw/benchmark.csv \
    --repeats 3

# 仅测试 Z3
python3 src/tools/benchmark.py \
    --input-dir data/manual \
    --solvers z3 \
    --timeout 5000

# 仅测试自定义算法（指定启发式）
python3 src/tools/benchmark.py \
    --input-dir data/generated/hard \
    --solvers custom \
    --heuristic dim \
    --timeout 30000
```

## 5. 结果解读

结果汇总在 `results/tables/` 目录下：
- `summary.csv` — 每个实例的中位数运行时间
- `benchmark_report.md` — Markdown 格式报告，含统计表格

关注：
1. 同一实例两个求解器的速度比
2. unsat 实例两个求解器的对比（Z3 可能更快证明无解）
3. 自定义算法各剪枝的触发频率（指导进一步优化）
4. 局部搜索的实际贡献（调用/成功比）
