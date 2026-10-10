# 我的 AI 工程学习之路
<!-- Managed by the ai-engineering-from-scratch learning skills.
     Repo: https://github.com/rohitg00/ai-engineering-from-scratch -->

> 自 2026-10-09 起本文件一律用中文记录。路径表中的状态关键字（Do / Skip / Review / Done）保留英文，供学习技能校验使用。

## 固定约定（记忆）

1. **每次学习新一课之前，先把该课 `docs/en.md` 改成中文**：在同目录写 `docs/zh.md`，中文正文在前，英文原文以引用块（`>`）保留在对应段落下方；代码块、命令、`figure` 块、术语名一律保留英文不翻译；`en.md` 本体保持英文不动。（2026-10-09 起，学员指定）

   > **⚠️ 执行顺序（2026-10-09 学员指出后补充）**
   >
   > 「先写 zh.md」是**开课前的第一步**，不是收尾时的一项待办。
   >
   > 正确顺序：
   > 1. 读 `docs/en.md` + `quiz.json`
   > 2. **立刻写 `docs/zh.md`**（中文讲义，含实测数据与纠正）
   > 3. 才开始热身题 → 讲义正文 → 测验
   > 4. 测验后写进度日志 + 复习队列
   >
   > **违反记录**：0/08 漏写了——读完美mit直接出题，把 zh.md 拖到收尾时又被别的事
   > 打断，最终没写。根因是把它当成待办清单的一项，而不是流程的第一步。
   > 「约定挂在待办清单里迟早会漏，必须挂在流程第一步上。」
   >
   > 相关：`.workbuddy/memory/MEMORY.md` 存了同一条规则的长期记忆版，含完整格式表与本机环境事实。

   > 具体格式要求：
   >
   > | 项 | 要求 |
   > |---|---|
   > | 中文正文 | 在前，作为主体 |
   > | 英文原文 | 引用块 `>`，放在对应中文段落**下方** |
   > | 代码块 / 命令 | 不译，原样保留 |
   > | `figure` 块 | 不译，原样保留 |
   > | 术语名 | 保留英文（kernel / cell / layer / token），首次出现可加中文注释 |
   > | `en.md` 本体 | 保持英文不动 |
   >
   > 交付形态以中英双语对照为最优（0/06 实测：双语版质量高于纯中文版）。
   >
   > **讲义里要写实测数据**，不是只翻译原文。实测发现课程原文不准确时，
   > 直接在讲义里加「实测纠正」一节说明（见 0/08 的类型检查那节）。

## 使命
转行进入 AI 工程，以最快速度冲刺，目标是在课程结束时亲手构建一个自主智能体。

## 定位
- 日期：2026-10-09
- 得分：5/10 — 数学与统计：2/2，经典机器学习：1/2，深度学习：0/2，NLP 与 Transformer：0/2，应用 AI：2/2
- 起点：Phase 0：深度学习核心
- 节奏：冲刺（"越快越好"）

## 状态关键字说明
路径表里的英文关键字供学习技能校验用，中文含义如下：

| 关键字 | 中文含义 | 标记 |
|--------|----------|------|
| `Do` | 执行 | ● |
| `Skip` | 跳过 | ○ |
| `Review` | 复习（走`check-understanding`） | ◐ |
| `Done` | 完成 | ✓ |

## 学习路径
| Phase | 名称 | 状态 | 预计学时 |
|-------|------|------|---------|
| 0 | 环境配置与工具 | Do | 12 |
| 1 | 数学基础 | Do | 12 |
| 2 | 机器学习基础 | Do | 21 |
| 3 | 深度学习核心 | Do | 15 |
| 4 | 计算机视觉 | Do | 27 |
| 5 | NLP — 从基础到进阶 | Do | 30 |
| 6 | 语音与音频 | Do | 18 |
| 7 | Transformer 深度剖析 | Do | 14 |
| 8 | 生成式 AI | Do | 14 |
| 9 | 强化学习 | Do | 13 |
| 10 | 从零构建大语言模型 | Do | 26 |
| 11 | 大语言模型工程 | Do | 19 |
| 12 | 多模态 AI | Do | 65 |
| 13 | 工具与协议 | Do | 43 |
| 14 | 智能体工程 | Do | 55 |
| 15 | 自主系统 | Do | 20 |
| 16 | 多智能体与群体智能 | Do | 28 |
| 17 | 基础设施与生产部署 | Do | 32 |
| 18 | 伦理、安全与对齐 | Do | 31 |
| 19 | 毕业项目 | Do | 620 |

