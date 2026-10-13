# Embodied VLAs: RT-2, OpenVLA, π0, GR00T · 具身 VLA：RT-2、OpenVLA、π0、GR00T

> 模型第一次读下网站上的菜谱并在厨房机器人上执行，是 RT-2（Google DeepMind，2023 年 7 月）。RT-2 把动作离散化成文本 token，在网络数据加机器人动作数据上共同微调一个 VLM，证明了网络规模的视觉-语言知识能迁移到机器人控制。OpenVLA（2024 年 6 月）交付了开源的 7B 参照。Physical Intelligence 的 π0 系列（2024-2025）加入了 flow-matching 动作专家。NVIDIA 的 GR00T N1（2025 年 3 月）为人形机器人交付了规模化的双系统（System 1 / System 2）控制。VLA 原语 —— 视觉-语言-动作，一个能看、能读、能行动的单一模型 —— 是本阶段的理解模型与 Phase 15 自主系统之间的桥梁。

> The first time a model read a recipe off a website and executed it in a kitchen robot was RT-2 (Google DeepMind, July 2023). RT-2 discretized actions as text tokens, co-fine-tuned a VLM on web data plus robot-action data, and proved that web-scale vision-language knowledge transfers to robotic control. OpenVLA (June 2024) shipped the open 7B reference. Physical Intelligence's π0 series (2024-2025) added flow-matching action experts. NVIDIA's GR00T N1 (March 2025) delivered dual-system (System 1 / System 2) control for humanoid robots at scale. The VLA primitive — vision-language-action, a single model that sees, reads, and acts — is the bridge between this phase's understanding models and the autonomous systems in Phase 15.

**Type:** Learn
**Languages:** Python (stdlib, action tokenizer + VLA inference skeleton)
**Prerequisites:** Phase 12 · 05 (LLaVA), Phase 15 (Autonomous Systems, referenced)
**Time:** ~180 minutes

## Learning Objectives · 学习目标

- 描述动作 token 化：离散分箱编码（RT-2）、FAST 高效动作 token、连续 flow-matching 动作（π0）。
- 解释为什么在网络数据 + 机器人数据上共同微调能保住向新任务迁移的通用知识。
- 在同一个机器人任务上对比 OpenVLA（开源 7B Llama+VLM）、π0（flow-matching）与 GR00T N1（双系统）。
- 说出 Open X-Embodiment 数据集及其作为 RT-X 训练语料的角色。

> Describe action tokenization: discrete bin encoding (RT-2), FAST efficient action tokens, continuous flow-matching actions (π0).
> Explain why co-fine-tuning on web + robot data preserves general-knowledge transfer to novel tasks.
> Compare OpenVLA (open 7B Llama+VLM), π0 (flow-matching), and GR00T N1 (dual-system) on the same robot task.
> Name the Open X-Embodiment dataset and its role as the RT-X training corpus.

## The Problem · 问题在哪

让机器人听自然语言指令做家务，自 1970 年代起就是研究目标。2020 年代的答案：视觉-语言-动作（VLA）模型。与 VQA 相同的 VLM 架构，但输出不是文本，而是动作（关节力矩、末端执行器位姿、离散指令）。

VLA 特有的挑战：

1. 动作空间连续（关节角度、力）且高维（7 自由度机械臂 + 3 自由度夹爪 = 30Hz 下的 10 维）。
2. 机器人专属训练数据稀缺。Open X-Embodiment 约 100 万条轨迹；网络图文是 50 亿+。
3. 控制频率要紧。30Hz 控制回路意味着每个动作只有 33ms 预算。
4. 安全。一个错误动作会损坏硬件、伤到人或损毁财物。

> A robot that does chores from natural language instructions has been a research target since the 1970s. The 2020s answer: a vision-language-action (VLA) model. Same VLM architecture used for VQA, but output is actions (joint torques, end-effector poses, discrete commands) instead of text. ... Challenges specific to VLAs: Action spaces are continuous (joint angles, forces) and high-dimensional (7-DOF arm + 3-DOF gripper = 10 dims at 30 Hz). Robot-specific training data is scarce. Open X-Embodiment has ~1M trajectories; web text-image is 5B+. Control frequency matters. 30 Hz control loop means 33ms budget per action. Safety. A wrong action damages hardware, humans, or property.

