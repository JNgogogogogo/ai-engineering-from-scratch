# Retry transient reads and reuse completed requests · 重试瞬时读取失败并复用已完成的请求

Stage 3 of 4 · 第 3 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

## What changes · 变化在哪

只重试瞬时的 timeout 失败，并按规范化的 action 身份缓存成功的读取。权限失败不是瞬时错误，必须立即向上抛出。这个缓存是请求局部的：真实的云端状态会变化，长期存活的缓存需要显式的 TTL 或版本号，而不是默默复用旧数据。

> Retry only transient timeout failures and cache successful reads by a canonical action identity. A permission failure is not transient and must escape immediately. This cache is request-local: real cloud state changes, so a long-lived cache needs an explicit TTL or version instead of silently reusing old data.

## Work through one concrete case · 走通一个具体案例

计划读取 checkout metrics 两次。第一次调用超时一次后成功；第二个逻辑读取复用了缓存值。Provider 调用数=2，完成的逻辑读取=2，缓存命中=1。

> The plan reads checkout metrics twice. The first call times out once and then succeeds; the second logical read reuses the cached value. Provider calls=2, completed logical reads=2, cache hits=1.

```figure
pj-cloud-agent-with-aws-strands-3
```

先修改实验输入、自己算出结果，再去读它的指标。图中的数值由这些输入计算得出；下方的实现测试仍然是完成与否的判定依据。

> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

实现 `retry.py` 中的 `request_key` 和 `cached_read`。这个工件是 Cloud Agent With AWS Strands 的第 3 阶段产物：它消费显式输入，返回一个可供下一阶段使用的、可检查的结果。

> Implement `retry.py`: `request_key`, `cached_read`. This artifact is stage 3 of Cloud Agent With AWS Strands. It consumes explicit inputs and returns an inspectable result that the next stage can use.

使用[公开 API 契约](../../../API.md)和带类型标注的起始签名。核心函数只返回值；文件输入、参数解析和展示一律交给配套的 driver。

> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.

只把成功的结果缓存到 operation 与 resource 的规范化二元组之下。权限错误绕过 timeout 重试循环；反复重试它们也无法因此获得授权。

> Cache only successful results under a canonical pair of operation and resource. Permission errors bypass the timeout retry loop; repeating them cannot grant authority.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py cloud-agent-with-aws-strands --init learning-artifacts/cloud-agent-with-aws-strands` 初始化一次，然后按阶段累加评分：

> From the repository root, initialize once with `python3 scripts/project_test.py cloud-agent-with-aws-strands --init learning-artifacts/cloud-agent-with-aws-strands`. Then grade cumulatively:

```bash
python3 scripts/project_test.py cloud-agent-with-aws-strands --stage 3 --path learning-artifacts/cloud-agent-with-aws-strands --strict
```

全新的工作区在你实现契约之前应当是失败的。所有阶段完成后，用提供的样例运行你自己的工件：

> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

```bash
cd learning-artifacts/cloud-agent-with-aws-strands
python3 cli.py samples/input.json --output incident.json
```

## Investigate the failure boundary · 探查失败边界

把第二个资源换成范围内另一个服务。即使操作完全相同，也必须产生一个不同的缓存键。

> Change the second resource to another scoped service. It must produce a different cache key even though the operation is identical.

## References · 参考资料

[Reference 1](https://strandsagents.com/docs/user-guide/concepts/model-providers/custom_model_provider/)
