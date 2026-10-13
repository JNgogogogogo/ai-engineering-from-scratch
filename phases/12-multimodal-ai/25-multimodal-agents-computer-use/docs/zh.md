# Multimodal Agents and Computer-Use (Capstone) · 多模态智能体与计算机使用（毕业项目）

2026 年的前沿产品是一个多模态智能体（multimodal agent）：读屏幕截图、点按钮、操作网页 UI、填表单、端到端完成工作流。SeeClick 和 CogAgent（2024）证明了 GUI 定位（GUI grounding）这一原语。Ferret-UI 补上了移动端。ChartAgent 引入了面向图表的视觉工具使用（visual tool use）。VisualWebArena 和 AgentVista（2026）是前沿追逐的基准——连 Gemini 3 Pro 和 Claude Opus 4.7 在 AgentVista 的困难任务上也只有约 30%。这个毕业项目把 Phase 12 的每条线索拧在一起：感知（高分辨率 VLM）、推理（带工具使用的 LLM）、定位（坐标输出）、长程记忆与评测。

> The 2026 frontier product is a multimodal agent that reads screenshots, clicks buttons, navigates web UIs, fills forms, and completes workflows end-to-end. SeeClick and CogAgent (2024) proved the GUI-grounding primitive. Ferret-UI added mobile. ChartAgent introduced visual tool-use for charts. VisualWebArena and AgentVista (2026) are the benchmarks the frontier chases — and even Gemini 3 Pro and Claude Opus 4.7 score ~30% on AgentVista's hard tasks. This capstone pulls together every thread of Phase 12: perception (high-res VLM), reasoning (LLM with tool use), grounding (coordinate output), long-horizon memory, and evaluation.

**Type:** Capstone
**Languages:** Python（标准库，动作 schema + 智能体循环骨架）
**Prerequisites:** Phase 12 · 05（LLaVA）、Phase 12 · 09（Qwen-VL JSON）、Phase 14（Agent Engineering · 智能体工程）
**Time:** ~240 分钟

---

## Learning Objectives · 学习目标

- 设计一个多模态智能体循环：感知 → 推理 → 行动 → 观察 → 重复。
- 构建 GUI 定位输出 schema（点击坐标、输入文本、滚动、拖拽），让 VLM 能以 JSON 输出。
- 比较纯截图智能体、无障碍树（accessibility-tree）智能体与混合智能体。
- 在一个小型 VisualWebArena 切片上搭建多模态智能体基准评测。

> Design a multimodal agent loop: perceive → reason → act → observe → repeat.
> Build a GUI grounding output schema (click coordinates, type text, scroll, drag) the VLM can emit as JSON.
> Compare screenshot-only agents vs accessibility-tree agents vs hybrid agents.
> Set up a multimodal agent benchmark evaluation on a small VisualWebArena slice.

---

## The Problem · 问题在哪

一个订票网站的工作流：「帮我订一张 4 月 15 日去东京的机票，靠走道座位，800 美元以内，直接订掉。」（"find me a flight to Tokyo for April 15, aisle seat under $800, book it."）

一个多模态智能体需要：

1. 给浏览器截一张图。
2. 把截图 + URL + 目标解析成一个计划。
3. 产出一个结构化动作：click（在 x,y）、type "Tokyo"（在元素 E）、scroll down、select（单选按钮）。
4. 把动作施加到浏览器上。
5. 观察新状态（下一张截图）。
6. 重复，直到任务完成。

每一步都是一次多模态 VLM 调用。VLM 输出必须是可解析的 JSON。误差会跨步累积，所以恢复（recovery）很关键。

> Each step is a multimodal VLM call. The VLM output must be parseable JSON. Errors compound across steps, so recovery matters.

---

## The Concept · 概念

### GUI grounding — the primitive · GUI 定位——核心原语

GUI 定位（GUI grounding）是：给定截图和一句自然语言指令，输出要点击的 (x, y) 坐标（或其他动作）。

SeeClick（arXiv:2401.10935）是第一个大规模开源结果：在合成 + 真实 GUI 数据上微调 VLM，用纯文本 token 输出坐标。有效。

CogAgent（arXiv:2312.08914）为密集 UI 加了 1120x1120 高分辨率编码。成绩：网页导航约 84%。

Ferret-UI（arXiv:2404.05719）聚焦移动 UI，接入 iOS 无障碍（accessibility）数据。

输出格式通常是 JSON：

