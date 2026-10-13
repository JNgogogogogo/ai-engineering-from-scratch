# Define modeled control profiles · 定义建模的控制配置档

**第 2 阶段（共 4 阶段）。** Rust。预留约 2 小时。

把进程、文件系统、容器网络和 microVM 这些边界建模为数据。配置档（profile）这个名字本身证明不了任何东西；要把每一项必需的控制（control）和它的布尔能力逐一匹配。这些配置档刻意假定运维者配置正确，并把部署验证留给真实的运行时。

```figure
pj-sandbox-ladder-2
```

> Model process, filesystem, container-network and microVM boundaries as data. A profile name alone proves nothing; match each required control against its boolean capability.
> The profiles deliberately assume correct operator configuration and leave deployment verification to a real runtime.

## Implementation boundary · 实现边界

```rust
pub fn profiles()->Vec<Profile>
pub fn satisfies(n:&Needs,p:&Profile)->bool
```

主要参考：[官方参考](https://docs.docker.com/engine/security/)。

> Primary reference: [Official reference](https://docs.docker.com/engine/security/).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Rust 所有权与 Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 和 [面向 AI 的 Docker](../../../../../phases/00-setup-and-tooling/07-docker-for-ai/docs/en.md)。先完成 [阶段 1](../../01-parse-the-capability-request/docs/en.md)。

配置档是带示例性成本的建模能力（capability）。在这个模型里，进程边界没有任何文件系统或网络隔离；容器配置档两者都建模，但与宿主共享内核。

```text
process: filesystem=false, network=false, kernel=false
container: filesystem=true, network=true, kernel=false
```

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Docker for AI](../../../../../phases/00-setup-and-tooling/07-docker-for-ai/docs/en.md). Complete [stage 1](../../01-parse-the-capability-request/docs/en.md) first.
> Profiles are modeled capabilities with illustrative costs. A process boundary has no filesystem or network isolation in this model; the container profile models both but shares its host kernel.

## Build and inspect · 构建并检查

逐项独立地测试需求。只要缺少一项必需的能力，低成本就无关紧要。

在你的学习者工作区（learner workspace）中实现本阶段。CLI 辅助脚本是随仓库提供的适配器（adapter），它们导入你的函数；它们不能替代参考解法。

```bash
python3 scripts/project_test.py sandbox-ladder --stage 2 --path learning-artifacts/sandbox-ladder
```

先预测上方的中间状态，再运行本阶段。全新的桩（stub）会失败；参考实现跑通并不能证明你的学习者工作区已完成。

> Test requirements independently. A low cost is irrelevant when one required capability is absent.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 下一步探究

为什么这个模型不能作为「运行中的容器具备这些设置」的证据？

> Why is the model not evidence that a running container has these settings?
