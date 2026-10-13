# Verify every claim · 核验每一条论断

> 引用是「关于论断的论断」。去检查它，并让 harness（测试框架）决定运行何时结束。
> A citation is a claim about a claim. Check it, and let the harness decide when the run is done.

**Type:** Build
**Languages:** Python
**Stage:** 5 of 7 (core)
**Time:** ~2 hours

## What you build · 你要构建什么

`report_agent/critic.py`：

- `support_score(sentence, snippet_text)` 返回一个分数和一个原因。
- `review(markdown, snippets)` 为每个句子返回一个 `Verdict`。
- `apply_verdicts(report, verdicts)` 丢弃不被支撑的句子。
- `Budget` 限制步数和 token 数，`decide_state` 选出终态：`completed`、`needs_review` 或 `failed`。

> `support_score(sentence, snippet_text)` returns a score and a reason.
> `review(markdown, snippets)` returns one `Verdict` per sentence.
> `apply_verdicts(report, verdicts)` drops unsupported sentences.
> `Budget` limits steps and tokens, and `decide_state` picks the terminal state: `completed`, `needs_review` or `failed`.

## Why it matters · 为什么重要

你在第 4 阶段的写作器之所以诚实，是因为它在照抄。一旦模型来写散文，引用就会漂移：一个名词被换掉、一个 "not" 消失、一个数字变了，或者一个真实片段被挂到它从没说过的论断上。第二遍检查独立于写作器去核对被引用的证据。标记解析到某个来源只是语法层面的保证；来源是否支撑是另一个独立判断。

签入的公开 fixture 文件 `heldout/poisoned_drafts.json` 包含带有上述每种攻击的草稿，外加必须通过的忠实改写。这个遗留的文件夹名并不会让它们成为隐藏测试。你的 critic 必须抓住前者而不误伤后者。

> Your writer in stage 4 is honest because it copies. The moment a model writes the prose, citations drift: a name gets swapped, a "not" disappears, a number changes, or a real snippet gets attached to a claim it never made. A second pass checks the cited evidence independently of the writer. A marker resolving to a source is a syntactic guarantee; source support is a separate judgment.
> The checked-in public fixture file `heldout/poisoned_drafts.json` contains drafts with each of these attacks, plus faithful paraphrases that must pass. The legacy folder name does not make these hidden tests. Your critic has to catch the first without flagging the second.

## Support, in three rules · 支撑判定，三条规则

```python
def support_score(sentence, snippet_text):
    # 1. names and numbers must appear in the source
    # 2. negation words must match
    # 3. otherwise: share of the claim's content tokens found in the source
```

| 攻击 | 抓住它的规则 |
|---|---|
| 把 "The Hypervisor component intercepts system calls" 引到一句 interceptor 的句子上 | Hypervisor 是严格词，来源里没有 |
| 把 "Denylists are a security boundary" 引到 "Denylists are not a security boundary." | 否定不一致 |
| 把 "allows 5 destinations" 引到 "allows 10 destinations" | 数字 5 缺失 |
| 一个真实片段被挂到无关论断上 | 重叠度低或否定不匹配 |
| 没有标记的句子，或指向 `S9` 的标记 | uncited 或 dangling |

严格词（strict term）指：带数字的词、首字母之后还有大写的词（`microVMs`），以及在第一个位置之后出现的大写词。词面检查很粗糙，但它们快、零成本、可解释。它们也设定了基于模型的 judge 必须超越的门槛。

> Strict terms are words with digits, words with a capital after the first letter (`microVMs`), and capitalized words after the first position. Lexical checks are crude, but they are fast, free and explainable. They also set the bar a model-based judge has to beat.

## Budgets and terminal states · 预算与终态

模型永远不决定运行何时结束。决定者是 harness：

```python
budget = Budget(max_steps=50, max_tokens=20000)
budget.charge("plan", estimate_tokens(question))   # raises BudgetExceeded when over
```

| 状态 | 何时 |
|---|---|
| `completed` | 每个句子都被支撑 |
| `needs_review` | 有一些句子被丢弃 |
| `failed` | 预算耗尽，或没有任何内容被支撑 |

一个返回 `needs_review` 的运行不是失败。它是一份告诉人类「该看哪里」的报告。

```figure
pj-rra-critic
```

> A run that says `needs_review` is not a failure. It is a report that tells a human exactly where to look.

## Follow the mechanism · 理解机制

