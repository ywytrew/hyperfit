# HyperFit

[中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)

三语使用手册：[中文](docs/manual.zh.md) · [English](docs/manual.en.md) · [日本語](docs/manual.ja.md)。
三语部署教程：[中文](docs/deployment.zh.md) · [English](docs/deployment.en.md) · [日本語](docs/deployment.ja.md)，含 Windows、Linux/macOS、Docker Compose 与 SSH 远程访问。

网页顶部可切换语言，保留当前数据、参数、seed、运行任务和所选候选；也可通过 `?lang=zh`、`?lang=en`、`?lang=ja` 指定。浏览器记住语言偏好，导出 JSON 的科学字段名保持一致。

Joint calibration of stress and volume for isotropic hyperelastic materials.
Local research preview **0.1.0**, licensed **GPL-3.0-or-later**.

这是从部分抢救出的研究项目重新实现的独立版本。论文中的自定义体积项按公式重新实现，**不是原代码恢复，也不是论文实验结果复现**。公开内容为新代码、测试、文档与合成示例，不含原始实验或论文文件。

## Run locally / 本地启动

Windows 首次使用先按下面命令创建 `.venv` 并安装依赖。以后双击 `start.cmd`，或在 PowerShell 运行 `./start.ps1`。访问 <http://127.0.0.1:8765>；关闭运行窗口或按 Ctrl+C 停止服务。端口已占用时先检查已有服务，或用 `./start.ps1 -Port 8766`。

在其他机器安装（Python 3.11+，本次验证为 Windows / Python 3.12.14）：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-lock.txt
.\.venv\Scripts\python -m uvicorn hyperfit.api:app --host 127.0.0.1 --port 8765
```

Linux/macOS 对应使用 `.venv/bin/python`。尚未在这些平台实机验收。锁文件包含本次成功验证的依赖版本，正常开发不需要 Node、npm 或前端构建步骤。

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m hyperfit.verify --output validation-results/fem-verification.json
```

API 文档：<http://127.0.0.1:8765/docs>。Python 科学核心可直接导入，不依赖网页。前端通过 `/api/*` JSON 接口通信；文件存放在 `hyperfit/frontend/`，打包在 Python 包内只是为了方便本地启动。独立前端可在载入模块前设置 `window.HYPERFIT_API`；开发 CORS 已允许本机 5173 端口。

## Workflow / 使用流程

1. 载入明确标记的合成示例，或导入首行为列名的 CSV、TSV、XLSX。示例不是真实试验数据。
2. 明确选择轴向应变定义、应力定义、应力单位和体积定义；不得靠数值大小猜单位。
3. 组合偏应变项与体积项，检查参数范围和误差尺度；在“研究偏好与计算预算”中设置随机 seed、采样数量和起点数，也可切换到人工初值模式。
4. 联合拟合后检查两条响应曲线、低应变区、残差、收敛状态、边界命中和参数灵敏度。
5. 需要权重敏感性分析时启用“探索应力／体积折中”，再点击候选参数或散点切换结果。
6. 对所选材料运行有限元立方体检验，导出完整运行 JSON。记录含输入、参数、算法设置、依赖版本和科学源码哈希。

内部单位为 **MPa**，轴向应变为 **ln λ**，体积为 **ln J**，应力为 **Cauchy stress**。名义应力转换采用 `σ = P λ / J`。当前 UI 接受 4–3000 个严格递增的应变点；压缩支路需由用户明确按应变递增方向导出。程序不自动排序、删点、合并重复试验或混合加载/卸载。

## Initial guesses / 自动初值

旧流程实际采用人工输入起点。此版本默认在指定范围内做带 seed 的 Latin hypercube 采样（默认 48 组），正模量使用对数尺度，其他参数使用线性尺度。每组参数都求解完整的应力–体积耦合响应，排除无效状态，再按联合目标与参数距离选择多个优化起点。人工模式使用输入值作为第一个起点，其余起点在附近扰动。

seed 控制采样序列，**不能代替物理上合理的范围**。默认边界是通用演示范围，须按材料量级检查。Polynomial 允许部分系数为负，但要求正初始剪切模量和有效的横向平衡路径；Ogden 每个 α 区间不能跨过零。初值筛选不证明全局稳定，最终候选另作采样声学张量检查。

导出记录包含 seed、范围、采样筛选信息、所选初值及最终参数。同一输入、边界、seed 和依赖版本可复现；更换 seed 可检查对初值的敏感性。权重扫描复用同一组起点，避免把初值差异误认为权重效应。

## Energy combinations / 能量组合

偏应变项：Neo-Hookean、Mooney–Rivlin、二阶 Polynomial、Yeoh、Ogden 1/2/3 项。

体积项：

- `quadratic_J`: `K0/2 * (J−1)^2`
- `quadratic_logJ`: `K0/2 * (ln J)^2`
- `exponential_logJ`: `K0/(2β) * (exp(β(ln J)^2)−1)`；β=0 连续退化为上一项。
- `polynomial2_J`: `(J−1)^2/D1 + (J−1)^4/D2`