## The Concept · 概念

### Action tokenization (RT-2) · 动作 token 化（RT-2）

RT-2 的技巧：把每个关节目标表示成一个量化的文本 token。把归一化的 [-1, 1] 区间离散成 256 个箱，每个箱映射到一个词表 ID。10 自由度的动作在每个控制步变成 10 个 token。

在混合数据上共同微调一个 PaLM-X VLM：

- 网络图文对（描述、VQA）。
- 机器人演示，动作表示为 token。

模型看到「拿起红色方块」（语言）→ 图像（视觉）→ 10 个 token 的动作序列（离散化的关节目标）。网络预训练保住了通用知识迁移：即使「快速移动的」不在训练数据里，RT-2 也能执行「朝快速移动的物体移过去」。

RT-2 论文中的推理速度是 3-5 Hz，瓶颈在 VLM 自回归解码。

> RT-2's trick: represent each joint target as a quantized text token. Discretize the normalized [-1, 1] range into 256 bins, map each bin to a vocabulary ID. A 10-DOF action becomes 10 tokens at each control step. ... The model sees "pick up the red cube" (language) → image (vision) → 10-token action sequence (discretized joint targets). Web pretraining preserves general-knowledge transfer: RT-2 can follow "move towards the fast-moving object" even though "fast-moving" isn't in training data. ... Inference at 3-5 Hz in the RT-2 paper, limited by VLM autoregressive decode.

### OpenVLA — the open 7B reference · OpenVLA——开源 7B 参照

OpenVLA（Kim et al.，2024 年 6 月）是开源权重的 RT-2 等价物。7B Llama 骨干、DINOv2 + SigLIP 双视觉编码器、256 箱动作 token 化。

在 Open X-Embodiment（22 台机器人共 97 万条轨迹）上训练。自带 LoRA 微调支持，便于适配新机器人。

推理：A100 上量化后 4-5 Hz。慢速操作够用，高频控制不行。

> OpenVLA (Kim et al., June 2024) is the open-weights RT-2 equivalent. 7B Llama backbone, DINOv2 + SigLIP dual vision encoder, action tokenization over 256 bins. ... Trained on Open X-Embodiment (970k trajectories across 22 robots). Ships with LoRA fine-tuning support for adapting to new robots. ... Inference: 4-5 Hz on an A100 with quantization. Fast enough for slow manipulation, not for high-frequency control.

### FAST tokenizer — faster action decode · FAST tokenizer——更快的动作解码

Pertsch et al.（2024）指出离散分箱 token 化效率低下 —— 多数动作聚在箱空间的一小块区域。FAST（频域动作序列 tokenizer）用 DCT 压缩动作序列，再对系数做量化。

一条 30 步动作轨迹变成约 10 个 FAST token，而不是 300 个离散分箱 token。推理提速 3-5 倍且无质量损失。

> Pertsch et al. (2024) showed that discrete-bin tokenization is inefficient — most actions cluster in a small region of bin-space. FAST (Frequency-domain Action Sequence Tokenizer) compresses action sequences via DCT and quantizes the coefficients. ... A 30-step action trajectory becomes ~10 FAST tokens instead of 300 discrete-bin tokens. Inference speeds up 3-5x without quality loss.

### π0 and flow-matching actions · π0 与 flow-matching 动作

Physical Intelligence 的 π0（Black et al.，2024 年 10 月）用 flow-matching 动作专家替代离散动作 token：

- 一个小的动作 Transformer 读取 VLM 的隐状态，通过整流流输出连续的 50 步动作序列。
- 动作头用 flow-matching 损失训练；VLM 预训练保持不变。
- 推理：整个动作序列约 5 个去噪步产出，实际控制率 50 Hz。

π0 的主张：在一大批操作任务上胜过 OpenVLA 和 Octo。连续动作的表述保住了被离散化破坏的平滑性。

π0.5 和 π0-FAST 是增量升级。π0-FAST 把 FAST token 化与 flow matching 结合。