词面重叠是一个启发式，不是蕴含（entailment）模型。一份被照抄的错误来源可以通过，一句忠实的改写也可能被拒。把分数、阈值和拒绝原因留在每个 verdict 里，这样后来的语义 judge 可以与这条基线做比较，而不是悄悄取代它。

> Lexical overlap is a heuristic, not an entailment model. A copied false source can pass, and a faithful paraphrase can fail. Keep the score, threshold and rejection reason in each verdict so a later semantic judge can be compared with this baseline rather than silently replacing it.

## Your task · 你的任务

```python
class Budget:
    def __init__(self, max_steps=50, max_tokens=20000): ...
    def charge(self, step, tokens=0): ...
def strict_terms(sentence) -> set[str]: ...
def support_score(sentence, snippet_text) -> tuple[float, str]: ...
def review(markdown, snippets, threshold=0.6) -> list[Verdict]: ...
def decide_state(verdicts, budget_exceeded=False) -> str: ...
def apply_verdicts(report, verdicts) -> Report: ...
```

`snippets` 可以把 id 映射到 `Snippet` 对象，也可以映射到普通字符串。`snippet_text()` 两者都处理。

> `snippets` may map ids to `Snippet` objects or to plain strings. `snippet_text()` handles both.

## Run the tests · 运行测试

```bash
python3 scripts/project_test.py research-report-agent --stage 5 --path my-report-agent
```

## What you should see · 预期结果

第 5 阶段通过 9 个 Python 测试，且此前所有阶段仍然通过。全部六份带毒草稿都得到预期的 verdict 序列。实体替换、数字改动、否定改动和悬空标记被拒绝；忠实的改写通过。两步预算在第三次扣费之前停下。

> Stage 5 passes 9 Python tests, and all preceding stages still pass. All six poisoned drafts receive their expected verdict sequences. Entity swaps, changed numbers, negation changes and dangling markers are rejected; faithful paraphrases pass. A two-step budget stops before the third charge.

## Check yourself · 自检

1. 你的写作器在照抄片段。那为什么还要建一个 critic？
2. 找出一条你的 critic 会错误拒绝的改写。模型 judge 会做得更好在哪里？代价是什么？
3. 为什么 `needs_review` 比悄悄丢弃句子然后报告 `completed` 更安全？

> 1. Your writer copies snippets. Why build a critic at all?
> 2. Find a paraphrase that your critic wrongly rejects. What would a model judge do better, and what would it cost?
> 3. Why is `needs_review` safer than silently dropping sentences and reporting `completed`?

## Going further · 进阶

- 在 `Model` protocol 后面加一个模型 judge，处理词面分数落在 0.4 到 0.6 之间的句子，并把它的答案记录进 cassette。
- 写三份能骗过你的 critic 的新带毒草稿，然后修复 critic。

> - Add a model judge behind the `Model` protocol for sentences whose lexical score falls between 0.4 and 0.6, and record its answers in a cassette.
> - Write three new poisoned drafts that fool your critic, then fix the critic.

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html)和[检索增强生成](../../../../../phases/11-llm-engineering/06-rag/docs/en.md)。先完成[阶段 4](../../04-write-with-citations/docs/en.md)。

核验在有限的工作预算下检查词面支撑、数字和否定。critic 能拒绝一个被改过的超时值，但它无法证明一个来源在真实世界里为真或仍然有效。

```text
source timeout=15; draft timeout=60 -> reject number
no evidence -> failed or needs_review according to verdict state
budget exhausted -> named terminal state
```

> Verification checks lexical support, numbers and negation under a finite work budget. The critic can reject a changed timeout, but it cannot prove that a source is true or current in the real world.

## Build and inspect · 构建并检查

在开始下一个操作之前先为工作扣费。把被拒绝的论断保留在 trace 里，而不是抹掉「报告为何变短」的原因。

在你的学习工作区（learner workspace）中实现该阶段。这些 CLI 辅助工具是给定的适配器，它们导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py research-report-agent --stage 5 --path learning-artifacts/research-report-agent
```

先预测上面的中间状态，再运行该阶段。全新的 stub 会失败；参考实现跑通并不代表你的学习工作区已经完成。

> Charge work before starting the next operation. Preserve rejected claims in the trace rather than erasing the reason a report became shorter.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 下一步探究

在按照一条部署建议行动之前，你会增加什么独立检查？

> What independent check would you add before acting on a deployment recommendation?
