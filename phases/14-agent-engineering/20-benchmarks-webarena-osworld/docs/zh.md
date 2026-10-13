# Benchmarks: WebArena and OSWorld · 基准测试：WebArena 与 OSWorld

> WebArena 在四个自托管应用上测 web agent 能力。OSWorld 在 Ubuntu、Windows、macOS 上测桌面 agent 能力。发布时（2023–2024），两者都显示出一流 agent 与人类之间的巨大差距。差距正在缩小；失效模式却没变过。
>
> WebArena tests web-agent capability across four self-hosted apps. OSWorld tests desktop-agent capability across Ubuntu, Windows, macOS. At release (2023–2024) both showed a big gap between best-in-class agents and humans. The gap is narrowing; the failure modes haven't changed.

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 19 (SWE-bench, GAIA)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 描述 WebArena 的四个自托管应用，以及为什么基于执行的评估很重要。
- 解释 OSWorld 为什么用真实操作系统截图而不是无障碍 API。
- 说出 OSWorld 的两大失效模式：GUI grounding 和操作知识（operational knowledge）。
- 总结 OSWorld-G 和 OSWorld-Human 在基础基准之上补充了什么。

> Describe WebArena's four self-hosted apps and why execution-based evaluation matters.
> Explain why OSWorld uses real OS screenshots instead of accessibility APIs.
> Name the two primary OSWorld failure modes: GUI grounding and operational knowledge.
> Summarize what OSWorld-G and OSWorld-Human add on top of the base benchmark.

## The Problem · 问题在哪

通用 agent 会调用工具。但它们能驱动浏览器点满 20 下完成一次购物结账吗？能只用键盘和鼠标配置好一台 Linux 机器吗？这些就是 WebArena 和 OSWorld 要回答的问题。

> Generalist agents can call tools. Can they drive a browser across 20 clicks to complete a shopping checkout? Can they configure a Linux box using only keyboard and mouse? These are the questions WebArena and OSWorld answer.

## The Concept · 概念

### WebArena (Zhou et al., ICLR 2024) · WebArena

- 812 个长程任务，分布在四个自托管 web 应用上：购物站、论坛、类 GitLab 的开发工具、企业 CMS。
- 外加工具类应用：地图、计算器、草稿板。
- 评估基于执行、通过 gym API 进行——订单下了没有？issue 关了没有？CMS 页面更新了没有？
- 发布时：最好的 GPT-4 agent 成功率 14.41%，人类为 78.24%。

> - 812 long-horizon tasks across four self-hosted web apps: a shopping site, a forum, a GitLab-like dev tool, a business CMS.
> - Plus utilities: map, calculator, scratchpad.
> - Evaluation is execution-based via gym APIs — was the order placed, was the issue closed, was the CMS page updated?
> - At release: best GPT-4 agent hit 14.41% success vs human 78.24%.

自托管这个设定很关键——目标应用版本被钉死、可复现，基准本身不会因为外部网站变化而抖动。

> The self-hosted framing matters — the benchmark is not flaky because the target apps are pinned and reproducible.

### Extensions · 扩展

- **VisualWebArena** —— 视觉接地的任务，成功与否取决于对图像的解读（截图作为一等公民观测）。
- **TheAgentCompany**（2024 年 12 月）—— 加入终端 + 编码；更像真实的远程办公环境。

> - **VisualWebArena** — visually grounded tasks where success depends on interpreting images (screenshots as first-class observations).
> - **TheAgentCompany** (Dec 2024) — adds terminal + coding; more like a real remote-work environment.

### OSWorld (Xie et al., NeurIPS 2024) · OSWorld

- 369 个真实计算机任务，横跨 Ubuntu、Windows、macOS。
- 对真实应用做自由形式的键盘和鼠标控制。
- 观测是 1920×1080 截图。
- 发布时：最好的模型 12.24%，人类 72.36%。

> - 369 real computer tasks across Ubuntu, Windows, macOS.
> - Free-form keyboard and mouse control of real applications.
> - 1920×1080 screenshots as the observation.
> - At release: best model 12.24% vs human 72.36%.

### Primary failure modes · 两大失效模式

1. **GUI grounding（界面定位）。** 像素 → 元素的映射。模型很难在 1920×1080 的画面里可靠地定位 UI 元素。
2. **操作知识（operational knowledge）。** 哪个菜单里有那个设置、哪个快捷键、哪个偏好面板。这是人类花好几年积累起来的知识长尾。

> 1. **GUI grounding.** Pixel → element mapping. Models struggle to localize UI elements reliably in 1920×1080.
> 2. **Operational knowledge.** Which menu has the setting, which keyboard shortcut, which preference pane. Knowledge tail that humans build over years.

### Follow-ups · 后续工作

- **OSWorld-G** —— 564 个样本的 grounding 专项套件 + Jedi 训练集。把 grounding 从规划里拆出来，让你能分开测量两者。
- **OSWorld-Human** —— 人工精选的黄金动作轨迹。显示顶级 agent 用的步数是必要步数的 1.4–2.7 倍（轨迹效率差距）。

> - **OSWorld-G** — 564-sample grounding suite + Jedi training set. Decomposes grounding from planning so you can measure them separately.
> - **OSWorld-Human** — manually curated gold action trajectories. Shows top agents use 1.4-2.7x more steps than necessary (the trajectory-efficiency gap).

### Why this matters · 为什么这很重要