Ogden 采用 `Σ 2μ_i/α_i² (Σ λbar_k^α_i−3)` 约定，初始剪切模量为 `Σμ_i`。不要混用其他资料中的系数约定。默认正 μ 与交替正/负 α 搜索区间只是一种受限参数化，并不包含所有 Ogden 表示；可在参数边界中调整 α 区间，但不应跨越 α=0。项的置换会给出等价能量，不能据此宣称参数唯一。

材料点前向计算通过**横向应力为零**求解横向收缩和 J；没有预先施加不可压缩条件。其允许的求根区间和稳定性检查见 [方法说明](docs/methods.md)。

## Why not only RRMSE or Pareto? / 为什么不只换成帕累托

旧代码的 RRMSE 实际是 RMSE 除以曲线峰值。同样的绝对误差贡献相同，而同样的百分比误差在高应力区贡献更大。帕累托只能显示多个目标间的折中，不能修正各目标内部的误差尺度、数据定义或模型错误。

默认采用 `sqrt(a²+(b|y|)²)` 的绝对＋相对**容差尺度**，并按应变区间做梯形积分加权，防止密集采样区仅因点多而主导结果。可选择平方、Huber、soft-L1 损失；稳健变换在积分加权之前执行，使容差阈值不随采样密度变化。容差是研究偏好，**不是估计出来的噪声或置信区间**。

有可信的独立观测标准差时可选不确定度模式；平方损失此时对应指定噪声尺度下的加权最小二乘。误差相关、DIC 系统误差或横坐标测量误差目前没有建模。

折中功能以三个体积/应力权重比进行多起点局部搜索，显示**已探索候选集中的非支配解**。它不是 NSGA-II，不证明全局帕累托前沿，也不把“膝点”自动定义为科学上的最优参数。报告同时保留未加稳健权重的 RMSE、峰值 NRMSE、最大绝对误差与低应变区 RMSE。

## Verification and limits / 验证及边界

- FElupe 10.1.0，三维 u/p/J 混合有限元。自由收缩立方体与独立解析主应力计算对照；另外提供夹持非均匀算例和 Hex8、Hex27 加密比较。
- 自动测试覆盖能量导数、客观性、Ogden 重根极限、拉伸/压缩、近不可压缩情况、合成参数回收、未参与拟合的应变预测、输入转换、取消及 API 结果重读。
- 强椭圆性使用采样声学张量筛查：不通过的候选不会被作为合格候选默认推荐。通过有限个状态和方向**不能证明全局稳定**。这也不等价于 Abaqus 的内置筛查。
- 反力误差小不等于体积场足够准确。混合 J 与 `det(F)` 仅弱满足约束；非均匀问题必须同时检查二者偏差，以及 `mean(ln J)` 与 `ln(mean J)` 的不同含义。
- 当前 UI **拟合均匀单轴材料点**，没有用实际试样 FE 网格做反演。若夹持、几何不均匀或空间观测效应显著，需要匹配真实试样、边界条件和 DIC 观测区域后再识别参数。
- **没有 Abaqus 运行验证，也没有 UHYPER/UMAT 导出器。** 数学模型与开源 FEM 的一致性不能被表述为 Abaqus 等价性。
- 没有重拟合当前恢复目录中的真实实验：其应力面积定义、重复试验分组、误差估计尚需确认。该版本没有把真实数据、论文或旧仿真结果打包公开。

完整证据见本机生成的 `validation-results/fem-verification.json`。复核报告只包含合成/公式算例；不代表原试样验证已完成。

## Layout / 维护入口

```text
hyperfit/models.py          具名参数、能量导数、解析材料点响应
hyperfit/spectral.py        Ogden 谱函数导数，含重复特征值极限
hyperfit/objectives.py      数据检查、残差尺度、积分、评价指标
hyperfit/fitting.py         参数尺度化、多起点局部优化、候选诊断
hyperfit/fem.py             FElupe 适配与立方体算例
hyperfit/stability.py       有限状态/方向的强椭圆性筛查
hyperfit/data.py            文件读取、单位和物理量转换
hyperfit/api.py             后台任务、取消、运行记录、HTTP
hyperfit/frontend/         独立 HTML/CSS/JavaScript 前端
tests/                     科学与服务回归测试
docs/                      理论约定和贡献指南
```

运行输出在 `runs/<id>/`，默认只监听 `127.0.0.1`。单 worker 限制并发，任务失败不复用其他结果。服务重启后可按任务 ID 查询已完成结果；未完成任务标为 interrupted。UI 暂不提供历史任务列表，导出的 JSON 也尚无一键导入重放入口。

这是本地研究应用；公开源码不意味着当前服务具备多用户鉴权、资源配额、生产部署或公网数据安全能力。

## License and attribution

Copyright (C) 2026 HyperFit contributors. New code in this directory is available under the GNU General Public License, version 3 or (at your option) any later version. See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Provided without warranty.

该许可仅适用于本仓库的重建代码，不替旧文件、论文或原始实验数据作许可决定。仓库采用单进程本地运行；公开代码与部署在线公共服务是不同步骤。