```json
{"action": "click", "x": 384, "y": 220, "element_desc": "Search button"}
```

`element_desc` 是为了便于恢复：如果坐标在两张截图之间漂移了，这条语义提示能让系统重新定位。

> GUI grounding is: given a screenshot and a natural language instruction, output the (x, y) coordinate to click (or other action).
> SeeClick (arXiv:2401.10935) was the first open result at scale: fine-tune a VLM on synthetic + real GUI data, output coordinates as plain text tokens. Works.
> The `element_desc` helps recovery: if coordinates drift between screenshots, the semantic hint lets the system re-ground.

---

### Action schemas · 动作 schema

一个典型的动作 schema 有 6-10 种动作类型：

- `click`: (x, y)
- `type`: (text, x?, y?)
- `scroll`: (direction, amount)
- `drag`: (x0, y0, x1, y1)
- `select`: (option_index)
- `hover`: (x, y)
- `navigate`: (url)
- `wait`: (ms)
- `done`: (success, explanation)

智能体每步产出一个动作。浏览器包装器执行它并返回新状态。

> A typical action schema has 6-10 action types:
> The agent emits one action per step. The browser wrapper executes and returns the new state.

---

### Screenshot-only vs accessibility-tree · 纯截图 vs 无障碍树

两种输入模式：

- 纯截图（screenshot-only）：完整图像，没有结构信息。最通用；任何应用都能用。
- 无障碍树（accessibility tree）：结构化的 DOM / iOS 无障碍信息。定位可靠得多；树可用的地方才有效。
- 混合（hybrid）：两者都用，树作为原子动作的可靠定位器，截图提供语义上下文。

生产级智能体在可能时都用混合模式。浏览器自动化（Selenium + 无障碍）总有树；桌面应用则不一定。

> Production agents use hybrid when possible. Browser automation (Selenium + accessibility) always has the tree; desktop apps sometimes do.

---

### Long-horizon memory · 长程记忆

一个 20 步工作流会产生 20 张截图。VLM 的上下文很快就满。三种压缩策略：

- 摘要链（summary-chain）：每 5 步总结一次发生了什么，丢掉旧截图。
- 跳帧（skip-frame）：保留第一张、最后一张，以及每 3 张取一张。
- 工具记录日志（tool-recorded log）：执行动作，保留一份文字日志记录做过什么；不回头重看旧截图。

Claude 的 computer-use API 用的就是日志模式。更简单、更可靠。

> A 20-step workflow generates 20 screenshots. The VLM's context fills up fast. Three compression strategies:
> Claude's computer-use API uses the log pattern. Simpler, more reliable.

---

### Visual tool use · 视觉工具使用

ChartAgent（arXiv:2510.04514）为图表理解引入了视觉工具使用：裁剪、缩放、OCR、调用外部检测。智能体可以输出「裁剪到区域 (100, 200, 300, 400) 然后调用 OCR」这样的工具调用。工具返回文本；VLM 继续推理。

这个模式可以泛化：set-of-mark 提示、区域标注、外部检测工具，全都符合「输出一个工具调用、收到一个结构化响应」的 schema。

> ChartAgent (arXiv:2510.04514) introduces visual tool use for chart understanding: crop, zoom, OCR, call external detection.
> This pattern generalizes: set-of-mark prompting, region annotation, and external detection tools all fit the same "output a tool call, receive a structured response" schema.

---

### The 2026 benchmarks · 2026 年的基准

- ScreenSpot-Pro。约 1k 张网页截图上的 GUI 定位。开源 SOTA 是 Qwen2.5-VL-72B，约 85%。前沿约 90%。
- VisualWebArena。端到端网页任务（购物、论坛、分类信息）。开源 SOTA 约 20%。Gemini 3 Pro 约 27%。
- AgentVista（arXiv:2602.23166）。2026 年最难的基准。横跨 12 个领域的真实工作流。前沿模型 27-40%；开源模型 10-20%。
- WebArena / WebShop。更老的基准；已被前沿模型打穿。

> ScreenSpot-Pro. GUI grounding on ~1k web screenshots. Open SOTA Qwen2.5-VL-72B ~85%. Frontier ~90%.
> AgentVista (arXiv:2602.23166). The hardest 2026 benchmark. Realistic workflows across 12 domains. Frontier models score 27-40%; open models 10-20%.

---

### Why it's still hard · 为什么还是难

智能体性能的瓶颈：

