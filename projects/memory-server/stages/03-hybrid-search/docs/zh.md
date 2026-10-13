# Score vectors in a real Rust process · 在真实的 Rust 进程里给向量打分

第 3 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 3 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

用标准 Rust 工具链编译 `score.rs`，通过 stdin 传入 query 向量和 document 向量。计算 cosine similarity，零范数向量返回 0。把 60% 的词法查询覆盖率与 40% 的 cosine 分数组合起来，并用 id 决出并列名次。在跨越进程边界之前，先测试维度和数值有限性（finite）。把 Rust 二进制编译到一个私有的临时目录里，并在进程正常退出时删除。绝不信任一个已经躺在可预测共享临时路径上的可执行文件。

本阶段的边界是 `cosineScores, MemoryStore.search`。保持之前阶段的行为不变：最终评分器会在同一个 workspace 上运行每一个阶段。

> Compile score.rs with the standard Rust toolchain and send query and document vectors over stdin. Compute cosine similarity, returning zero for a zero-norm vector. Combine 60 percent lexical query coverage with 40 percent cosine score and use ids to break ties. ... Never trust an executable already present at a predictable shared temporary path.

## Work through one concrete case · 走一遍具体案例

query 向量 `[1,1]` 与 document 向量 `[1,0]` 的 cosine 是 1/sqrt(2)，约 0.707。词法覆盖率取 0.5 时，混合分数是 `0.6*0.5+0.4*0.707`，约 0.583。

```figure
pj-memory-server-3
```

修改实验（lab）的输入，先自己算出结果，再去看它的指标。图中数字由这些输入计算而来；下面的实现测试仍然是完成与否的证据来源。

> Query vector[1,1] and document[1,0] have cosine 1/sqrt(2), about 0.707. With lexical coverage 0.5, the hybrid score is0.6*0.5+0.4*0.707, about 0.583. ... Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的 workspace `main.ts` 里实现 `cosineScores, MemoryStore.search`。先自己尝试契约，之后再去读参考实现中导出的类型。保留起始代码的公开名称，测试才能调用你的实现。核心函数返回结构化值，不要在核心函数内部打印；最终结果由 CLI 打印。

使用[公开的 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示交给随附的 driver。

在把逗号分隔的行发给 Rust 之前，先校验向量是有限的且长度相等。零范数按 0 分处理，并核对子进程真实返回的结果数量。

> Implement `cosineScores, MemoryStore.search` in your workspace `main.ts`. ... Validate finite, equal-length vectors before sending comma-separated rows to Rust. Treat zero norm as score 0 and check the real subprocess result count.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py memory-server --init learning-artifacts/memory-server` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py memory-server --stage 3 --path learning-artifacts/memory-server --strict
```

全新的 workspace 在你实现契约之前应当判为失败。每个阶段完成后，用随附的样例运行你的真实产物：

```bash
cd learning-artifacts/memory-server
node cli.ts --data-dir memory-data --put samples/memory.json
node cli.ts --data-dir memory-data --query "cache policy"
node cli.ts --data-dir memory-data --history cache-policy
```

> From the repository root, initialize once with `python3 scripts/project_test.py memory-server --init learning-artifacts/memory-server`. Then grade cumulatively ... A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample.

## Investigate the failure boundary · 探查失败边界

在实验里换一个 query，检查两个成分各自的贡献。字面上毫无重叠却拿到很高的哈希 cosine，那可能是碰撞（collision），不是语义支持。

> Change the query in the lab and inspect both contributions. A high hash cosine with no literal overlap may be a collision, not semantic support.

## References · 参考资料

[MCP tools 规范](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
[Rust 标准库](https://doc.rust-lang.org/std/)
[Node HTTP API](https://nodejs.org/api/http.html)