> 合计约 1103 小时（不含 Phase 1 跳过的 17 课）。Phase 19 的 620 小时是毕业项目本身的工作量，
> 不属于「学完课程」的必读内容。

## 学习进度日志
| 日期 | 课程 | 测验 | 备注 |
|------|------|------|------|
| 2026-10-09 | 1/01 | 3/3 | 岔路：学员明确要求学完 Phase 1 全部 17 课。中英文混合教学。曾把秩（rank，400）与冗余计数（100）弄混一次，随后自行纠正。点积直觉很强。 |
| 2026-10-09 | 1/02 | 2/2 | 热身 2/2。形状规则需要一步步重新讲解才弄懂；之后正确答出 3 层权重形状题（8x5、4x8、2x4）。"Use It"回答较浅（简化过程）——值得回顾"从零构建"对理解黑盒框架的意义。 |
| 2026-10-09 | 1/02 | 4/4 | 应学员要求重做：此前两道热身题全错（形状规则方向弄反、广播的作用）。通过"左列=右行"口诀和批量广播演示修复；有效/无效矩阵乘法对练习全对。可以进入第 3 课。 |
| 2026-10-09 | 1/03 | 2/3 | 第 3 课（矩阵变换与特征值）。热身先 0/2，重做第 2 课后通过。手算 [[4,2],[1,3]] 的特征值正确（5、2）。特征分解解释题未答出（需要讲解 V/D 各自的角色）。"旋转-反射-两次"题空着，已用几何方式补讲。 |
| 2026-10-09 | 1/04 | 2/3 | 第 4 课（机器学习微积分）。梯度下降直觉很强：发现了我只打印偶数步里隐藏的一步（第 1 步 x=3.2），准确预测 lr=1.0 会震荡，手算出 (1,2) 处梯度 (8,7)。Hessian/牛顿法题未答出——是之前跳过的内容；随即补讲（曲率、N×N 的开销、为什么需要 Adam）。已加入复习队列。 |
| 2026-10-09 | 0/01 | 2/3 | 岔路：Phase 0 标记为 Skip，但学员在课程指南后明确要求学这一课。热身（1/04）2/2——Hessian/牛顿法回忆正确。现场运行 verify.py 讲解四层技术栈（系统 python 与 .venv 的 numpy 导入差异效果很好）。GPU 检查测验答错：选了 torch.__version__（版本号 ≠ 可用性）；"Use It"回答较浅（"自动化环境安装"），经提示才展开——关键收获：工具自动化的是执行，不是判断。 |
| 2026-10-09 | 0/02 | 3/3 | 学员连发三条冲突的"learn"消息；按最新的（0/02）执行。热身 2/2——正确回忆出 0/01 的 GPU 错题，复习项已销。挖出"git 只存差异"的经典误解；用内容寻址快照 + blob 去重，现场演示 scratch 仓库的分支/合并（fast-forward = 移动指针）予以纠正。"分支即指针"的题答对。测验 3/3 全对。 |
| 2026-10-09 | 0/03 | 2/3 | 学员修改主线：Phase 0 由 Skip 改为 Do，按顺序推进。把 gpu_check.py 适配到 MPS（踩坑：macOS 的 os.sysconf 不认 "hw.memsize"，改用 sysctl 子进程修复）。用 uv 重建 .venv（学员在 0/01 后自己装了 uv）。基准测试的求实时刻：我对 4x 加速的"矩阵太小"假设被数据推翻（4000² 到 12000² 加速比稳定 4x），改讲 Apple AMX CPU ≈1.6 TFLOPS vs MPS fp32 ≈6 TFLOPS。nvidia-smi 题失分（选了不存在的 torch API）；fp16 法则测验中途补讲后答对 C。 |
| 2026-10-09 | 0/04 | 1/3 | 首次 LLM API 调用成功：配好 .env（已被 .gitignore 覆盖）+ uv run --env-file 工作流，用 openai SDK 调 DeepSeek（OpenAI 兼容，base_url + model 两个字符串即可换厂商）。git 历史不可变题答对（密钥泄露后删文件不够，需改写历史+换钥匙）。测验 1/3：.env 存放答对；Anthropic 裸 HTTP 的 x-api-key 头答成 Bearer（正好与其 DeepSeek 调用用的 Bearer 对照，已讲厂商差异）；429 限流答成"自动排队"，补讲指数退避与 Retry-After。答题速度偏快，疑为未细读题干。 |
| 2026-10-09 | 0/05 | 3/3 | Jupyter Notebooks，无新数学，纯工程手感。热身 2/2——Anthropic 的 x-api-key 这次答对，0/04 复习项销账。理解检查（跨 cell 变量存活）一次答对 12。用真实 kernel（jupyter_client 驱动，非模拟）复现三个陷阱：乱序执行、幽灵状态、内存泄漏；最触动的是幽灵状态——CELL4 一行未改，只因前面多跑了一个 cell 就从 NameError 变成 499,999。实测 %timeit 的必要性：同一段 np.random.randn(1000) 单次计时 8轮 =4.61/0.01/0.01…ms，差582 倍，首次懒加载主导。测验 3/3 全对且Q2（乱序执行）答得很快，说明 kernel 概念已内化。产物：learning-artifacts/phase0/notebook_traps_demo.py。 |
| 2026-10-09 | 0/06 | 3/3 | Python Environments。热身 2/2（0/05 的%timeit 与乱序执行都答对，且主动补出"setup 提到循环外"这个细节）。核心讲透三件事：① 虚拟环境不是 Python 特性而是**目录约定**，隔离的实现就是 pyvenv.cfg 里那行 `include-system-site-packages = false`；② activate 只做两件事——PATH 前面插入 + 导出 VIRTUAL_ENV，deactivate 就是把 PATH 字符串还原，没有"卸载"；③ 隔离判定看 sys.prefix != sys.base_prefix。实测建了两个真环境各装不同 numpy（1.26.4 vs 2.2.6）互不干扰，系统 Python保持干净。发现本课程 .venv 是 uv 建的**没有 pip**，`python -m pip` 报 `No module named pip`（极具误导性的报错）。体积对比 69MB vs 297 字节 ≈ 24万倍。测验 3/3 全对。产物：learning-artifacts/phase0/venv_isolation_lab.py。 |
| 2026-10-09 | 0/07 | 3/3 | Docker for AI。热身 2/2（0/06 的 uv 无pip 与 which python 都答对）。核心讲透：镜像分层与缓存失效范围（每条指令一层，改一层则其后全废）；四个反直觉但正确的写法（apt-get update 必须与 install 合并、pip 要 --no-cache-dir、--platform=linux/amd64 是给 Apple Silicon 的、get-pip.py 要带 sha256 校验）。实测数据：原版 13 层合计约 4360 MB（torch 层 2610 MB 最贵），改第 9 层只需重跑 250 MB，改第 7 层要 2860 MB——这就是"torch 装倒数第二层"的量化理由。给了 M5 Pro 的现实结论：Docker daemon 未运行、8.32 GB 上限跑不动 7GB CUDA 镜像、PyTorch cu124 wheel 只发 x86_64，Apple Silicon 上建议直接用 MPS 原生跑。测验 3/3 全对。产物：dockerfile_layer_analyzer.py + Dockerfile.macos-lite。 |
| 2026-10-09 | 0/08 | 3/3 | Editor Setup。热身 2/2（0/07 的 apt-get update合并 与 Apple Silicon 平台约束都答对，且 Q2 正确选了"容器里依然没有 GPU"而非"改 CPU 版"这个陷阱项）。**本课修正了课程原文一处不准确**：课程说 typeCheckingMode: basic 能抓 tensor shape mismatch，实测抓不到——`x.reshape(x.size(1), x.size(0))` 零报错，但作者本意是转置。根本原因：shape 不在类型系统里，Tensor 注解对 (32,100) 还是 (100,32) 一无所知。实测能抓的是拼错参数名（SGD(learning_rate=) → TypeError）。顺带发现 pred.backward() 非标量时 PyTorch 自己会拦（grad can be implicitly created only for scalar outputs），那是运行时检查不是类型检查。**核心收获是两层防线：类型检查抓「接口用错」+ smoke test 抓「意图算错」**。测验 Q3 按课程答案选D 算对（选项本身不严谨，知识点已在讲义「实测纠正」一节）。产物：type_checking_demo.py。**流程违规**：本课漏写 zh.md就被大哥指出，根因是把约定挂成待办而非流程第一步，已在三处修正。 |
| 2026-10-10 | 0/09 | 3/3 | Data Management。热身 2/2（typeCheckingMode 选 D 但只有半边成立——shape 抓不到，第三次强调；Remote SSH 销账）。课前把今早的纯中文 zh.md 升级成双语+实测（外部进程写的，增量补未覆盖）。实测驱动：Parquet 全列 10.5x / 单列 61x（投影下推，跳列越多领先越大）、冷启动 12.7ms vs warm 0.18ms 差 70x、压缩率同质 text 11x vs 各异 3.2x。**纠正课文 Step 5 划分代码切出 70/10/20**（文字写 80/10/10，正确版一直在 data_utils.make_splits 里——示例代码没和产物对拍）；纠正 Arrow「小」（save_to_disk 落盘 ≈CSV，赢在 mmap 读速 0.001s）；本地 from_csv/from_json 也写 HF 缓存（0→27MB）。HF 直连+hf-mirror 均 Connection refused，下载环节用合成数据顶上。预测题1（单列优势更大）答对方向但没来得及答就跳过，已用数据补讲。产物：learning-artifacts/phase0/data_formats_lab.py。测验 3/3。 |
| 2026-10-10 | 0/10 | 3/3 | Terminal & Shell。热身 2/2（0/09 的三集划分目的与 streaming=True 都答对）。课前按新强制流程先确认/写出 zh.md（已存在 473 行含实测一节，按 Step 0.5 校验后跳过重写）。补课流程改进：把「先写 zh.md」从 LEARNING.md/MEMORY.md 升级为 learn skill 的 Step 0.5（skills/learn/SKILL.md:120，与 .claude/skills/learn/SKILL.md 同步），自检点=出第一道题前 zh.md 必须存在。讲透管道三条铁律：① stderr 不走管道（要 `2>&1`）；② `2>&1` 顺序陷阱口诀「先安家再搬家」；③ `$NF` = awk 最后一个字段（抠日志数值标配）。tmux 理解题一次答对 B，追问补坑：合盖睡眠不是 tmux 管的（本地用 caffeinate，云上才是 tmux 保护训练）。测验 3/3。Q2 SIGHUP 与 `&` 的辨析补讲。剩余 3 题应学员要求合并出题，节奏可以加快。 |
| 2026-10-10 | 0/11 | 3/3 | Linux for AI。热身 2/2（0/10 管道与 SIGHUP 复习全对）。课前按 Step 0.5 先写 zh.md（双语对照 + 实测纠正一节，含 macOS/BSD 与 Linux 的 sed -i ''/du -d 1 差异实测、sort -h 人类可读排序、rm -rf 无撤销教训）。讲透文件系统布局（/ ~ /tmp /usr /etc /var/log）、15 个核心命令、chmod 权限位（755=4+2+1 数字记法）、apt 先 update 再 install、kill/SIGTERM vs kill -9/SIGKILL、du/df 磁盘排查、scp vs rsync（大传输选 rsync）、macOS→Linux 踩坑表。理解题 3 连全对（chmod +x、kill 优雅停止、du 找空间大户），测验 3/3。补坑：chmod +x 后仍报错查 shebang。 |
| 2026-10-10 | 0/12 | 1/3 | Debugging & Profiling。热身 2/2（0/11 的 `~`=home、`sudo`=root 权限）。课前按 Step 0.5 先写 zh.md（双语对照 + 实测纠正一节）。讲解三层调试模型（标准 Python → Tensor 操作 → 训练动态，80% bug 在前两层）、debug_print/条件断点/logging/Timer 计时、四类静默 bug 抓法（shape hook、detect_nan、check_data_leakage、check_devices）、cProfile/line_profiler/tracemalloc/cuda.memory、OOM 五步、TensorBoard 看图口诀。理解题「99% 准确率先怀疑泄漏」答对 B。**测验 1/3：Q1 答对 B（数据泄漏），Q2/Q3 学员表示不知道——先补课再重测**。产物：debug_tools.py 实测输出进 zh.md（logging 四行 + tracemalloc 前5大分配；本机无 torch，torch 部分待学员环境跑）。 |
| 2026-10-10 | 1/01 | -- | Linear Algebra Intuition 开课（Phase 1 Math Foundations，用户明确要求从 Phase 1 开始，不跳数学）。课前 Step 0.5：写 zh.md（双语对照 + 实测纠正一节，实跑 code/vectors.py：点积 32、cosine 0.9746、旋转 90°→[-1,3]、Gram-Schmidt 三点积严格 0、[[1,2],[2,4]] 秩=1、5 个手算易错点）。热身 A/B 重测 0/12 的 Q2/Q3 答 C/C 全对销账；热身 C 点积题答 C（**错误**，正确 B「多相似/多同向」；距离是另一回事，归一化点积才是余弦相似度）。已当场补讲。 |
| 2026-10-10 | 1/02 | -- | Vectors, Matrices & Operations 开课（Build 型）。课前 Step 0.5：写 zh.md（双语对照 + 实测纠正一节，实跑 code/matrices.py 并核对：eWise=[[5,12],[21,32]] vs matmul=[[19,22],[43,50]]、det=10、A@A^-1 出 -0.0000（负零，判等要用 allclose）、广播 [[11,22,33],[14,25,36]]、两层网络 shape 链 (4x3)@(3x1)+(4x1)->(4x1)->ReLU）。热身 2/2 全对（embedding=D 向量表示；LoRA 复习项重测=A 低秩分解，0/1 遗留项销账）。 |
| 2026-10-10 | 1/03 | 2/3 | Matrix Transformations。课前 Step 0.5 写 zh.md（双语+mermaid 全保留+实测纠正，实跑 code/transformations.py）。热身 2/2 但**第 2 题答错**（单位矩阵：答 B「全是 1 的矩阵」，正确 A「乘完不变」；B 其实是 ones matrix J，行为相反）已补讲。讲解：矩阵的列=基向量落点、五种基本变换表（旋转/缩放/剪切/反射/单位 + det）、复合顺序 S@R=[0,0.5] vs R@S=[0,2.0]、特征值 A@v=λv、三角矩阵特征值=对角元、旋转矩阵复数特征值 1j/-1j、特征分解 V@D@V^-1、三用途（PCA/RNN 稳定性/谱方法）、det=面积缩放（**det=1 不等于旋转**，Scale(2,0.5) det 也是 1）。理解题 1/2：特征向量→A 对；行列式几何意义→**答 B 旋转角度（错，正确 C 面积缩放）**，已用「转 45° 与转 90° det 都是 1」反证补讲。**测验 2/3：Q1 顺序→C 对、Q2 RNN 特征值>1→C 对；Q3 特征分解 [[2,1],[1,2]] 学员表示不知道——已补课（λ=3 沿 [1,1] 拉伸 3 倍、λ=1 沿 [1,-1] 不动；干扰项 C 把对角线 2 误当特征值），待重测**。 |
| 2026-10-10 | 1/04 | 3/3 | Calculus for ML。Step 0.5 写 zh.md（942 行全 627 行 en.md 双语覆盖 + 实测纠正八节，实跑 code/derivatives.py 零依赖全通过）。热身 3 题清 1/03 复习项：1/2 答 A/C 对（单位矩阵=乘完不变、det=面积缩放）；**热身 3 又答 C（错，正确 D）**——已用实测数字钉死：`A@[1,1]=[3,3]` 比值 3.0、`A@[1,-1]` 比值 1.0、`A@[1,0]=[2,1]` 比值 2.236=√5，**对角线元素 2 不是特征值，特征值只在三角/对角矩阵时才等于对角元**。讲解九节（导数/偏导/梯度/梯度下降/数值 vs 解析/Hessian/泰勒/链式法则与反向传播/积分雅可比）。**实测三个宝藏**：① `x_new = (1-2·lr)·x` 精确几何衰减（5×0.8²⁰=0.0576 与实测吻合，lr<1 才收敛，0.5 一步到位，>1 发散）；② 数值导数误差 4.33e-09 而非 1e-14，**是浮点舍入主导**（eps·|f|/(2h)），h 不是越小越好，最优 1e-5~1e-7；③ Rosenbrock Hessian λ=1001.60/0.40 条件数≈2504，解释 Adam 为何必要；④ **线性回归里 w 比 b 收敛快 3 倍**（dw 多乘了 x，平均 x=3），结构性问题，归一化/Adam/学习率预热都是为它。理解题 A 对（梯度=最陡上升方向，训练时取负）。**测验 3/3 全对**（更新规则→D、牛顿法 Hessian N² 不可行→B、中心差分→C）。 |
| 2026-10-10 | 1/02 | 3/3 | Vectors, Matrices & Operations。课前 Step 0.5 写 zh.md（双语+实测纠正，实跑 code/matrices.py）。热身 2/2（embedding=D、LoRA 复习项=A 销账）。讲解：形状铁律 (m×n)@(n×p)=(m×p) 内侧必须相等、运算地图表、**逐元素 [[5,12],[21,32]] vs 矩阵乘 [[19,22],[43,50]]**（NumPy 把 @ 打成 * 是最常见静默 bug）、广播=沿缺失维度复制（bias 相加原理）、Matrix 类实现（matmul 三重循环 / 余子式展开求 det / det==0 抛奇异错 / inverse_2x2）、relu(W@x+b) 就是稠密层。理解题 2/2（广播→D；逐元素 vs 矩阵乘→B）。**测验 3/3 全对**（内侧维度→C、det=0→A 奇异无逆、转置→B 行列互换）。零错题。 |
| 2026-10-10 | 1/01 | 2/3 | Linear Algebra Intuition。热身 A/B 重测 0/12 Q2/Q3 答 C/C 全对销账；热身 C 点积题答 C（错误，正确 B，已当场补讲：点积=|a||b|cosθ 测方向对齐非距离，距离是 |a-b|，归一化点积才是余弦相似度）。讲解七节概念（向量是点/矩阵是变换/点积相似度/线性无关/基与秩/投影/QR=Gram-Schmidt）+ 实跑 code/vectors.py（点积 32、cosine 0.9746、旋转 90°→[-1,3]、Gram-Schmidt 三点积严格 0、[[1,2],[2,4]] 秩=1）。理解题：v1,v2,v3 线性无关判定答 B 对。**测验 2/3：Q1 答 B（线性无关）、Q2 答 A（秩=线性无关列数）全对；Q3 LoRA 学员表示不知道——已补课（LoRA=ΔW≈B·A 两个低秩矩阵，r=8 的玩具参数量是全量微调的 1/1000 量级），待重测**。 |