1. 细粒度视觉定位。「点那个小 X」在移动分辨率下经常失败。
2. 长程规划。10 个动作之后，智能体会偏离目标。
3. 错误恢复。点击失败（点错按钮）时，「检测到失败 + 恢复」在训练数据里很少见。
4. 跨页面上下文。在标签页或长表单之间跳转会丢状态。

研究方向：记忆架构、显式重规划、多模态验证（用截图比对确认动作成功）。

> 1. Visual grounding at fine scale. "Click the small X" fails often at mobile resolution.
> 2. Long-horizon planning. After 10 actions, the agent drifts from the goal.
> Research directions: memory architectures, explicit replanning, multimodal verification (screenshot match for action success).

---

### The capstone build-it · 毕业项目要造的东西

毕业项目任务：造一个 computer-use 智能体，它能：

1. 读取订票网站模拟页面的 HTML + 截图。
2. 规划一个多步序列：搜索 → 选择 → 填表单 → 提交。
3. 产出符合动作 schema 的 JSON 动作。
4. 在固定的 10 任务切片上评测。

本课提供脚手架代码，很容易扩展到真实浏览器。

> The capstone task: build a computer-use agent that:
> The lesson provides scaffold code that is easy to extend into a real browser.

```figure
mm-agent-loop
```

---

## Use It · 实战用法

`code/main.py` 是毕业项目的脚手架：

- 动作 schema 的 JSON 定义（10 个动作）。
- 用 dict 模拟的浏览器状态。
- 智能体循环骨架：接收状态、产出动作、施加、循环。
- 10 任务迷你基准（合成页面），测量端到端成功率。
- 动作失败时的错误恢复钩子。

---

## Ship It · 交付

本课产出 `outputs/skill-multimodal-agent-designer.md`。给定一个 computer-use 产品（领域、动作集、评测目标），设计完整的智能体循环、记忆策略、定位模式与预期基准分数。

> This lesson produces `outputs/skill-multimodal-agent-designer.md`. Given a computer-use product (domain, action set, evaluation target), designs the full agent loop, memory strategy, grounding mode, and expected benchmark score.

---

## Exercises · 练习

1. 给动作 schema 扩展一个 `screenshot_region` 工具（裁剪 + 缩放）。哪些任务会受益？

2. 读 AgentVista（arXiv:2602.23166）。描述最难的任务类别，以及前沿模型为什么仍然失败。

3. 长程记忆压缩：设计一个摘要链，实时保留的截图不超过 4 张，日志数量不限。

4. 构建一个错误恢复钩子：动作失败（按钮没找到）时，智能体下一步做什么？

5. 在 10 个网页任务上比较「纯截图的 Claude 4.7」与「截图 + 无障碍树混合的 Qwen2.5-VL」。谁在哪类任务上赢？

---

## Key Terms · 术语表

| 术语 | 通俗说法 | 实际含义 |
|------|-----------------|------------------------|
| GUI grounding | 「点击坐标」 | 模型为截图上指令的目标输出 (x,y) 坐标 |
| Action schema | 「工具定义」 | 合法动作（click、type、scroll、drag）的 JSON 描述 |
| Accessibility tree | 「结构化 DOM」 | 来自浏览器/iOS API 的机器可读 UI 层级 |
| Hybrid agent | 「截图 + 树」 | 同时使用图像与结构化信息；比任一单独使用更可靠 |
| Visual tool use | 「缩放/裁剪/检测」 | 智能体在规划中途调用外部视觉工具（OCR、检测） |
| Summary-chain | 「记忆压缩」 | 用周期性的文字摘要替代冗长的截图历史 |
| VisualWebArena | 「端到端网页基准」 | 2024 年的端到端网页任务基准 |
| AgentVista | 「2026 高难基准」 | 12 领域真实工作流；连 Gemini 3 Pro 也只有约 30% |

---

## Further Reading · 延伸阅读

- [Cheng et al. — SeeClick (arXiv:2401.10935)](https://arxiv.org/abs/2401.10935)
- [Hong et al. — CogAgent (arXiv:2312.08914)](https://arxiv.org/abs/2312.08914)
- [You et al. — Ferret-UI (arXiv:2404.05719)](https://arxiv.org/abs/2404.05719)
- [ChartAgent (arXiv:2510.04514)](https://arxiv.org/abs/2510.04514)
- [Koh et al. — VisualWebArena (arXiv:2401.13649)](https://arxiv.org/abs/2401.13649)
- [AgentVista (arXiv:2602.23166)](https://arxiv.org/abs/2602.23166)
