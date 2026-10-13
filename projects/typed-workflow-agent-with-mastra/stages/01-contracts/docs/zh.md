# Validate typed step inputs at runtime · 在运行时校验类型化的步骤输入

> 对 workshop 策略执行 find 会产生读取意图（read intent）；对 workshop 标签执行 update 会产生写入意图（write intent）。空白 ID 在选择工具之前就会失败。unchanged 里面的 change 一词不会命中变更动词（mutation verb）的词边界。

> Find the workshop policy produces read intent. Update the workshop label produces write intent. A blank ID fails before a tool is chosen. The word change inside unchanged does not match the mutation-verb word boundary.

**Type:** Build
**Stage:** 1 of 4
**Time:** About 2 hours

## The useful boundary · 有用的边界

TypeScript 的类型并不能校验一个 JSON 文件。要求 ID 和 message 非空，对两者做 trim，并拒绝超过 10000 个字符的 message。然后把显式的变更动词 update、delete、change、cancel 用作教学用的意图（intent）基线。要让分类器的局限始终可见。

```figure
pj-typed-workflow-agent-with-mastra-1
```

> A TypeScript type does not validate a JSON file.
> Require a nonempty ID and message, trim both and reject messages beyond 10000 characters.
> Then use the explicit mutation verbs update, delete, change and cancel as an educational intent baseline.
> Keep the classifier's limits visible.

## Work the example · 做一遍示例

对 workshop 策略执行 find 会产生读取意图；对 workshop 标签执行 update 会产生写入意图。空白 ID 在选择工具之前就会失败。unchanged 里面的 change 一词不会命中变更动词的词边界。

在写代码之前，先写下要返回的字段和预期的副作用（side-effect）次数。保留一个应当失败的第二个输入，这样成功的示例就无法变成硬编码的答案。

> Find the workshop policy produces read intent. Update the workshop label produces write intent. A blank ID fails before a tool is chosen. The word change inside unchanged does not match the mutation-verb word boundary.
> Write the returned fields and the expected side-effect count before coding. Keep a second input that should fail so the successful example cannot become a hard-coded answer.

## Build the contract · 构建契约

在你的学习者工作区（learner workspace）里实现 `parseTicket(raw), classify(raw) in main.ts`。保留导出的名称，并继续复用此前阶段（stage）的成果，而不是把它们的策略再复制一遍。

被选中的工具决定了后续的审批（approval）要求。一份词表无法授权真实世界的动作，也无法可靠地推断每一种自然语言意图。输出是一个带类型的分类结果（typed classification），包含原始的已校验工单（ticket）、意图和主题（topic）。

> Implement `parseTicket(raw), classify(raw) in main.ts` in your learner workspace. Preserve the exported names and continue using earlier stages rather than duplicating their policies.
> The selected tool determines the later approval requirement. A word list cannot authorize real-world actions or reliably infer every natural-language intention. The output is a typed classification with the original validated ticket, intent and topic.

## Hints · 提示

写一张短语表，把假阳性（false positives）和假阴性（false negatives）都暴露出来。把运行时输入类型的测试与分类行为的测试分开进行。Node 会剥离 TypeScript 类型标注；它不会替你运行静态类型检查器。

> Write a table of phrases that expose false positives and false negatives. Test runtime input types separately from classification behavior. Node strips TypeScript annotations; it does not run a static type checker for you.

## Verify your work · 验证你的成果

```bash
python3 scripts/project_test.py typed-workflow-agent-with-mastra --init my-typed-workflow-agent-with-mastra
python3 scripts/project_test.py typed-workflow-agent-with-mastra --stage 1 --path my-typed-workflow-agent-with-mastra --strict
```

只需初始化一次。累积测试（cumulative tests）会导入你的工作区并保留你早先的源码。运行参考实现（reference solution）验证的是教学实现，永远不会给学习者颁发证书。可选的 SDK 检查需要项目 README 中的依赖和命令。

> Initialize once. Cumulative tests import your workspace and preserve your earlier source. A reference-solution run verifies the teaching implementation and never grants a learner certificate. Optional SDK checks require the dependencies and commands in the project README.

## Inspect the result · 检查结果

哪些校验属于传输边界（transport boundary），哪些判断属于工具能力检查（tool capability check）？

完成整个项目后，你会得到一份 scratch 版的 HTML/JSON 工作流评审，以及一次真实的 Mastra 运行：结果存入 SQLite，并附带一份与计划绑定的审批文档（plan-bound approval document）。

```bash
cd projects/typed-workflow-agent-with-mastra/solution
node --experimental-strip-types cli.ts --ticket fixtures/ticket.json --out workflow-output
```

把这个 fixture 换成来自你自己工作流的一小段输入。把预期结果和观察到的证据放在一起保存，另外再留一组单独的用例用于评估。Provider 请求测试证明的是序列化和控制流，而不是模型质量。

> Which validation belongs at the transport boundary, and which decision belongs in a tool capability check?
> The completed project produces a scratch HTML/JSON workflow review and a real Mastra run stored in SQLite with a plan-bound approval document.
> Replace the fixture with a small input from your own workflow. Keep expected outcomes and observed evidence together, then retain a separate set of cases for evaluation. Provider request tests establish serialization and control flow; they do not establish model quality.

## Primary reference · 主要参考

[官方 API 文档](https://mastra.ai/docs/workflows/suspend-and-resume)。实现、策略选择和示例均为原创。

> [Official API documentation](https://mastra.ai/docs/workflows/suspend-and-resume). The implementation, policy choices and examples are original.
