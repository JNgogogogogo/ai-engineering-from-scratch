# Protect edits during upgrades · 升级时保护本地修改

**第 4 阶段（共 4 阶段）。** TypeScript。预计约 2 小时。

替换安装之前，核实每个被跟踪（tracked）文件仍与先前的摘要一致，也没有冒出不受管（unmanaged）的文件。当用户改动了被跟踪文件、或添加了自己的文件时，拒绝升级。用户可以有意把这些改动移进源技能包。成功的重复安装不会留下任何暂存（staging）或备份目录。

本阶段的实现边界是 `install`。保持此前各阶段的行为不变：最终评分器（grader）会用同一个工作区运行所有阶段。

```figure
pj-skill-installer-4
```

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [TypeScript object types](https://www.typescriptlang.org/docs/handbook/2/objects.html) 和 [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)，并先完成[第 3 阶段](../../03-install/docs/en.md)。

升级必须保留本地修改。把当前文件与上一次安装的摘要做比较，拒绝被修改或不受管的文件。演示会编辑清单（checklist）、重试安装，并保住这笔修改。

```text
installed checklist hash=A
local edit -> current hash=B
upgrade -> modified installation; local text remains
```

> Before coding, review [TypeScript object types](https://www.typescriptlang.org/docs/handbook/2/objects.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md). Complete [stage 3](../../03-install/docs/en.md) first.
> An upgrade must preserve local edits. Compare the current files with the previous installed digest and reject modified or unmanaged files. The demo edits the checklist, retries installation, and retains the edit.

## Build and inspect · 构建与检查

移动目标目录之前，先读取现有回执（receipt）并核验它的文件列表。如果最后一步重命名失败，就把已移走的备份还原回来。

请在你的学习者工作区（learner workspace）里实现本阶段。CLI 辅助工具只是随附的适配器（adapter），它们导入你的函数；不能替代参考解答。

```bash
python3 scripts/project_test.py skill-installer --stage 4 --path learning-artifacts/skill-installer
```

所有累计阶段都通过后，从仓库根目录用原始示例输入运行你的产物（artifact）：

```bash
node learning-artifacts/skill-installer/cli.ts inspect projects/skill-installer/examples/orchard-release.json codex
```

inspect 是一次演练（dry run）。install 需要 bundle、agent、root 和一份可信的期望源摘要。支持的目标目录映射是 codex=.agents/skills、claude=.claude/skills 和 cursor=.cursor/skills。发现路径在本地配置；安装成功并不证明另一个独立运行的 agent 激活了该技能。

> Read the existing receipt and verify its file list before moving the destination. Restore a moved backup if the final rename fails.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> After the cumulative stages pass, run your artifact on the original sample input from the repository root:
> inspect is a dry run. install needs bundle, agent, root and trusted expected source digest. Supported destination mappings are codex=.agents/skills, claude=.claude/skills and cursor=.cursor/skills. Discovery paths are configured locally; successful installation does not prove a separately running agent activated the skill.

## Investigate next · 接着探究

在替换一份被本地编辑过的清单之前，一次可评审的合并（reviewable merge）需要拿出什么证据？

> What would a reviewable merge need to show before replacing a locally edited checklist?
