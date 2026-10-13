# Drive the actual Strands loop with a local model · 用本地模型驱动真实的 Strands 循环

Stage 4 of 4 · 第 4 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

## What changes · 变化在哪

真实的 Strands Agent 从一个注入的 Model 子类消费流式事件。这样可以在没有凭证、没有云调用的情况下驱动框架循环。模型仍然只提出一个计划；用前面写好的 validator 对它的结果做解析和 scope 检查。单独的 Bedrock 构造是显式给出的，离线 demo 和测试都不会调用它。

> The real Strands Agent consumes streaming events from an injected Model subclass. This exercises the framework loop without credentials or cloud calls. The model still only proposes a plan; parse and scope-check its result with the earlier validator. A separate Bedrock constructor is explicit and is not invoked by offline demos or tests.

## Work through one concrete case · 走通一个具体案例

可选的 Strands Agent 通过它真实的流式 Model 接口发出一份 JSON 计划。这份提案随后会经过 cli.py 所使用的同一套 scope validator、retry 包装器和有界 executor。

> The optional Strands Agent emits a JSON plan through its real streaming Model interface. That proposed plan then passes through the same scope validator, retry wrapper and bounded executor used by cli.py.

```figure
pj-cloud-agent-with-aws-strands-4
```

先修改实验输入、自己算出结果，再去读它的指标。图中的数值由这些输入计算得出；下方的实现测试仍然是完成与否的判定依据。

> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

实现 `strands_adapter.py` 中的 `parse_model_plan`、`run_strands`、`bedrock_agent`。这个工件是 Cloud Agent With AWS Strands 的第 4 阶段产物：它消费显式输入，返回一个可供下一阶段使用的、可检查的结果。

> Implement `strands_adapter.py`: `parse_model_plan`, `run_strands`, `bedrock_agent`. This artifact is stage 4 of Cloud Agent With AWS Strands. It consumes explicit inputs and returns an inspectable result that the next stage can use.

使用[公开 API 契约](../../../API.md)和带类型标注的起始签名。核心函数只返回值；文件输入、参数解析和展示一律交给配套的 driver。

> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.

让三种模式保持显式：纯离线 core、安装 SDK 后的本地模型对比、以及可选加入（opt-in）的 AWS 读取。装好的 SDK 通过 fake-model 测试是有用的集成证据，但它说明不了 IAM 或 Bedrock 的可用性。

> Keep three modes explicit: pure offline core, installed-SDK local-model comparison, and opt-in AWS reads. An installed SDK passing a fake-model test is useful integration evidence but says nothing about IAM or Bedrock availability.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py cloud-agent-with-aws-strands --init learning-artifacts/cloud-agent-with-aws-strands` 初始化一次，然后按阶段累加评分：

> From the repository root, initialize once with `python3 scripts/project_test.py cloud-agent-with-aws-strands --init learning-artifacts/cloud-agent-with-aws-strands`. Then grade cumulatively:

```bash
python3 scripts/project_test.py cloud-agent-with-aws-strands --stage 4 --path learning-artifacts/cloud-agent-with-aws-strands --strict
```

全新的工作区在你实现契约之前应当是失败的。所有阶段完成后，用提供的样例运行你自己的工件：

> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

```bash
cd learning-artifacts/cloud-agent-with-aws-strands
python3 cli.py samples/input.json --output incident.json
```

## Investigate the failure boundary · 探查失败边界

用 cli.py 跑样例，检查重复的 metrics 读取上 cached=true。然后用固定版本的 SDK 运行 --optional --strict，在不发送云端请求的前提下驱动框架事件。

> Run the sample through cli.py and inspect cached=true on the repeated metrics read. Then run --optional --strict with the pinned SDK to exercise framework events without sending cloud requests.

默认模式读取提供的录制数据。--mode aws 是一个可选加入的 AWS CLI 适配器，面向 ECS 服务、CloudWatch CPU 和有边界的日志读取；它需要调用方自行提供配置、凭证和 AWS 权限。这里不包含任何部署或线上验证的承诺。

> Default mode reads the supplied recording. --mode aws is an opt-in AWS CLI adapter for ECS services, CloudWatch CPU and bounded log reads; it requires caller configuration, credentials and AWS permissions. No deployment or live verification is implied.

## Verify the actual framework · 验证真实框架

五个默认的阶段测试在不导入 SDK 的情况下检查 adapter 契约。安装固定版本的可选依赖，然后显式地加上五个真实 SDK 测试：

> The five default stage tests check the adapter contract without importing the SDK. Install the pinned optional dependency, then include the five real-SDK tests explicitly:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r projects/cloud-agent-with-aws-strands/requirements-framework.txt
.venv/bin/python scripts/project_test.py cloud-agent-with-aws-strands --solution --optional --strict
.venv/bin/python projects/cloud-agent-with-aws-strands/solution/framework_demo.py
```

用 `--path my-cloud-agent-with-aws-strands` 代替 `--solution` 来给你的实现评分。缺少依赖时，optional 模式下记为 skip，strict optional 模式下记为失败。已验证的 SDK 版本是 `strands-agents==1.57.1`；所有模型回复都是本地 fixture。

> Use `--path my-cloud-agent-with-aws-strands` instead of `--solution` to grade your implementation. Missing dependencies produce a skip in optional mode and a failure in strict optional mode. The verified SDK version is `strands-agents==1.57.1`; all model replies are local fixtures.

## References · 参考资料

[Reference 1](https://strandsagents.com/docs/user-guide/concepts/model-providers/custom_model_provider/)
