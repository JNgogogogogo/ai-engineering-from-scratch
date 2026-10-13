# Return feedback that shows its source · 返回能显示来源的反馈

> Grade constrained short answers and reveal the supporting passage.

**Type:** Build  
**Language:** TypeScript  
**Stage:** 2 of 4  
**Time:** About 2 hours

## What you are building · 你在构建什么

对一个初学者项目来说，一个狭窄的评分契约比一个无法解释的模型分数更容易检视。对 Unicode 兼容形式、大小写、空白和句末标点做规范化（normalize）。与规范答案以及 deck 作者显式批准的变体（variant）进行比较。另一种措辞在日常语言里可能正确，但在这里仍然需要人工复核。

> For a beginner project, a narrow grading contract is easier to inspect than an unexplained model score. Normalize Unicode compatibility forms, case, whitespace and terminal sentence punctuation. Compare with the canonical answer and variants explicitly approved by the deck author. A different phrasing may be correct in ordinary language and still need manual review here.

```figure
pj-source-grounded-study-coach-2
```

## Work through an example · 过一遍示例

对于 paper envelopes，回答「PAPER   ENVELOPES!」在规范化之后会被接受。「Plastic envelopes」会失败。空回答会失败，即使标点在规范化过程中消失了也一样。如果作者把 a paper envelope 列为变体，那么这个精确的规范化变体也会被接受。

动手编码之前，先写下该示例应返回的字段，以及一个应当失败的输入。把预期结果放在实现旁边，这样你才能区分「契约变了」和「出了 bug」。

> For paper envelopes, the response PAPER   ENVELOPES! is accepted after normalization. Plastic envelopes fails. An empty response fails even if punctuation disappears during normalization. If the author includes a paper envelope as a variant, that precise normalized variant is also accepted.
> Before coding, write down the returned fields for that example and one input that should fail. Keep the expected result beside your implementation so you can distinguish a contract change from a bug.

## Implement the contract · 实现契约

- `normalizeAnswer(answer: string): string`
- `gradeAnswer(deck, cardId, response)`

返回 cardId、correct、expected、quote、sourceId、start、end、method 和 feedback。未知的卡片 ID 和非字符串的回答会抛出错误。在 feedback 里保留原始的 expected 答案与 quote；规范化属于比较环节，不属于对证据的改写。

> Return cardId, correct, expected, quote, sourceId, start, end, method and feedback. Unknown card IDs and nonstring responses raise an error. Keep the original expected answer and quote in feedback; normalization belongs to comparison, not evidence rewriting.

让之前的阶段保持可用。请在你的学习工作区（learner workspace）里实现这些函数；在过示例的过程中，保持参考解法（reference solution）关闭、不要查看。

> Keep earlier stages working. Implement these functions in your learner workspace, leaving the reference solution closed while you work through the example.

## Hints and failure cases · 提示与失败情形

测试正反两类「差一点」的邻近情形（near-miss）。子串匹配规则会错误地接受 not paper envelopes。把精确相等与显式变体在 method 字段里呈现清楚。不要把正确性解释成一个置信度分数。

> Test positive and negative near-misses. A substring rule would incorrectly accept not paper envelopes. Keep exact equality and explicit variants visible in the method field. Do not interpret correctness as a confidence score.

## Run your stage · 运行你的阶段

从仓库根目录初始化一次，然后运行累计测试：

```bash
python3 scripts/project_test.py source-grounded-study-coach --init my-source-grounded-study-coach
python3 scripts/project_test.py source-grounded-study-coach --stage 2 --path my-source-grounded-study-coach
```

起始代码（starter）会刻意抛出一个实现错误。之后的初始化会保留你的源码，而不是替换它。要通过测试，每个被选中的测试都必须真正运行；被跳过的测试不能作为完成的证据。

> Initialize once from the repository root, then run the cumulative tests:
> The starter deliberately raises an implementation error. Later initialization preserves your source rather than replacing it. A passing result requires every selected test to run; a skipped test is not completion evidence.

## Check your reasoning · 检查你的推理

一个科学上正确的同义词如果不在 accepted 里，会有什么结果？你会如何让教师复核这些假阴性（false negative），又不削弱证据要求？

> What happens to a scientifically valid synonym absent from accepted? How would you let a teacher review these false negatives without weakening evidence requirements?

## Connect it to the finished artifact · 与最终产物的关联

最终产物是一个独立的「揭晓答案」练习页面，以及带有到期卡片和可复现调度状态的 progress.json。核心只使用人工编写的题目和精确的规范化答案匹配；它不评判任意的作文，也不推断理解程度。复习间隔是一种确定性的教学策略，不是经过实证验证的学习效果结论。来源偏移量使用 JavaScript 的 UTF-16 码元（code unit）。

> A standalone answer-reveal practice page and progress.json with due cards and reproducible schedule state. The core uses authored questions and exact normalized answer matching. It does not judge arbitrary essays or infer understanding. The review intervals are a deterministic teaching policy, not an empirically validated learning-outcome claim. Source offsets use JavaScript UTF-16 code units.

完成项目之后，用你自己的输入试一试：

```bash
cd my-source-grounded-study-coach
node --experimental-strip-types main.ts --deck ./fixtures/deck.json --attempts ./fixtures/attempts.json --initial-date 2026-09-01 --date 2026-09-03 --out ./study-output
```

增加一个 appeal（申诉）事件，把学习者的回答存储下来供教师查看。让复核结论与自动评分分开保存，并对 accepted 答案的编辑做版本管理。

> Add an appeal event that stores the learner's response for a teacher. Keep review outcomes separate from automatic grades and version accepted-answer edits.

## Primary reference · 主要参考

[官方 API 文档](https://nodejs.org/api/typescript.html)。实现、示例和测试夹具（fixture）均为原创。该参考解释底层 API；项目特定的策略已在上方说明。

> [Official API documentation](https://nodejs.org/api/typescript.html). The implementation, examples and fixtures are original. The reference explains the underlying API; the project-specific policies are stated above.
