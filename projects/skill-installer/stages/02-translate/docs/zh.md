# Translate metadata and hash content · 翻译元数据并对内容做哈希

**第 2 阶段（共 4 阶段）。** TypeScript。预计约 2 小时。

只重新生成一小段带引号的元数据头（metadata header），正文指令保持不变。参考文件（reference）逐字节原样保留（byte-for-byte）。对排序后的 path/content 对计算 SHA-256 摘要（digest），文件的插入顺序因此无法改变完整性。摘要能检测内容是否被改过，但不能证明发布者身份；获取一份可信的期望摘要，是调用方的责任。

本阶段的实现边界是 `digest, translate`。保持此前各阶段的行为不变：最终评分器（grader）会用同一个工作区运行所有阶段。

```figure
pj-skill-installer-2
```

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [TypeScript object types](https://www.typescriptlang.org/docs/handbook/2/objects.html) 和 [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)，并先完成[第 1 阶段](../../01-bundle/docs/en.md)。

把 name 和 description 序列化为与 JSON 兼容的双引号 YAML 标量（scalar）。Rust 校验器接受同一个子集，包括转义序列。源技能包摘要和翻译后摘要不同，因为翻译改写了元数据。

```text
source bundle digest -> expected source identity
translated SKILL.md: name: "orchard-release"
translated digest -> installed content identity
```

> Before coding, review [TypeScript object types](https://www.typescriptlang.org/docs/handbook/2/objects.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md). Complete [stage 1](../../01-bundle/docs/en.md) first.
> Serialize name and description as JSON-compatible double-quoted YAML scalars. The Rust validator accepts that same subset, including escapes. Source and translated digests differ because translation rewrites metadata.

## Build and inspect · 构建与检查

哈希之前先对文件条目排序。摘要用来对照可信的期望值核验内容；用不可信的字节算出的摘要证明不了发布者身份。

请在你的学习者工作区（learner workspace）里实现本阶段。CLI 辅助工具只是随附的适配器（adapter），它们导入你的函数；不能替代参考解答。

```bash
python3 scripts/project_test.py skill-installer --stage 2 --path learning-artifacts/skill-installer
```

先预测上面的中间状态，再运行本阶段。全新的桩代码（stub）会失败；参考解答能跑通，并不代表你的学习者工作区已经完成。

> Sort file entries before hashing. A digest verifies content against a trusted expectation; computing it from untrusted bytes does not establish publisher identity.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

含引号的 description 要如何在安装器与校验器之间完整往返（round trip）？

> How should a description containing a quote survive installer-to-validator round trip?
