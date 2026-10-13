# Report residual assumptions · 报告残余假设

**第 4 阶段（共 4 阶段）。** Rust。预留约 2 小时。

返回选中的夹具（fixture），并清楚地声明尚未执行操作系统层面的强制（enforcement）。根据选中的控制列出「共享内核」「网络未禁用」这些残余项（residual），并拒绝不满足原始需求的配置档。这份报告是部署评审（deployment review）的一项输入。

```figure
pj-sandbox-ladder-4
```

> Return the selected fixture and state clearly that operating-system enforcement has not been performed.
> List shared-kernel and enabled-network residuals from the selected controls, and reject a profile that fails the original requirements.
> The report is an input to deployment review.

## Implementation boundary · 实现边界

```rust
pub fn plan(n:&Needs,p:&Profile)->Result<String,Error>
```

主要参考：[官方参考](https://docs.docker.com/engine/security/)。

> Primary reference: [Official reference](https://docs.docker.com/engine/security/).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Rust 所有权与 Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 和 [面向 AI 的 Docker](../../../../../phases/00-setup-and-tooling/07-docker-for-ai/docs/en.md)。先完成 [阶段 3](../../03-select-the-least-costly-sufficient-profile/docs/en.md)。

可选的 Docker 适配器会生成一份可检查的参数列表，并且只运行调用方指定的、本地已有的镜像。它的无害探测（probe）会测试「被拒绝的 root 写入」和「默认路由不存在」这两件事。这里不包含任何 microVM 实现。

```text
--docker-image alpine:local -> command preview
--execute -> docker_probe with observed stdout
shared host kernel remains a residual
```

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Docker for AI](../../../../../phases/00-setup-and-tooling/07-docker-for-ai/docs/en.md). Complete [stage 3](../../03-select-the-least-costly-sufficient-profile/docs/en.md) first.
> The optional Docker adapter produces an inspectable argument list and only runs a caller-selected image already present locally. Its harmless probes test a denied root write and absence of a default route. No microVM implementation is included.

## Build and inspect · 构建并检查

把 policy_simulation 和 docker_probe 的结果分开保存。一次成功的探测只是这些检查项的证据，不能证明能防住容器逃逸（container escape）。

在你的学习者工作区（learner workspace）中实现本阶段。CLI 辅助脚本是随仓库提供的适配器（adapter），它们导入你的函数；它们不能替代参考解法。

```bash
python3 scripts/project_test.py sandbox-ladder --stage 4 --path learning-artifacts/sandbox-ladder
```

在前面各阶段累计通过之后，从仓库根目录用最初的样例输入运行你的产物：

```bash
python3 learning-artifacts/sandbox-ladder/cli.py untrusted=true,secrets=true,network=true,host_kernel=false --budget 3
```

默认输出是一次策略模拟（policy simulation）。`--docker-image` 预览一次调用；`--execute` 需要本地已有的镜像和 Docker。只测试 root 写入和默认路由两项探测。适配器绝不实现、也不验证 microVM 边界。

> Keep policy_simulation and docker_probe results distinct. A successful probe is evidence for those checks only, not proof against container escape.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> After the cumulative stages pass, run your artifact on the original sample input from the repository root:
> Default output is a policy simulation. --docker-image previews an invocation; --execute requires an already available local image and Docker. Only root-write and default-route probes are tested. The adapter never implements or verifies a microVM boundary.

## Investigate next · 下一步探究

如果 root_write 变成允许的，你会最先检查哪个运行时设置？

> If root_write becomes allowed, which runtime setting would you inspect first?