> Physical Intelligence's π0 (Black et al., October 2024) replaces discrete action tokens with a flow-matching action expert: A small action transformer reads the VLM's hidden states and outputs a continuous 50-step action sequence via rectified flow. The action head trains with flow-matching loss; VLM pretraining stays unchanged. Inference: full action sequence emitted in ~5 denoising steps, effectively 50 Hz control. ... π0's claim: beats OpenVLA and Octo on a wide suite of manipulation tasks. The continuous-action formulation preserves smoothness that discretization destroys. ... π0.5 and π0-FAST are incremental upgrades. π0-FAST combines FAST tokenization with flow matching.

### GR00T N1 — dual-system for humanoids · GR00T N1——人形机器人双系统

NVIDIA 的 GR00T N1（2025 年 3 月）为人形机器人打造（>30 自由度、全身）：

- System 2：一个大型 VLM 读取场景 + 指令，以约 1 Hz 产出高层子目标。
- System 1：一个小型动作头 Transformer，以子目标为条件产出 50-100 Hz 的低层关节指令。

这个分工对应卡尼曼的快与慢思考：System 2 规划，System 1 行动。好处：慢的 VLM 级规划不阻塞快速控制；System 1 保持小巧以满足延迟。

GR00T N1.7（2025 年末）改进了数据扩展。GR00T 用来自 Omniverse 的 sim-to-real 数据做微调。

> NVIDIA's GR00T N1 (March 2025) is built for humanoid robots (>30 DOF, full-body): System 2: a large VLM reading scene + instruction, producing high-level subgoals at ~1 Hz. System 1: a small action-head transformer producing low-level 50-100 Hz joint commands conditioned on the subgoals. ... The split maps to Kahneman's fast-and-slow thinking: System 2 plans, System 1 acts. Benefits: slow VLM-sized planning does not block fast control; System 1 stays small for latency. ... GR00T N1.7 (late 2025) improves data scaling. GR00T fine-tunes with sim-to-real data from Omniverse.

### Open X-Embodiment · Open X-Embodiment

训练数据本体。RT-X（2023 年 10 月）汇集了覆盖 22 台机器人、100 万条轨迹的 22 个数据集。Open X-Embodiment 是人人都在用的语料：

- ALOHA / Bridge V2 / Droid / RT-2 Kitchen / Language Table。
- 每个样本：(机器人状态、相机视角、指令、动作序列)。
- 训练卫生：统一动作空间，归一化关节范围，调整相机分辨率。

OpenVLA 和 π0 都在 Open X-Embodiment 上训练。与任何具体机器人的领域差距，靠 100-1000 条任务专属演示的 LoRA 微调来弥合。

> The training data. RT-X (October 2023) assembled 22 datasets covering 1M trajectories across 22 robots. Open X-Embodiment is the corpus everyone uses: ALOHA / Bridge V2 / Droid / RT-2 Kitchen / Language Table. Each sample: (robot state, camera views, instruction, action sequence). Training hygiene: unify action space, normalize joint ranges, resize cameras. ... OpenVLA and π0 train on Open X-Embodiment. Domain gap to any specific robot is closed by LoRA fine-tuning on 100-1000 task-specific demos.

### Co-fine-tuning vs robot-only · 联合微调 vs 仅机器人数据

联合微调把网络 VQA 数据与机器人轨迹混在一起。配比很关键：VQA 太多，模型忘掉动作；机器人数据太多，模型丢掉通用知识。

RT-2 的配比约 1:1。OpenVLA 约 0.5:1（网络:机器人）。π0 类似。精确配比是随数据集规模调整的超参数。

只用机器人数据的训练产出任务专属模型，遇到分布外指令就失败。联合微调正是「拿起红色方块（演示里有）」与「拿起左起第三大的物体（全新表述）」之间的差别。

> Co-fine-tuning mixes web VQA data with robot trajectories. The ratio matters: too much VQA and the model forgets actions; too much robot data and the model loses general knowledge. ... RT-2's ratio: ~1:1. OpenVLA: ~0.5:1 web-to-robot. π0: similar. The precise ratio is a hyperparameter to tune per dataset size. ... Robot-only training produces task-specific models that fail on out-of-distribution instructions. Co-fine-tuning is the difference between "pick up the red cube (in demo)" and "pick up the third largest object from the left (novel phrasing)."

