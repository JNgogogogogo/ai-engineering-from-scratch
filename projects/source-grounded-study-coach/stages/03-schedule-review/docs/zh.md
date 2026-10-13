# Replay attempts into a visible schedule · 把 attempts 重放出一份可见的日程

> Derive due dates from stable, dated attempt events.

**Type:** Build  
**Language:** TypeScript  
**Stage:** 3 of 4  
**Time:** About 2 hours

## What you are building · 你在构建什么

把 attempts 作为事件（event）存储，这样进度就可以被重新计算。每个事件包含 ID、卡片 ID、日期和答案。完全重复的事件不应该让一张卡片前进两次。同一个 ID 被复用且内容不同则是一个错误。先按日期、再按事件 ID 排序，让同一天内的顺序具有确定性。

> Store attempts as events so progress can be recomputed. Each event has an ID, card ID, date and answer. Exact duplicate events should not advance a card twice. A reused ID with different contents is an error. Sort by date and then event ID to make same-day ordering deterministic.

```figure
pj-source-grounded-study-coach-3
```

## Work through an example · 过一遍示例

9 月 1 日第一次答对会把一张卡片移到 box 1，9 月 2 日到期。9 月 2 日答对会把它移到 box 2，9 月 4 日到期。答错会把 box 重置为 0，并把下一次安排在次日。box 的上限是 5，其答对间隔是 16 天。

动手编码之前，先写下该示例应返回的字段，以及一个应当失败的输入。把预期结果放在实现旁边，这样你才能区分「契约变了」和「出了 bug」。

> A first correct response on September 1 moves a card to box 1, due September 2. A correct response on September 2 moves it to box 2, due September 4. An incorrect response resets the box to 0 and schedules the next day. Boxes cap at 5, whose correct interval is 16 days.
> Before coding, write down the returned fields for that example and one input that should fail. Keep the expected result beside your implementation so you can distinguish a contract change from a bug.

## Implement the contract · 实现契约

- `parseDay(value: string): number`
- `buildProgress(deck, attempts, initialDate): Progress[]`
- `dueCards(progress, date): Progress[]`

只接受真实存在的 YYYY-MM-DD 日期；9 月 31 日必须失败。attempts 不能早于 initialDate，也不能引用未知的卡片。每张卡片从 box 0 开始，到期日为 initialDate。答对前进一个 box，间隔取 2^(box-1) 天；答错则重置并间隔一天。按 deck 顺序返回 progress；dueCards 选取 due <= date 的卡片，并先按到期日、再按卡片 ID 排序。

> Accept only real YYYY-MM-DD dates; September 31 must fail. Attempts cannot precede initialDate or refer to unknown cards. Start every card at box 0 due on initialDate. Correct answers advance one box and use 2^(box-1) days; incorrect answers reset and use one day. Return progress in deck order; dueCards selects due <= date and sorts by due date then card ID.

让之前的阶段保持可用。请在你的学习工作区（learner workspace）里实现这些函数；在过示例的过程中，保持参考解法（reference solution）关闭、不要查看。

> Keep earlier stages working. Implement these functions in your learner workspace, leaving the reference solution closed while you work through the example.

## Hints and failure cases · 提示与失败情形

在 UTC 零点做日历运算，以避开本地夏令时切换。在处理之前先对事件去重。把一个乱序的输入列表与其排序后的等价列表做对照，把一个跨月的边界日期与一个显式的期望日期做对照。

> Perform calendar arithmetic at UTC midnight to avoid local daylight-saving shifts. Deduplicate events before processing. Check an out-of-order input list against its sorted equivalent and a month-boundary date against an explicit expected date.

## Run your stage · 运行你的阶段

从仓库根目录初始化一次，然后运行累计测试：

```bash
python3 scripts/project_test.py source-grounded-study-coach --init my-source-grounded-study-coach
python3 scripts/project_test.py source-grounded-study-coach --stage 3 --path my-source-grounded-study-coach
```

起始代码（starter）会刻意抛出一个实现错误。之后的初始化会保留你的源码，而不是替换它。要通过测试，每个被选中的测试都必须真正运行；被跳过的测试不能作为完成的证据。

> Initialize once from the repository root, then run the cumulative tests:
> The starter deliberately raises an implementation error. Later initialization preserves your source rather than replacing it. A passing result requires every selected test to run; a skipped test is not completion evidence.

## Check your reasoning · 检查你的推理

既然调度器是确定性的，为什么同一天的两次答对仍可能夸大学习效果？对于真实的学习者，你会修改哪一条调度策略？

> Why might two same-day correct attempts overstate learning even though the scheduler is deterministic? Which scheduling policy would you change for real learners?

## Connect it to the finished artifact · 与最终产物的关联

最终产物是一个独立的「揭晓答案」练习页面，以及带有到期卡片和可复现调度状态的 progress.json。核心只使用人工编写的题目和精确的规范化答案匹配；它不评判任意的作文，也不推断理解程度。复习间隔是一种确定性的教学策略，不是经过实证验证的学习效果结论。来源偏移量使用 JavaScript 的 UTF-16 码元（code unit）。

> A standalone answer-reveal practice page and progress.json with due cards and reproducible schedule state. The core uses authored questions and exact normalized answer matching. It does not judge arbitrary essays or infer understanding. The review intervals are a deterministic teaching policy, not an empirically validated learning-outcome claim. Source offsets use JavaScript UTF-16 code units.

完成项目之后，用你自己的输入试一试：

```bash
cd my-source-grounded-study-coach
node --experimental-strip-types main.ts --deck ./fixtures/deck.json --attempts ./fixtures/attempts.json --initial-date 2026-09-01 --date 2026-09-03 --out ./study-output
```

增加一个有文档说明的同日推进上限（cap），或者另一种调度策略。在同一个 attempt 日志上比较行为，而不是仅凭间隔长度就宣称学习效果更好。

> Add a documented same-day advancement cap or an alternative scheduling policy. Compare behavior on the same attempt log instead of claiming better learning from interval length alone.

## Primary reference · 主要参考

[官方 API 文档](https://nodejs.org/api/typescript.html)。实现、示例和测试夹具（fixture）均为原创。该参考解释底层 API；项目特定的策略已在上方说明。

> [Official API documentation](https://nodejs.org/api/typescript.html). The implementation, examples and fixtures are original. The reference explains the underlying API; the project-specific policies are stated above.
