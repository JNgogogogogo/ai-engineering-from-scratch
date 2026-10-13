# Keep text, namespace and provenance together · 让 text、namespace 与溯源信息绑在一起

第 1 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 1 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

每条 memory 都需要一个有界长度的 id、namespace、text 和 source locator（来源定位）。绝不返回脱离出处的裸字符串。小型 feature-hashing embedding 把归一化后的词项映射进固定向量；它是确定性的词法投影，不是预训练的语义模型。哈希冲突是预期之内的，这也解释了为什么词法证据（lexical evidence）仍是检索的一部分。

本阶段的边界是 `validateMemory, embed`。保持之前阶段的行为不变：最终评分器会在同一个 workspace 上运行每一个阶段。

> Every memory needs a bounded id, namespace, text and source locator. Never return a detached string without its provenance. ... Hash collisions are expected and explain why lexical evidence remains part of retrieval. ... The boundary for this stage is `validateMemory, embed`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

## Work through one concrete case · 走一遍具体案例

一条 memory `{id:cache-policy,namespace:docs,text:...,source:policies/cache.md:12}` 把内容和证据放在一起。同一个 id 放在 `namespace:private` 里就是另一条记录。

```figure
pj-memory-server-1
```

修改实验（lab）的输入，先自己算出结果，再去看它的指标。图中数字由这些输入计算而来；下面的实现测试仍然是完成与否的证据来源。

> A memory {id:cache-policy,namespace:docs,text:...,source:policies/cache.md:12} keeps content and evidence together. The same id in namespace:private is a different record. ... Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的 workspace `main.ts` 里实现 `validateMemory, embed`。先自己尝试契约，之后再去读参考实现中导出的类型。保留起始代码的公开名称，测试才能调用你的实现。核心函数返回结构化值，不要在核心函数内部打印；最终结果由 CLI 打印。

使用[公开的 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示交给随附的 driver。

在哈希或写入之前先校验 JSON 边界。feature hashing 把词项映射进 32 个桶，不相关的词可能撞在一起；保留词法覆盖率（lexical coverage）正是为了暴露这个局限。

> Implement `validateMemory, embed` in your workspace `main.ts`. ... Preserve the starter's public names so tests can call your implementation. ... Validate the JSON boundary before hashing or writing. Feature hashing maps terms into 32 buckets, so unrelated words can collide; retain lexical coverage to expose that limitation.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py memory-server --init learning-artifacts/memory-server` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py memory-server --stage 1 --path learning-artifacts/memory-server --strict
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

构造两个 text 完全相同的 namespace。在 `docs` 里查询绝不能返回 `private` 的记录。

> Construct two namespaces with identical text. A query in docs must never return the private record.

## References · 参考资料

[MCP tools 规范](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
[Rust 标准库](https://doc.rust-lang.org/std/)
[Node HTTP API](https://nodejs.org/api/http.html)
