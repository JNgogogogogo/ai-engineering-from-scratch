# Plan the research · 规划研究

> 一个问题背后藏着好几个问题。先拆分再检索，并让模型保持可选。
> One question hides several. Split it before you search, and make the model optional.

**Type:** Build
**Languages:** Python
**Stage:** 3 of 7 (core)
**Time:** ~2 hours

## What you build · 你要构建什么

- `report_agent/planner.py`：`plan_research(question, model=None)` 返回一个 `Plan`，内含一组 `Facet`。每个 facet 有一个 id、一个用作报告小标题的 label、一个子问题和关键词。
- `report_agent/model.py`：一个 `Model` protocol、一个从录制好的 cassette（卡带）里取答案的 `ReplayModel`，以及一个想用时可以指向任何 chat-completions 兼容端点的 `LiveModel`。

> `report_agent/planner.py`: `plan_research(question, model=None)` returns a `Plan` with a list of `Facet`s. Each facet has an id, a label for the report heading, a sub-question and keywords.
> `report_agent/model.py`: a `Model` protocol, a `ReplayModel` that answers from a recorded cassette, and a `LiveModel` you can point at any chat-completions-compatible endpoint when you want to.

## Why it matters · 为什么重要

"为什么容器对 agent 代码来说是个弱沙箱？"实际上是四个问题：容器是什么、它怎么工作、它在哪里失效、什么时候该换别的方案。一份计划在检索开始之前就把这些相互独立的覆盖需求点名列出。每个 facet 之后会变成报告的一个小节，因此 trace 能揭示哪个角度没有证据。

规划也是本项目中模型第一次登场的地方，这带来你在每个真实 agent 里都会遇到的两个工程问题：

1. **测试绝不能调用线上模型。** 那样会很慢、花钱，而且每次运行给出不同答案。
2. **模型输出是不可信输入。** 回复可能话痨、被截断或不是合法 JSON。管道必须照常运转。

> "Why are containers a weak sandbox for agent code?" is really four questions: what a container is, how it works, where it fails, and when to use something else. A plan names these separate coverage requirements before retrieval begins. Each facet later becomes a report section, so the trace can reveal which angle had no evidence.
> Planning is also the first place a model enters this project, which raises two engineering problems you meet in every real agent:
> 1. **Tests must not call a live model.** They would be slow, cost money and give different answers each run.
> 2. **Model output is untrusted input.** A reply can be chatty, truncated or invalid JSON. The pipeline must keep working.

## Rule planner first · 先做规则规划器

默认的规划器使用四个模板：

| 标签 | 子问题 | 额外关键词 |
|---|---|---|
| Overview | What is {subject}? | none |
| How it works | How does {subject} work? | works, uses, runs |
| Risks and limits | What are the risks and limits of {subject}? | risk, attack, escape, weakness, cost |
| When to use it | When should teams use {subject}? | use, teams, tradeoff, overhead |

主语（subject）是去掉开头疑问词之后的问题。关键词是问题的词元加上额外关键词。它简单、确定，并且给了你一个可供超越的基线。

> The default planner uses four templates:
> The subject is the question with its leading question words removed. Keywords are the question tokens plus the extras. It is simple, deterministic, and it gives you a baseline to beat.

## Record and replay · 录制与回放

cassette 是一个保存已录制调用的 JSON 文件：

```json
{"entries": [{"purpose": "plan", "prompt": "You plan research...", "response": "{\"facets\": [...]}"}]}
```

`ReplayModel` 查找 `prompt_key(purpose, prompt)`，即对完整 prompt 取 sha256。prompt 哪怕只变一个字符，查找就会 miss 并抛出 `CassetteMiss`。这种严格正是关键所在：prompt 变了就是实验变了，你应该有意地重新录制。

> A cassette is a JSON file of recorded calls:
> `ReplayModel` looks up `prompt_key(purpose, prompt)`, a sha256 of the exact prompt. If the prompt changes by one character, the lookup misses and raises `CassetteMiss`. That strictness is the point: a changed prompt is a changed experiment, and you should record it again on purpose.

## Fallback on bad output · 坏输出时回退

```python
try:
    raw = model.complete(build_planner_prompt(question), purpose="plan")
    return Plan(question, parse_model_facets(raw, max_facets), source="model")
except (KeyError, ValueError, TypeError, AttributeError) as error:
    return Plan(question, rule_plan(question), source="rules-fallback", notes=[...])
```

`plan.source` 记录走的是哪条路径。第 6 阶段的 trace 会展示它，这样你就能统计模型规划被拒绝的频率。

```figure
pj-rra-plan-facets
```

> `plan.source` records which path ran. The trace in stage 6 will show it, so you can count how often the model plan was rejected.

## Follow the mechanism · 理解机制

