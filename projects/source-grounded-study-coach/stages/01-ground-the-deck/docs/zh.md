# Give every answer a source location · 给每个答案一个来源位置

> Validate authored cards against immutable source passages.

**Type:** Build  
**Language:** TypeScript  
**Stage:** 1 of 4  
**Time:** About 2 hours

## What you are building · 你在构建什么

一张练习卡片需要的不只是问题和答案。要为支撑引文（quote）存储来源 ID 以及 start/end 偏移量（offset）。这样学习者就能查看一个答案为什么是预期答案，编辑者也能发现被修改的来源何时会让一张卡片失效。在创建练习队列之前先做校验。

> A practice card needs more than a question and answer. Store the source ID and start/end offsets for the supporting quote. A learner can then inspect why an answer is expected, and an editor can detect when a changed source invalidates a card. Validate before creating a practice queue.

```figure
pj-source-grounded-study-coach-1
```

## Work through an example · 过一遍示例

来源文本为「Each packet records the harvest year」。一张询问「数据包记录的是哪一年」的卡片，其答案是「harvest year」，证据（evidence）覆盖那一句话。如果编辑者把答案改成「purchase year」而来源保持不变，校验会拒绝这张卡片。

动手编码之前，先写下该示例应返回的字段，以及一个应当失败的输入。把预期结果放在实现旁边，这样你才能区分「契约变了」和「出了 bug」。

> The source says Each packet records the harvest year. A card asking which year a packet records uses answer harvest year and evidence covering that sentence. If an editor changes the answer to purchase year while retaining the same source, validation rejects the card.
> Before coding, write down the returned fields for that example and one input that should fail. Keep the expected result beside your implementation so you can distinguish a contract change from a bug.

## Implement the contract · 实现契约

- `validateDeck(value: unknown): Deck`

要求存在 sources 与 cards 数组、唯一且非空的 ID、来源标题和非空文本。每张卡片必须指名一个已知的 source、给出非空的 question 和 answer，并提供满足 0 <= start < end <= text.length 的整数偏移量。规范答案（canonical answer）必须逐字出现在该引文之内。可接受的变体（variant）是显式列出的非空字符串。返回一份脱离原对象的副本（detached copy），这样后续对输入对象的编辑就无法改动已校验的 deck。

> Require sources and cards arrays, unique nonempty IDs, source titles and nonempty text. Every card names a known source, a nonempty question and answer, and integer offsets satisfying 0 <= start < end <= text.length. The canonical answer must occur verbatim within that quote. Accepted variants are explicit nonempty strings. Return a detached copy so later edits to the input object cannot alter the validated deck.

让之前的阶段保持可用。请在你的学习工作区（learner workspace）里实现这些函数；在过示例的过程中，保持参考解法（reference solution）关闭、不要查看。

> Keep earlier stages working. Implement these functions in your learner workspace, leaving the reference solution closed while you work through the example.

## Hints and failure cases · 提示与失败情形

用一个以 source ID 为键的映射（map）来做查找。把偏移量当作 UTF-16 位置处理，因为 JavaScript 的 slice 用的就是这个单位。在一个留出（held-out）示例中让引文前面带一个 emoji，用来暴露误用码点（code point）做索引的情况。

> Use a source-ID map for lookup. Treat offsets as UTF-16 positions because JavaScript slice uses that unit. Include an emoji before a quote in a held-out example to expose accidental code-point indexing.

## Run your stage · 运行你的阶段

从仓库根目录初始化一次，然后运行累计测试：

```bash
python3 scripts/project_test.py source-grounded-study-coach --init my-source-grounded-study-coach
python3 scripts/project_test.py source-grounded-study-coach --stage 1 --path my-source-grounded-study-coach
```

起始代码（starter）会刻意抛出一个实现错误。之后的初始化会保留你的源码，而不是替换它。要通过测试，每个被选中的测试都必须真正运行；被跳过的测试不能作为完成的证据。

> Initialize once from the repository root, then run the cumulative tests:
> The starter deliberately raises an implementation error. Later initialization preserves your source rather than replacing it. A passing result requires every selected test to run; a skipped test is not completion evidence.

## Check your reasoning · 检查你的推理

一个答案出现在 passage 之中，就能证明这个问题写得好吗？除了这些结构性检查之外，还有哪些部分需要编辑层面的审阅？

> Does an answer occurring in a passage prove that the question is well-written? Which parts need editorial review beyond these structural checks?

## Connect it to the finished artifact · 与最终产物的关联

最终产物是一个独立的「揭晓答案」练习页面，以及带有到期卡片和可复现调度状态的 progress.json。核心只使用人工编写的题目和精确的规范化答案匹配；它不评判任意的作文，也不推断理解程度。复习间隔是一种确定性的教学策略，不是经过实证验证的学习效果结论。来源偏移量使用 JavaScript 的 UTF-16 码元（code unit）。

> A standalone answer-reveal practice page and progress.json with due cards and reproducible schedule state. The core uses authored questions and exact normalized answer matching. It does not judge arbitrary essays or infer understanding. The review intervals are a deterministic teaching policy, not an empirically validated learning-outcome claim. Source offsets use JavaScript UTF-16 code units.

完成项目之后，用你自己的输入试一试：

```bash
cd my-source-grounded-study-coach
node --experimental-strip-types main.ts --deck ./fixtures/deck.json --attempts ./fixtures/attempts.json --initial-date 2026-09-01 --date 2026-09-03 --out ./study-output
```

增加一个 deck 版本号或来源摘要（digest），并且只在显式的迁移（migration）策略之下才让 attempts 失效。来源被编辑之后，不要悄悄地重新映射证据。

> Add a deck version or source digest and invalidate attempts only under an explicit migration policy. Do not silently remap evidence after source edits.

## Primary reference · 主要参考

[官方 API 文档](https://nodejs.org/api/typescript.html)。实现、示例和测试夹具（fixture）均为原创。该参考解释底层 API；项目特定的策略已在上方说明。

> [Official API documentation](https://nodejs.org/api/typescript.html). The implementation, examples and fixtures are original. The reference explains the underlying API; the project-specific policies are stated above.
