# Make the reading useful as a practice page · 让阅读内容变成可用的练习页面

> Export a portable reveal-and-review view with reproducible progress.

**Type:** Build  
**Language:** TypeScript  
**Stage:** 4 of 4  
**Time:** About 2 hours

## What you are building · 你在构建什么

完成后的页面让你输入答案，然后揭晓预期答案和支撑引文（quote）。它还会显示每张卡片的到期时间。在揭晓来源之后，学习者在本地核对并记录实际输入的答案。页面会显示下一个到期日，并把先前的加上新的 attempts 下载为 JSON 供 CLI 使用。对一张卡片重新记录会编辑它在当前会话（session）里的 attempt，而在下载之前重新加载页面会把它丢弃。该页面不发出任何网络请求。

> The finished page lets you type an answer, then reveal the expected answer and supporting quote. It also shows when each card is due. After revealing the source, the learner checks and records the actual typed answer locally. The page shows the next due date and downloads prior plus new attempts as JSON for the CLI. Re-recording a card edits its current session attempt, and reloading before download discards it. The page makes no network requests.

```figure
pj-source-grounded-study-coach-4
```

## Work through an example · 过一遍示例

人工编写的 seed-library deck 包含三张卡片。在两次答对 storage、一次答错 harvest-year 之后，9 月 3 日的报告会把未动过的 sorting 卡片和 harvest-year 卡片列为到期。storage 卡片在 9 月 4 日到期。用相同的事件重新导出会复现这些日期。

动手编码之前，先写下该示例应返回的字段，以及一个应当失败的输入。把预期结果放在实现旁边，这样你才能区分「契约变了」和「出了 bug」。

> The authored seed-library deck contains three cards. After two correct storage answers and one incorrect harvest-year answer, the September 3 report lists the untouched sorting card and the harvest-year card as due. The storage card is due September 4. Exporting the same events reproduces these dates.
> Before coding, write down the returned fields for that example and one input that should fail. Keep the expected result beside your implementation so you can distinguish a contract change from a bug.

## Implement the contract · 实现契约

- `renderPractice(deck, progress, date): string`
- `exportPractice(deck, attempts, initialDate, date, out)`
- `proposeCard(source, endpoint, model, apiKey="")`

写出 progress.json 和 index.html。拒绝早于初始日期或早于任何 attempt 的报告日期。对问题、答案、来源标题和引文做转义（escape）。在 method 里包含精确评分与教学调度器两种方法。可选的真实 HTTP 提案适配器（adapter）必须要求非空的问题、答案和逐字引文；答案出现在引文之内，引文出现在来源之内。把模型提案单独保存，供作者审阅。

> Write progress.json and index.html. Reject a report date before the initial date or before any attempt. Escape questions, answers, source titles and quotes. Include the exact-grading and teaching-scheduler methods. The optional real HTTP proposal adapter must require nonempty question, answer and verbatim quote; answer occurs inside quote and quote inside source. Save model proposals separately for author review.

让之前的阶段保持可用。请在你的学习工作区（learner workspace）里实现这些函数；在过示例的过程中，保持参考解法（reference solution）关闭、不要查看。

> Keep earlier stages working. Implement these functions in your learner workspace, leaving the reference solution closed while you work through the example.

## Hints and failure cases · 提示与失败情形

用原生的 details/summary 实现答案揭晓，这样页面不需要框架或服务器就能工作。测试一个形似 HTML 的来源标题。对适配器，运行一个本地 HTTP 服务器，检查它发出的请求，并分别返回有效与伪造的证据。

> Use native details/summary for answer reveal so the page works without a framework or server. Test an HTML-like source title. For the adapter, run a local HTTP server that inspects the outgoing request and returns both valid and fabricated evidence.

## Run your stage · 运行你的阶段

从仓库根目录初始化一次，然后运行累计测试：

```bash
python3 scripts/project_test.py source-grounded-study-coach --init my-source-grounded-study-coach
python3 scripts/project_test.py source-grounded-study-coach --stage 4 --path my-source-grounded-study-coach
```

起始代码（starter）会刻意抛出一个实现错误。之后的初始化会保留你的源码，而不是替换它。要通过测试，每个被选中的测试都必须真正运行；被跳过的测试不能作为完成的证据。

> Initialize once from the repository root, then run the cumulative tests:
> The starter deliberately raises an implementation error. Later initialization preserves your source rather than replacing it. A passing result requires every selected test to run; a skipped test is not completion evidence.

## Check your reasoning · 检查你的推理

只带一个 index.html，学习者在离线状态下能做什么？要重新计算进度或迁移到另一个界面，他们必须保留什么？

> What can a learner do offline with only index.html? What must they retain to recompute progress or move to another interface?

## Connect it to the finished artifact · 与最终产物的关联

最终产物是一个独立的「揭晓答案」练习页面，以及带有到期卡片和可复现调度状态的 progress.json。核心只使用人工编写的题目和精确的规范化答案匹配；它不评判任意的作文，也不推断理解程度。复习间隔是一种确定性的教学策略，不是经过实证验证的学习效果结论。来源偏移量使用 JavaScript 的 UTF-16 码元（code unit）。

> A standalone answer-reveal practice page and progress.json with due cards and reproducible schedule state. The core uses authored questions and exact normalized answer matching. It does not judge arbitrary essays or infer understanding. The review intervals are a deterministic teaching policy, not an empirically validated learning-outcome claim. Source offsets use JavaScript UTF-16 code units.

完成项目之后，用你自己的输入试一试：

```bash
cd my-source-grounded-study-coach
node --experimental-strip-types main.ts --deck ./fixtures/deck.json --attempts ./fixtures/attempts.json --initial-date 2026-09-01 --date 2026-09-03 --out ./study-output
```

使用「Download attempts JSON」按钮，然后把该文件传给 --attempts，并把选定的复习日期作为 --date。为生成的题目增加一个单独的留出（held-out）评估；一条可用的传输通道和浏览器事件导出并不能证明题目质量。

> Use the Download attempts JSON button, then pass that file to --attempts with the selected review date as --date. Add a separate held-out evaluation of generated questions; a working transport and browser event export do not establish question quality.

## Primary reference · 主要参考

[官方 API 文档](https://nodejs.org/api/typescript.html)。实现、示例和测试夹具（fixture）均为原创。该参考解释底层 API；项目特定的策略已在上方说明。

> [Official API documentation](https://nodejs.org/api/typescript.html). The implementation, examples and fixtures are original. The reference explains the underlying API; the project-specific policies are stated above.