回放键包含 purpose 和完整 prompt 的哈希。把 purpose 单独放进去，可以防止同一个 prompt 意外匹配到另一个操作。回退还必须记录它为什么发生；否则一次绿灯运行可能在悄无声息中不再真正锻炼模型规划。

> The replay key includes purpose and the exact prompt hash. Keeping purpose separate prevents the same prompt from accidentally matching a different operation. A fallback must also record why it happened; otherwise a green run can silently stop exercising model planning.

## Your task · 你的任务

```python
# model.py
class ReplayModel:
    def __init__(self, cassette_path): ...
    def complete(self, prompt, *, purpose) -> str: ...

# planner.py
class Facet:
    def query(self) -> str: ...
def subject_of(question) -> str: ...
def rule_plan(question, max_facets=4) -> list[Facet]: ...
def parse_model_facets(raw, max_facets) -> list[Facet]: ...
def plan_research(question, model=None, max_facets=4) -> Plan: ...
```

`build_planner_prompt` 已经写好了。不要改它，否则录制好的 cassette 就不再匹配。

> `build_planner_prompt` is already written. Do not change it, or the recorded cassette stops matching.

## Run the tests · 运行测试

```bash
python3 scripts/project_test.py research-report-agent --stage 3 --path my-report-agent
```

`fixtures/cassettes/planner.json` 里的 cassette 保存着一份录制好的、合格的规划，以及一条不是 JSON 的话痨回复。你的规划器必须使用前者，并在后者上回退。

> The cassette in `fixtures/cassettes/planner.json` holds one good recorded plan and one chatty reply that is not JSON. Your planner must use the first and fall back on the second.

## What you should see · 预期结果

第 3 阶段通过 9 个 Python 测试，且此前所有阶段仍然通过。录制的 denylist 问题返回 `source="model"`，带 3 个 facet。话痨回复和缺失的 cassette 都产生 `source="rules-fallback"`，并带一条解释性备注。

> Stage 3 passes 9 Python tests, and all preceding stages still pass. The recorded denylist question returns `source="model"` with 3 facets. A chatty reply and a missing cassette both produce `source="rules-fallback"` with an explanatory note.

## Check yourself · 自检

1. 为什么用完整 prompt 的哈希而不是问题本身作为 cassette 的键？
2. 当模型返回合法 JSON 但 `facets` 列表为空时，应该发生什么？
3. 在生产环境里，你会把 `plan.notes` 记录到哪里？

> 1. Why key the cassette by a hash of the full prompt instead of by the question?
> 2. What should happen when the model returns valid JSON with an empty `facets` list?
> 3. Where would you log `plan.notes` in production?

## Going further · 进阶

- 设置 `RRA_LLM_BASE_URL`、`RRA_LLM_MODEL` 和 `RRA_LLM_API_KEY`，把 `LiveModel()` 传给 `plan_research`，并把它的 facet 与规则规划器做比较。
- 写一个 `RecordingModel`，包住 `LiveModel` 并把每次调用追加进 cassette，这样一次线上运行就变成一个测试 fixture。

> - Set `RRA_LLM_BASE_URL`, `RRA_LLM_MODEL` and `RRA_LLM_API_KEY`, pass `LiveModel()` to `plan_research`, and compare its facets with the rule planner.
> - Write a `RecordingModel` that wraps `LiveModel` and appends every call to a cassette, so a live run becomes a test fixture.

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html)和[检索增强生成](../../../../../phases/11-llm-engineering/06-rag/docs/en.md)。先完成[阶段 2](../../02-extract-snippets/docs/en.md)。

在规则、录制好的 cassette 和线上规划器之间做出明确选择。只有规划调用可选的模型；写作仍然只是排列检索到的来源句子。trace 记录规划用的是规则、模型输出还是回退。

```text
--model rules -> deterministic facets
--model replay --cassette planner.json -> exact prompt lookup
invalid facet JSON -> rules-fallback
```

> Choose rules, a recorded cassette, or a live planner explicitly. Only planning calls the optional model; writing still arranges retrieved source sentences. The trace records whether planning used rules, model output or fallback.

## Build and inspect · 构建并检查

在 cassette 查找时，把 prompt 摘要和 purpose 放在一起。在构造 facet 之前先校验响应的形状。

在你的学习工作区（learner workspace）中实现该阶段。这些 CLI 辅助工具是给定的适配器，它们导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py research-report-agent --stage 3 --path learning-artifacts/research-report-agent
```

先预测上面的中间状态，再运行该阶段。全新的 stub 会失败；参考实现跑通并不代表你的学习工作区已经完成。

> Keep the prompt digest and purpose together in cassette lookup. Validate the response shape before constructing facets.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 下一步探究

为什么线上模型的失败不应被误标为一次已验证的离线运行？

> Why should a live model failure not be mislabeled as a verified offline run?