## 复习队列
- 1/03（矩阵变换与特征值）：未答出"A = V @ D @ V^-1 揭示了什么"——练习把特征值/特征向量对翻译成"沿 X 方向拉伸 k 倍"这类表述。
- 1/04（机器学习微积分）：Hessian 与牛顿法——曲率解读（临界点处特征值的符号）以及为什么 N×N 的 Hessian 不可行，进而理解 Adam 存在的意义。这部分是测验中途补讲的；用 check-understanding 测验再回顾一遍。
- 0/01（开发环境）：GPU 可用性检查 — `torch.cuda.is_available()` / `torch.backends.mps.is_available()` 与 `torch.__version__`（版本号说明不了硬件访问）。测验时弄混；课程中现场验证了 MPS。已解决 2026-10-09：0/02 热身中回忆正确。
- 0/03（GPU 设置与云）：系统级 vs 框架级 GPU 工具——`nvidia-smi` 是标准的硬件状态检查（不依赖 Python 也能跑）；`torch.cuda.list_devices()` 根本不存在。学员选了假 API；强化分层规则：查硬件状态用第 1 层系统工具，查框架可用性用第 4 层 API。已解决 2026-10-09：0/04 热身中回忆正确。
- 0/04（API 与密钥）：① 认证头的厂商差异——OpenAI/DeepSeek 用 `Authorization: Bearer`，Anthropic 用 `x-api-key` + `anthropic-version`；裸 HTTP 调试时必须带对头。② 限流处理——超限返回 HTTP 429，不会自动排队；客户端须自己重试（指数退避 + 读 `Retry-After`）。Phase 13 起 agent 循环调用前必须掌握。
- 0/05（Jupyter Notebook）：kernel 状态依赖这条铁律要保持住——**notebook 的正确性取决于点击顺序，不是文件里的顺序**。Phase 3 起每写一个训练 notebook 都养成两个习惯：① 每隔一段就 Restart & Run All；② 跑通的代码立刻挪进 `.py`，挪不动说明有幽灵状态。已解决 2026-10-09：0/04 的x-api-key 与 429 两项在0/05 热身中回忆正确。
- 0/06（Python环境）：① **本课程 `.venv` 是 uv 建的，里面没有 pip**——跑 `python -m pip` 会报 `No module named pip`（误导性报错，不说工具用错）。用 `uv pip install` / `uv add`。② 判定自己在不在环境里看 `sys.prefix != sys.base_prefix`，或 `which python` 的路径，**不要看版本号**。③ 隔离的本质是 `pyvenv.cfg` 里 `include-system-site-packages = false` 这一行；`activate` 只改 PATH，`deactivate` 只是把 PATH 字符串还原。这些在 Phase 4 起多环境并行时会直接用到。
- 0/07（Docker）：① **Dockerfile 写法的四条硬规则**（Phase 11 起构建训练镜像会直接用到）：`apt-get update` 必须与 `install` 合并成一条 RUN（分开会让 install 命中过期索引）；每个 `pip install` 要 `--no-cache-dir`（否则 pip 缓存固化进镜像层，重建全重下）；变化最频繁的指令放最后（重建范围最小）；**绝不 `curl | bash`**，要下载 → sha256 校验 → 执行三步分开。② **Apple Silicon 的现实约束**：PyTorch `cu124` wheel 只发 x86_64，没有 arm64；Mac 上要么加 `--platform=linux/amd64` 走模拟（慢且无 GPU），要么用 CPU 版 wheel，要么直接用 MPS 原生跑。判据用 `dockerfile_layer_analyzer.py`。③ Compose 里**服务名即 DNS 主机名**（`http://qdrant:6333`），Compose 内建 DNS 自动解析——和 Nacos 服务发现同类问题，只是 DNS 由 Compose 提供。
- 0/08（编辑器）：① **两层防线的分工**——类型检查（basic 模式）只抓「接口用错」：拼错参数名、参数类型传错、import 路径错、返回值不符声明；**抓不到「意图算错」：维度混淆、该mean 用了 sum、tensor 当 numpy 用**。后者才是 AI 工程真正会浪费几小时的。Phase 3 起每写一个训练模块，配一个 5 行 smoke test（断言关键张量 shape + loss 量级）。② `settings.json` 里对本项目最有用的几项：`"[python]"` 独立块（formatOnSave 只作用于 .py）、`editor.renderWhitespace: "trailing"`（只显行尾空格，Python 隐形 bug 克星）、`notebook.output.textLineLimit: 500`、`files.autoSaveDelay: 1000`、`search.exclude: "**/.venv": true`（跳过 1375 MB 的 .venv）。③ 本机 VS Code.app 已装但 `code` 命令未进 PATH；需要时 `/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code --install`。④ Remote SSH 是以后上GPU 服务器的主力，配好 `~/.ssh/config` 后 VS Code 里直接选主机名连上。
- 1/03（矩阵变换，**复习项**）：① 单位矩阵的判据是「**乘完不变**」（`A@I=A`），不是「全是 1」（那是 ones matrix J，会把信息揉成列和）。② 行列式几何意义是「**面积/体积缩放倍数**」，不是旋转角——旋转 45° 与 90° 的 det 都是 1，反证它不编码角度；角度在矩阵元素或复数特征值的辐角里。③ 特征分解 `[[2,1],[1,2]]` = 沿 [1,1] 拉伸 3 倍、[1,-1] 不变（正确 D）；干扰项 C「压缩 2 倍」把对角线元素 2 误当特征值。三题已补课，下次热身重测。
- 1/01（线性代数直觉，**复习项**）：Q3 LoRA 的正确答案是 **A「把权重更新分解成两个小的低秩矩阵」**（ΔW≈B·A，r≪d；直觉：大权重矩阵的"改动"其实是低秩的，不用动原矩阵）。已补课，下次热身重测。
- 0/12（调试与性能分析，**复习项已销账**）：Q2/Q3 已于 2026-10-10 开 1/01 时热身重测答 C/C 全对（数据加载是隐藏瓶颈→修法 num_workers>0；NaN 根因排查→正确动作是 detect_nan 逐参数查梯度+故障点 breakpoint，已补讲「逆向追第一个 NaN」机制）。
- 0/10（终端）+ 0/11（Linux）：**工具箱已齐**——grep/awk/tail -f/2>&1 处理大日志、tmux 三窗格管理训练、chmod/apt/kill/du/df/scp/rsync 运维远程 GPU 机器。macOS→Linux 三个高频坑：`sed -i ''` 空串、`du -d 1` 非 `--max-depth`、大小写敏感。下一课 0/12 调试与性能分析，学完 Phase 0 收官进 Phase 3。
- 0/09（数据管理）：① **划分算法**——要 x/y/z，先 `test_size=y+z` 切出尾部，再对尾部 `test_size=z/(y+z)` 切开；80/10/10 是对半分那 20%，70/15/15 是对半分那 30%。**教训：课文示例代码必须与产物对拍**（Step 5 内联代码 70/10/20 vs make_splits 80/10/10）。② 量化记忆列式优势：单列 61x / 全列 10.5x——**跳过的列越多优势越大**；`usecols` 省解析不省 I/O。③ 任何 benchmark 先 warm（冷启动 70x 假象，0/05 铁律）。④ 本地 `Dataset.from_*` 也写 `~/.cache/huggingface/datasets/` 缓存，磁盘账要算。⑤ test 集是高考只考一次，调参用 val；seed 是实验坐标系，不设 seed 两次划分必不同。
