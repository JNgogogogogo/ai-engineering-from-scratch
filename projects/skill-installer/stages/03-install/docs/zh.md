# Install atomically within a root · 在一个根目录内原子化安装

**第 3 阶段（共 4 阶段）。** TypeScript。预计约 2 小时。

创建目录之前先核对期望摘要。用 lstat 逐一检查 agent 目录并拒绝符号链接（symlink）。先把完整的翻译后技能包暂存（stage）到目标位置旁边，再重命名（rename）就位。已存在的受管安装会先移入临时备份，这样最后一步重命名失败时还能还原。这个教学版事务假设只有一个可信的本地写入者；要对抗恶意的并发文件系统替换，需要操作系统级的隔离。

本阶段的实现边界是 `install`。保持此前各阶段的行为不变：最终评分器（grader）会用同一个工作区运行所有阶段。

```figure
pj-skill-installer-3
```

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [TypeScript object types](https://www.typescriptlang.org/docs/handbook/2/objects.html) 和 [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)，并先完成[第 2 阶段](../../02-translate/docs/en.md)。

安装进一个由调用方提供、可随时丢弃的根目录。安装器把每个文件写进一个私有的同级目录，只有等技能包完整之后，才把它重命名进 agent 的发现路径（discovery path）。

```text
root/.agents/skills/orchard-release/
SKILL.md + references/checklist.md + .installed.json
```

> Before coding, review [TypeScript object types](https://www.typescriptlang.org/docs/handbook/2/objects.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md). Complete [stage 2](../../02-translate/docs/en.md) first.
> Install into a caller-owned disposable root. The installer writes every file to a private sibling directory and renames it into the agent discovery path only after the bundle is complete.

## Build and inspect · 构建与检查

暂存之前，先检查各级父目录有没有符号链接。把 agent 目录映射与可移植的技能内容分开保管。

请在你的学习者工作区（learner workspace）里实现本阶段。CLI 辅助工具只是随附的适配器（adapter），它们导入你的函数；不能替代参考解答。

```bash
python3 scripts/project_test.py skill-installer --stage 3 --path learning-artifacts/skill-installer
```

先预测上面的中间状态，再运行本阶段。全新的桩代码（stub）会失败；参考解答能跑通，并不代表你的学习者工作区已经完成。

> Check parent directories for symlinks before staging. Keep the agent directory mapping separate from portable skill content.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

如果写入在重命名之前失败，读者应该观察到什么？

> What should a reader observe if a write fails before the rename?
