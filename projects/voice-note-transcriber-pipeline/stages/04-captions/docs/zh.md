# Export a transcript you can hear and correct · 导出听得见、改得动的转写稿

> The fixture CLI pairs the original spoken clip with its supplied reference text and labels the method clearly. Real recognition instead uses --endpoint. After inspecting playback, edit the rows in transcript.json and run --review-file to rerender; the report must match the original audio hash.

**Type:** Build
**Stage:** 4 of 4
**Time:** About 2 hours

## The useful boundary · 有用的边界

在输出边界把片段时间渲染成 WebVTT。校验 cue 有限、有序、互不重叠且文本非空。保存原始 WAV 和一份 JSON 报告，然后构建一个本地审阅页面，内嵌音频和能跳转到每个片段的按钮。字幕描述的是片段边界，不是推断出来的词级对齐。

```figure
pj-voice-note-transcriber-pipeline-4
```

> Render segment times as WebVTT at the output boundary. Validate finite, ordered, nonoverlapping cues with nonempty text. Save the original WAV and a JSON report, then build a local review page with embedded audio and buttons that seek to each segment. The captions describe segment boundaries, not inferred word alignment.

## Work the example · 先把例子算明白

夹具 CLI 把原始口播片段和提供的参考文本配对，并清楚标注所用方法。真实识别则改用 --endpoint。检查回放之后，编辑 transcript.json 里的行并运行 --review-file 重新渲染；报告必须与原始音频哈希匹配。

写代码之前，先写下要返回的字段和预期的副作用次数。再保留一个应当失败的输入，防止成功的例子被硬编码成答案。

> The fixture CLI pairs the original spoken clip with its supplied reference text and labels the method clearly. Real recognition instead uses --endpoint. After inspecting playback, edit the rows in transcript.json and run --review-file to rerender; the report must match the original audio hash.
> Write the returned fields and the expected side-effect count before coding. Keep a second input that should fail so the successful example cannot become a hard-coded answer.

## Build the contract · 构建契约

在你的学习工作区（learner workspace）里实现 `stamp, captions in captions.py; export_transcript and the CLI in pipeline.py`。保持导出名称不变，并继续复用此前阶段，而不是复制它们的策略。

写出 audio.wav、captions.vtt、transcript.json 和 index.html。拒绝结束时间超出音频时长的 cue。在 HTML 中转义转写文本和方法标签。提供的 transcript-file 是绑定哈希的参考模式，不能与分段（segmentation）组合使用。参考模式和审阅模式都不发生任何 provider 调用。

`export_transcript` 返回写进 transcript.json 的同一个对象：`schema_version=1`、提供的 `method`、原始 WAV 字节的 `audio_sha256`、`duration_seconds` 和原样保留的 `rows`。每行包含以秒计的 start 和 end 外加 text；provider 行还可以携带片段哈希和尝试次数。导出时保留这些额外字段。时长用解码后的样本数除以实际采样率来计算。把 WAV 以 base64 音频源内嵌进页面，这样本地打开 HTML 时播放仍然可用。

> Implement `stamp, captions in captions.py; export_transcript and the CLI in pipeline.py` in your learner workspace. Preserve the exported names and continue using earlier stages rather than duplicating their policies.
> Write audio.wav, captions.vtt, transcript.json and index.html. Reject cues ending beyond the audio duration. Escape transcription text and method labels in HTML. A supplied transcript-file is a hash-bound reference mode and cannot be combined with segmentation. No provider call occurs in reference or review mode.
> `export_transcript` returns the same object written to transcript.json: `schema_version=1`, the supplied `method`, `audio_sha256` of the original WAV bytes, `duration_seconds` and the unchanged `rows`. Each row contains start and end in seconds plus text; provider rows can also carry segment hashes and attempt counts. Keep those extra fields when exporting. Compute duration from the decoded sample count divided by the actual sample rate. Embed the WAV as a base64 audio source so playback continues to work when the HTML is opened locally.

## Hints · 提示

打开导出的页面，播放真实音频并点击一个 cue。把 JSON 行和它的 WebVTT 时间戳做对比。在测试里把一条字幕改成类 HTML 字符串，确认它按纯文本渲染。

> Open the exported page, play the actual audio and click a cue. Compare the JSON row with its WebVTT timestamp. Change a caption to an HTML-like string in a test and confirm it renders as text.

## Verify your work · 验证你的实现

```bash
python3 scripts/project_test.py voice-note-transcriber-pipeline --init my-voice-note-transcriber-pipeline
python3 scripts/project_test.py voice-note-transcriber-pipeline --stage 4 --path my-voice-note-transcriber-pipeline --strict
```

初始化只需一次。累积测试会导入你的工作区并保留你此前的源码。跑参考解法（reference solution）只是验证教学实现，永远不会颁发学习者证书。可选的 SDK 检查需要项目 README 里列出的依赖和命令。

> Initialize once. Cumulative tests import your workspace and preserve your earlier source. A reference-solution run verifies the teaching implementation and never grants a learner certificate. Optional SDK checks require the dependencies and commands in the project README.

## Inspect the result · 检查结果

裁剪音频之后，哪些字段需要更新？为什么一个可编辑的参考转写是有用的集成测试，却算不上语音识别基准？

完整的项目会产出 audio.wav、captions.vtt、transcript.json，以及一个带内嵌播放和 cue 跳转按钮的 HTML 页面。

```bash
cd projects/voice-note-transcriber-pipeline/solution
python3 pipeline.py --input fixtures/repair-note.wav --transcript-file fixtures/reference.json --out voice-output
```

把夹具换成你自己工作流里的一段小输入。把预期结果和观察到的证据放在一起保存，再单独留一组用例用于评估。Provider 请求测试只验证序列化和控制流，不能证明模型质量。

> Which fields would need updating after trimming the audio? Why is an editable reference transcript a useful integration test without being a speech-recognition benchmark?
> The completed project produces audio.wav, captions.vtt, transcript.json and an HTML page with embedded playback and cue-seek buttons.
> Replace the fixture with a small input from your own workflow. Keep expected outcomes and observed evidence together, then retain a separate set of cases for evaluation. Provider request tests establish serialization and control flow; they do not establish model quality.

## Primary reference · 主要参考

[Official API documentation](https://docs.python.org/3/library/wave.html)（官方 API 文档）。实现、策略取舍和示例均为原创。

> [Official API documentation](https://docs.python.org/3/library/wave.html). The implementation, policy choices and examples are original.
