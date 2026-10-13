# Validate a portable bundle · 校验可移植技能包

**第 1 阶段（共 4 阶段）。** TypeScript。预计约 2 小时。

接受一个有名字、含 SKILL.md 和可选参考文件（reference file）的技能包（bundle）。在触碰磁盘之前校验每一条相对路径。拒绝点段（dot segment）、绝对路径、盘符前缀、反斜杠和保留的安装元数据。每个文本文件限制在 100 KB 以内。安装器读取的是内存中的技能包，网络抓取与签名信任是另外的独立职责。

本阶段的实现边界是 `safePath, validate`。保持此前各阶段的行为不变：最终评分器（grader）会用同一个工作区运行所有阶段。

```figure
pj-skill-installer-1
```

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [TypeScript object types](https://www.typescriptlang.org/docs/handbook/2/objects.html) 和 [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。

可移植技能包携带元数据和相对路径的 UTF-8 文件。把 SKILL.md 当作入口文档，拒绝任何可能逃出所选安装根目录（install root）的资源名。原始的 Orchard 技能包里带有一份恢复清单（restore checklist）。

```text
name=orchard-release
files: SKILL.md, references/checklist.md
../settings.json -> rejected
```

> Before coding, review [TypeScript object types](https://www.typescriptlang.org/docs/handbook/2/objects.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md).
> A portable bundle carries metadata and relative UTF-8 files. Treat SKILL.md as an entry document and reject any resource name that could escape the selected install root. The original Orchard bundle includes a restore checklist.

## Build and inspect · 构建与检查

在创建目录之前校验每一个文件路径。把 .installed.json 保留给安装回执（installer receipt）。

请在你的学习者工作区（learner workspace）里实现本阶段。CLI 辅助工具只是随附的适配器（adapter），它们导入你的函数；不能替代参考解答。

```bash
python3 scripts/project_test.py skill-installer --init learning-artifacts/skill-installer
python3 scripts/project_test.py skill-installer --stage 1 --path learning-artifacts/skill-installer
```

先预测上面的中间状态，再运行本阶段。全新的桩代码（stub）会失败；参考解答能跑通，并不代表你的学习者工作区已经完成。

> Validate every file path before creating directories. Reserve .installed.json for the installer receipt.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

即便当前机器用的是斜杠路径，为什么也必须拒绝 Windows 反斜杠？

> Why must a Windows backslash be rejected even when the current machine uses slash paths?