### Safety and action limits · 安全与动作限制

每个生产级 VLA 都自带：

- 硬关节限制（扭矩不能超过规格）。
- 速度限制（软裁剪）。
- 工作空间边界（末端执行器不能离开桌面）。
- 新任务的真人在环审批。

这些都位于 VLA 之外，作为控制层检查。VLA 的输出是建议，不是命令。

> Every production VLA ships with: Hard joint limits (can't torque past spec). Velocity limits (soft clipping). Workspace bounds (end-effector cannot leave the table). Human-in-the-loop approval for novel tasks. ... These sit outside the VLA as control-layer checks. The VLA's output is a suggestion, not a command.

```figure
mm-action-tokens
```

## Use It · 实战用法

`code/main.py`：

- 实现 256 箱动作 token 化与反 token 化。
- 草拟一个基于 DCT + 量化的 FAST tokenizer。
- 对比（离散分箱、FAST、连续流）三种方案每动作步的 token 数。
- 打印 RT-2 → OpenVLA → π0 → GR00T 的谱系摘要。

> `code/main.py`: Implements 256-bin action tokenization and de-tokenization. Sketches a FAST tokenizer based on DCT + quantization. Compares token-count per action step across (discrete-bin, FAST, continuous-flow). Prints a lineage summary of RT-2 → OpenVLA → π0 → GR00T.

## Ship It · 交付

本课产出 `outputs/skill-vla-action-format-picker.md`。给定一个机器人任务（操作、导航、人形全身），它在离散分箱 + RT-2、FAST + OpenVLA、flow-matching + π0、双系统 + GR00T 之间做选择。

> This lesson produces `outputs/skill-vla-action-format-picker.md`. Given a robot task (manipulation, navigation, humanoid whole-body), picks between discrete-bin + RT-2, FAST + OpenVLA, flow-matching + π0, or dual-system + GR00T.

## Exercises · 练习

1. 10 自由度机械臂、30Hz 控制率。256 箱离散分箱 token 化每秒产出多少 token？7B VLM 跟得上吗？

2. FAST token 化把 30 步轨迹压到约 10 个 token。如果轨迹含高频动作（比如打鼓），用户会失去什么？

3. π0 的 flow-matching 头约 5 步去噪。对比 OpenVLA 4-5 Hz 自回归解码的吞吐。

4. GR00T 的 System 1 / System 2 分工对应卡尼曼。提出另一种可能有助双足行走的分工（System 3？）。

5. 阅读 Open X-Embodiment 论文第 4 节的数据集策划。说出防止领域泄漏的三条策划规则。

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|------------------------|
| VLA | 「视觉-语言-动作」 | 接收图像 + 指令、输出动作命令的模型 |
| 动作 token 化（Action tokenization） | 「离散分箱」 | 把连续关节目标按维量化成 256 箱，每箱一个词表 ID |
| FAST tokenizer | 「频域动作 token」 | DCT + 量化，把 30 步轨迹压到约 10 个 token |
| 联合微调（Co-fine-tune） | 「网络 + 机器人混着训」 | 在机器人演示之外同时训练网络 VQA 数据，保住通用知识 |
| Flow-matching 动作头 | 「π0 的连续输出」 | 通过整流流输出 50 步动作序列的小 Transformer |
| System 1 / System 2 | 「双系统控制」 | 大 VLM 慢规划、小动作头快执行；GR00T 模式 |
| Open X-Embodiment | 「RT-X 数据集」 | 100 万条轨迹的跨机器人数据集；训练语料 |

## Further Reading · 延伸阅读

- [Brohan et al. — RT-2 (arXiv:2307.15818)](https://arxiv.org/abs/2307.15818)
- [Kim et al. — OpenVLA (arXiv:2406.09246)](https://arxiv.org/abs/2406.09246)
- [Black et al. — π0 (arXiv:2410.24164)](https://arxiv.org/abs/2410.24164)
- [NVIDIA — GR00T N1 (arXiv:2503.14734)](https://arxiv.org/abs/2503.14734)
- [Open X-Embodiment Collab — RT-X (arXiv:2310.08864)](https://arxiv.org/abs/2310.08864)
