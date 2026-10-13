# Measure activity without claiming speech detection · 只测活动，不宣称语音检测

> At 1000 Hz, forty samples of amplitude 0.5, twenty silent samples and forty active samples merge into [0,100] when gap_ms is 40. The merged span lasts 100 ms. A 20 ms isolated burst is discarded when min_ms is 40.

**Type:** Build
**Stage:** 2 of 4
**Time:** About 2 hours

## The useful boundary · 有用的边界

对每一帧计算均方根（RMS）能量。把高于阈值的帧标记为活动，把被足够短的间隙分隔的相邻活动段合并起来，然后丢弃短于最小时长的段。返回半开区间（half-open interval）的样本区间，让切片和时间戳共用同一坐标系。

```figure
pj-voice-note-transcriber-pipeline-2
```

> Compute root-mean-square energy for each frame. Mark frames above the threshold, merge neighboring active spans separated by a short enough gap, and discard spans shorter than the minimum. Return half-open sample intervals so slicing and timestamps share one coordinate system.

## Work the example · 先把例子算明白

在 1000 Hz 下，40 个幅度 0.5 的样本、20 个静音样本和 40 个活动样本，在 gap_ms 为 40 时合并成 [0,100]。合并后的区间持续 100 ms。一个 20 ms 的孤立爆发在 min_ms 为 40 时会被丢弃。

写代码之前，先写下要返回的字段和预期的副作用次数。再保留一个应当失败的输入，防止成功的例子被硬编码成答案。

> At 1000 Hz, forty samples of amplitude 0.5, twenty silent samples and forty active samples merge into [0,100] when gap_ms is 40. The merged span lasts 100 ms. A 20 ms isolated burst is discarded when min_ms is 40.
> Write the returned fields and the expected side-effect count before coding. Keep a second input that should fail so the successful example cannot become a hard-coded answer.

## Build the contract · 构建契约

在你的学习工作区（learner workspace）里实现 `activity(samples, rate, frame_ms=20, threshold=0.02, min_ms=40, gap_ms=40) in activity.py`。保持导出名称不变，并继续复用此前阶段，而不是复制它们的策略。

拒绝非有限（nonfinite）的样本或参数，以及无效的负边界。声学能量识别不了词、语言或说话人：风扇可以通过，轻声说话可能不通过。CLI 默认把整段音频一次性发送；`--segment` 是显式选择这种有损的、基于能量的切分。

> Implement `activity(samples, rate, frame_ms=20, threshold=0.02, min_ms=40, gap_ms=40) in activity.py` in your learner workspace. Preserve the exported names and continue using earlier stages rather than duplicating their policies.
> Reject nonfinite samples or parameters and invalid negative bounds. Acoustic energy does not identify words, language or speakers: a fan can pass and quiet speech can fail. The CLI sends the whole clip by default; --segment explicitly opts into this lossy energy-based split.

## Hints · 提示

在合并之前先把活动帧的索引画出来。把「间隙条件」和「最小时长过滤」分开处理。取一个刚好在某帧 RMS 之上、再取一个刚好在其之下的阈值，解释输出发生了什么变化。

> Draw the active frame indices before merging. Separate the gap condition from the minimum-duration filter. Try a threshold just above and just below a frame's RMS and explain the changed output.

## Verify your work · 验证你的实现

```bash
python3 scripts/project_test.py voice-note-transcriber-pipeline --init my-voice-note-transcriber-pipeline
python3 scripts/project_test.py voice-note-transcriber-pipeline --stage 2 --path my-voice-note-transcriber-pipeline --strict
```

初始化只需一次。累积测试会导入你的工作区并保留你此前的源码。跑参考解法（reference solution）只是验证教学实现，永远不会颁发学习者证书。可选的 SDK 检查需要项目 README 里列出的依赖和命令。

> Initialize once. Cumulative tests import your workspace and preserve your earlier source. A reference-solution run verifies the teaching implementation and never grants a learner certificate. Optional SDK checks require the dependencies and commands in the project README.

## Inspect the result · 检查结果

移除安静区域会丢失哪些信息？在你自己的录音条件下，你会怎么评估这个检测器？

完整的项目会产出 audio.wav、captions.vtt、transcript.json，以及一个带内嵌播放和 cue 跳转按钮的 HTML 页面。

```bash
cd projects/voice-note-transcriber-pipeline/solution
python3 pipeline.py --input fixtures/repair-note.wav --transcript-file fixtures/reference.json --out voice-output
```

把夹具换成你自己工作流里的一段小输入。把预期结果和观察到的证据放在一起保存，再单独留一组用例用于评估。Provider 请求测试只验证序列化和控制流，不能证明模型质量。

> What information can be lost by removing quiet regions? How would you evaluate this detector on your own recording conditions?
> The completed project produces audio.wav, captions.vtt, transcript.json and an HTML page with embedded playback and cue-seek buttons.
> Replace the fixture with a small input from your own workflow. Keep expected outcomes and observed evidence together, then retain a separate set of cases for evaluation. Provider request tests establish serialization and control flow; they do not establish model quality.

## Primary reference · 主要参考

[Official API documentation](https://docs.python.org/3/library/wave.html)（官方 API 文档）。实现、策略取舍和示例均为原创。

> [Official API documentation](https://docs.python.org/3/library/wave.html). The implementation, policy choices and examples are original.
