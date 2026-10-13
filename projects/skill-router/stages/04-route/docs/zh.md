# Abstain on ambiguous or blocked requests · 对模糊或被拦截的请求弃权

**Stage 4 of 4 · 第 4 阶段（共 4 阶段）。** TypeScript。计划约 2 小时。

把排序与依赖规划拼接起来，同时保留四种彼此区分的结果：ready、no-match、ambiguous 和 blocked。只要分差低于 margin（阈值），就是 ambiguous，即使 tie-breaker 已经决出了第一名。排出的赢家仍可能被权限拦截。无论哪种结果，都要返回带排名的解释，让调用方能够展示这次决策。

> Join ranking and dependency planning while preserving four distinct outcomes: ready, no-match, ambiguous and blocked. A score gap below the margin is ambiguous even if the tie-breaker produces a first result. A ranked winner can still be blocked by permissions. Return the ranked explanations in every outcome so a caller can display the decision.

本阶段的实现边界是 `route`。保持此前阶段的行为不变：最终评分器（grader）会在同一个工作区上运行每一个阶段。

> The boundary for this stage is `route`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

```figure
pj-skill-router-4
```

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [TypeScript object types](https://www.typescriptlang.org/docs/handbook/2/objects.html) 和 [Tool schema design](../../../../../phases/13-tools-and-protocols/05-tool-schema-design/docs/en.md)。先完成 [阶段 3](../../03-dependencies/docs/en.md)。

> Before coding, review [TypeScript object types](https://www.typescriptlang.org/docs/handbook/2/objects.html) and [Tool schema design](../../../../../phases/13-tools-and-protocols/05-tool-schema-design/docs/en.md). Complete [stage 3](../../03-dependencies/docs/en.md) first.

当两个技能得分过于接近，或所选计划需要不可用的权限时，就弃权（abstain）。一份「路由为什么停在这里」的解释，比一个武断选出的赢家技能更有用。

> Abstain when two skills score too closely or the chosen plan needs unavailable permissions. An explanation of why routing stopped is more useful than an arbitrary winning skill.

```text
publish request -> release-publish score 2
allowed=[read]; publish requires network
status=blocked, no execution plan
```

## Build and inspect · 构建与检视

先应用分差（margin）判断，再做依赖规划。把排序当作选择时的证据，而不是执行某个工具的授权。

> Apply the score margin before dependency planning. Treat ranking as evidence for selection, not authority to execute a tool.

请在你的学习者工作区（learner workspace）中实现本阶段。CLI 辅助工具是预先提供的适配器，它们导入你的函数；它们不能替代参考实现。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py skill-router --stage 4 --path learning-artifacts/skill-router
```

累计各阶段都通过之后，从仓库根目录用最初的示例输入运行你的产物：

> After the cumulative stages pass, run your artifact on the original sample input from the repository root:

```bash
node learning-artifacts/skill-router/cli.ts projects/skill-router/examples/skills projects/skill-router/examples/request.json
```

SKILL.md 提供标准的 name 和 description；routing.json 是本项目有文档记录的本地扩展。路由器只输出计划与解释，绝不执行被选中的技能。关键词分词是 ASCII 词法基线；多语言路由模型可以作为扩展。

> SKILL.md provides standard name and description; routing.json is this project's documented local extension. The router emits plans and explanations, and never executes a selected skill. Keyword tokenization is an ASCII lexical baseline; a multilingual routing model is an extension.

## Investigate next · 接下来探究

你会如何调一个引发 ambiguous 的关键词，又不过拟合到这个示例请求？

> How would you tune one ambiguous keyword without overfitting to the example request?
