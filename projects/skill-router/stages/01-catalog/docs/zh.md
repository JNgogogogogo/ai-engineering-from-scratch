# Parse a typed skill catalog · 解析带类型的技能目录

**Stage 1 of 4 · 第 1 阶段（共 4 阶段）。** TypeScript。计划约 2 小时。

技能清单（skill manifest）声明 id、描述（description）、关键词（keywords）、路径模式（path patterns）、优先级（priority）、依赖（dependencies）和权限（permissions）。数组和数字必须在运行时校验，而不是信任 JSON 的类型转换。分词（tokenization）会规范化标点与大小写并去掉重复的词，因此重复输入同一个提示无法把它的得分刷高。

> A skill manifest declares an id, description, keywords, path patterns, priority, dependencies and permissions. Validate arrays and numbers at runtime rather than trusting a JSON cast. Tokenization normalizes punctuation and case and removes repeated words, so repeating a prompt cannot inflate its score.

本阶段的实现边界是 `parseSkill, tokens`。保持此前阶段的行为不变：最终评分器（grader）会在同一个工作区上运行每一个阶段。

> The boundary for this stage is `parseSkill, tokens`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

```figure
pj-skill-router-1
```

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [TypeScript object types](https://www.typescriptlang.org/docs/handbook/2/objects.html) 和 [Tool schema design](../../../../../phases/13-tools-and-protocols/05-tool-schema-design/docs/en.md)。

> Before coding, review [TypeScript object types](https://www.typescriptlang.org/docs/handbook/2/objects.html) and [Tool schema design](../../../../../phases/13-tools-and-protocols/05-tool-schema-design/docs/en.md).

通过 SKILL.md 里的 name 和 description 发现一个技能，然后把 routing.json 作为本地路由扩展来读取。目录名必须与技能名一致。路由元数据不是可移植（portable）技能格式的一部分。

> Discover a skill from its SKILL.md name and description, then read routing.json as a local routing extension. The directory name must match the skill name. Routing metadata is not part of the portable skill format.

```text
skills/release-review/SKILL.md -> name release-review
routing.json -> keywords,paths,priority,requires,permissions
```

## Build and inspect · 构建与检视

用 parseSkill 校验合并后的记录。在解析发现到的文件之前，先拒绝符号链接（symlink）文件和超大文件。

> Validate the merged record with parseSkill. Refuse symlinked or oversized discovery files before parsing them.

请在你的学习者工作区（learner workspace）中实现本阶段。CLI 辅助工具是预先提供的适配器，它们导入你的函数；它们不能替代参考实现。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py skill-router --init learning-artifacts/skill-router
python3 scripts/project_test.py skill-router --stage 1 --path learning-artifacts/skill-router
```

先预测上面的中间状态，再运行本阶段。全新的存根（stub）会失败；一次通过的参考运行并不能证明你的学习者工作区已经完成。

> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接下来探究

当目录 release-review 声明的 name 是 publish 时，应该发生什么？

> What should happen when directory release-review declares name publish?
