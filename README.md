# BalanceLab

智能生产线平衡与瓶颈优化工具：给定带优先约束的工序标准工时与节拍，
自动把工序分配到工位，并对比贪心、局部搜索与精确求解（可选）的平衡效果。

Assembly line balancing and bottleneck optimization toolkit. Given task
standard times, precedence constraints and a takt time, BalanceLab assigns
tasks to stations and compares a greedy heuristic, a local-search improver
and (optionally) an exact CP-SAT solver.

## 功能 / Features

- 输入 CSV / JSON 工序清单（工序号、名称、标准工时、前序工序）
- 节拍可直接给定，或由可用时间 ÷ 需求量自动计算
- 三种求解方法，结果同表对比：
  - **greedy-rpw**：位置权重（Ranked Positional Weight）贪心
  - **local-search**：在贪心解上做任务迁移/交换的局部搜索改进
  - **cpsat**：OR-Tools CP-SAT 精确求解（可选依赖，小/中规模可证最优）
- 指标：工位数、每工位负荷、平衡率、平滑指数、瓶颈工位、闲置时间
- 输出 Markdown / JSON 报告；可选 Plotly 工位负荷图（HTML）
- 硬性保证：任何求解器输出都不违反优先约束、不超过节拍；
  单工序工时大于节拍时显式报告不可行

## 安装 / Install

```bash
pip install -e .                 # 核心（仅依赖 numpy）
pip install -e ".[optimize]"    # + OR-Tools 精确求解
pip install -e ".[plot]"         # + Plotly 图表
```

需要 Python ≥ 3.9。核心功能在没有 ortools / plotly 时完全可用。

## 使用 / Usage

```bash
# 内置演示（合成示例数据）
balancelab --demo

# 求解自己的工序清单
balancelab solve tasks.csv --takt 60 --out report.md --json-out report.json

# 用可用时间与需求量推节拍（27000 秒 / 450 件 = 60 秒/件）
balancelab solve tasks.csv --available-time 27000 --demand 450 --out report.md

# 生成工位负荷图（需要 plotly）
balancelab solve tasks.csv --takt 60 --chart loads.html
```

输入格式见 `examples/tasks15.csv`：

```csv
id,name,time,predecessors
T01,Base frame prep,42,
T03,Gearbox fit,36,T01
T04,Shaft assembly,28,"T01,T02"
```

JSON 格式见 `examples/tasks15.json`，可在文件中内嵌 `"takt"`。

## 示例数据说明 / Example data

`examples/` 与 `--demo` 使用同一份 **合成示例数据**（15 个工序、总工时
495、节拍 60、理论下界 9 个工位），并非真实产线数据，仅用于演示与
回归测试。该例的精确最优为 10 个工位（经 CP-SAT 验证），三种方法均
达到 10 工位、平衡率 82.5%；局部搜索进一步把平滑指数由 39.99 降到
39.48。真实场景中贪心与最优之间的差距会随数据而变，下界也不总能达到
（工序不可分割 + 优先约束）。

| Method | Stations | Efficiency | Smoothness |
|---|---|---|---|
| greedy-rpw | 10 | 82.5% | 39.99 |
| local-search | 10 | 82.5% | 39.48 |
| cpsat (optimal) | 10 | 82.5% | 44.46 |

算法细节见 [docs/algorithms.md](docs/algorithms.md)。

## 作为库使用 / Library use

```python
from balancelab import load_problem, solve_greedy, solve_local

problem = load_problem("tasks.csv", takt=60)
greedy = solve_greedy(problem)
better = solve_local(problem, start=greedy)
print(better.n_stations, better.efficiency, better.bottleneck_station)
```

## 开发 / Development

```bash
pip install -e . pytest pytest-cov
pytest --cov=balancelab tests/
```

核心测试套件不需要 ortools 与 plotly；装有 ortools 时会额外运行
CP-SAT 一致性测试。

## License

MIT
