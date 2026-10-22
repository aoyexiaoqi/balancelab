# 算法说明 / Algorithms

BalanceLab 求解的是经典的单型号装配线平衡问题（SALBP-1）：给定节拍
（takt / cycle time），把带优先约束的任务分配到工位，使每个工位负荷
不超过节拍，且工位数尽量少。

BalanceLab solves SALBP-1: assign precedence-constrained tasks to stations
so no station load exceeds the takt and the station count is minimized.

## 指标 / Metrics

- **平衡率 Efficiency** = 总工时 /（工位数 × 节拍）
- **平衡损失 Balance delay** = 1 − 平衡率
- **平滑指数 Smoothness index** = √(Σ(max_load − load_i)²)，越小越均匀
- **瓶颈工位 Bottleneck** = 负荷最大的工位
- **理论最少工位数** = ceil（总工时 / 节拍），是任何方案的下界

## 方法 / Methods

### greedy-rpw（贪心 + 位置权重）
按 Ranked Positional Weight（任务工时 + 全部后继任务工时之和）从高到低，
依次把"前序已分配且放得进当前工位"的任务装入当前工位，装不下就开新工位。
确定性、可复现，是其余方法的起点。

### local-search（局部搜索改进）
在贪心解上迭代两类邻域动作：单任务迁移与任务对交换。动作必须同时满足
优先约束的工位窗口（前序工位 ≤ 本工位 ≤ 后继工位）和节拍上限；目标函数
先比工位数、再比平滑指数。只接受严格改进，因此结果不会比贪心差，
且全程保持可行——不满足约束的解不会被输出。

### cpsat（可选，精确解）
安装 `ortools` 后可用（`pip install balancelab[optimize]`）。用 CP-SAT
建模：布尔变量 x[任务，工位]、工位启用变量 y[工位]，约束含每任务恰属一
工位、工位负荷 ≤ 节拍、优先序的工位单调性，目标最小化启用工位数；
工位上界取贪心解。小/中规模可证最优。未安装 ortools 时该方法在报告中
标记为 `unavailable`，其余功能不受影响。

## 可行性不变量 / Invariants

所有求解器的输出都经过 `verify()` 校验：每任务恰分配一次、优先约束
不被违反、工位负荷不超节拍。单任务工时大于节拍时问题本身无解，
求解器会显式报告不可行（InfeasibleError），而不是给出违规方案。