Claude computer use、OpenAI CUA、Gemini 2.5 Computer Use（第 21 课）都是在由 WebArena 和 OSWorld 塑造的工作负载上训练出来的。基准是靶子；生产模型是打靶的答案。

> Claude computer use, OpenAI CUA, Gemini 2.5 Computer Use (Lesson 21) all train on workloads shaped by WebArena and OSWorld. The benchmarks are the target; the production models are the shipped answer.

### Where benchmarking goes wrong · 基准测试的常见坑

- **只看截图的评估。** OSWorld 由截图驱动；拿一个用 DOM 或无障碍 API 的 agent 去 OSWorld 上跑分，测不到 grounding 这个挑战。
- **无视轨迹长度。** 只记成功率，就看不到 OSWorld-Human 揭示的 1.4–2.7 倍步数低效。
- **自托管应用过时。** WebArena 的应用钉死了特定版本；不经重新精选就升级，会破坏可比性。

> - **Screenshot-only evals.** OSWorld is screenshot-driven; evaluating an agent that uses DOM or accessibility APIs on OSWorld misses the grounding challenge.
> - **Ignoring trajectory length.** Scoring only success-rate misses the 1.4-2.7x step inefficiency OSWorld-Human surfaces.
> - **Stale self-hosted apps.** WebArena's apps pin specific versions; update without re-curation breaks comparability.

```figure
ae-agent-human-gap
```

## Build It · 动手造

`code/main.py` 实现了一个玩具 web-agent harness：

- 一个最小的「购物应用」状态机：list_items、add_to_cart、checkout。
- 3 个任务的黄金轨迹。
- 一个脚本化 agent，逐个尝试任务。
- 基于执行的评估器（状态检查）和轨迹效率指标（步数对比黄金轨迹）。

运行：

```
python3 code/main.py
```

> `code/main.py` implements a toy web-agent harness:
> - A minimal "shopping app" state machine: list_items, add_to_cart, checkout.
> - Gold trajectories for 3 tasks.
> - A scripted agent that attempts each task.
> - Execution-based evaluator (state check) and trajectory-efficiency metric (steps vs gold).

输出：每个任务的成功率与轨迹效率，呼应 OSWorld-Human 的方法论。

> Output: per-task success rate and trajectory efficiency, mirroring OSWorld-Human's methodology.

## Use It · 实战用法

- **WebArena Verified** 自托管在内部集群上做持续评估。
- **OSWorld** 在 VM 机群里跑桌面 agent。
- **计算机操作 agent**（第 21 课）—— Claude、OpenAI CUA、Gemini——都是在类似的工作负载上训练的。
- **你自己的产品流程** —— 给你最常用的 20 个任务采集黄金轨迹；每周让 agent 跑一遍。

> - **WebArena Verified** self-hosted on an internal cluster for continuous evaluation.
> - **OSWorld** in a VM fleet for desktop agents.
> - **Computer-use agents** (Lesson 21) — Claude, OpenAI CUA, Gemini — all trained on workloads like these.
> - **Your own product flows** — capture gold trajectories for your top 20 tasks; run agents against them weekly.

## Ship It · 交付

`outputs/skill-web-desktop-harness.md` 搭建一个 web/桌面 agent harness，带基于执行的评估和轨迹效率指标。

> `outputs/skill-web-desktop-harness.md` builds a web/desktop agent harness with execution-based eval and trajectory efficiency metric.

## Exercises · 练习

1. 给玩具 harness 加第二个应用（一个论坛）。写 3 个任务外加黄金轨迹。
2. 按任务汇报轨迹效率。在你的玩具上，agent 是黄金轨迹的 1 倍、2 倍还是 3 倍？
3. 实现一个「干扰」工具——黄金轨迹从来不用的那种。脚本化 agent 会上钩吗？
4. 读 OSWorld-G。在你自己的评估里，你会怎么把 grounding 失败和规划失败分开？
5. 读 WebArena 各应用的 README。升级其中一个钉死版本的应用时，什么东西会坏？

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|----------------|------------------------|
| WebArena | 「web agent 基准」 | 4 个自托管应用上的 812 个任务；gym 式评估 |
| VisualWebArena | 「视觉版 WebArena」 | 视觉接地的 WebArena；截图即观测 |
| OSWorld | 「桌面 agent 基准」 | 真实 Ubuntu/Windows/macOS 上的 369 个任务 |
| GUI grounding | 「像素到元素的映射」 | 模型在 1920x1080 画面里定位 UI 元素 |
| Operational knowledge | 「操作系统使用常识」 | 哪个菜单、哪个快捷键、哪个偏好面板 |
| OSWorld-G | 「grounding 套件」 | 564 个纯 grounding 样本 + 训练集 |
| OSWorld-Human | 「黄金轨迹」 | 人工专家动作序列，用来度量效率 |
| Trajectory efficiency | 「步数相对黄金的倍数」 | agent 步数除以人类最小步数 |

## Further Reading · 延伸阅读

- [Zhou et al., WebArena (arXiv:2307.13854)](https://arxiv.org/abs/2307.13854) —— 四应用 web 基准
- [Xie et al., OSWorld (arXiv:2404.07972)](https://arxiv.org/abs/2404.07972) —— 跨操作系统桌面基准
- [Anthropic, Introducing computer use](https://www.anthropic.com/news/3-5-models-and-computer-use) —— Claude 按基准塑形的能力
- [OpenAI, Computer-Using Agent](https://openai.com/index/computer-using-agent/) —— OSWorld 与 WebArena 的数字
