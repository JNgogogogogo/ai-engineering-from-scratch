# Decode the audio clock before processing · 先解码音频时钟，再处理数据

> The integer samples 0, 16384 and -16384 become 0, 0.5 and -0.5. A sample index of 800 at 16000 Hz means 0.05 seconds. Interpreting the same index at 8000 Hz would double the timestamp without changing a single byte.

**Type:** Build
**Stage:** 1 of 4
**Time:** About 2 hours

## The useful boundary · 有用的边界

在解读字节之前，先读取 WAV 头（WAV header）。内核只接受未压缩的单声道有符号 16 位 PCM，并把样本统一除以 32768 归一化。必须保留真实的采样率（sample rate）：后面每一个时间戳都是「样本索引 ÷ 采样率」。不支持的立体声或压缩输入必须显式失败（fail visibly）。

```figure
pj-voice-note-transcriber-pipeline-1
```

> Read the WAV header before interpreting bytes. The core accepts uncompressed mono signed 16-bit PCM and normalizes samples by 32768. Preserve the actual sample rate: every later timestamp is a sample index divided by that rate. Unsupported stereo or compressed input must fail visibly.

## Work the example · 先把例子算明白

整数样本 0、16384 和 -16384 分别变成 0、0.5 和 -0.5。在 16000 Hz 下，样本索引 800 意味着 0.05 秒；把同一个索引按 8000 Hz 去解读，时间戳会翻倍，而一个字节都没有变。

写代码之前，先写下要返回的字段和预期的副作用次数。再保留一个应当失败的输入，防止成功的例子被硬编码成答案。

> The integer samples 0, 16384 and -16384 become 0, 0.5 and -0.5. A sample index of 800 at 16000 Hz means 0.05 seconds. Interpreting the same index at 8000 Hz would double the timestamp without changing a single byte.
> Write the returned fields and the expected side-effect count before coding. Keep a second input that should fail so the successful example cannot become a hard-coded answer.

## Build the contract · 构建契约

在你的学习工作区（learner workspace）里实现 `decode_wav(data), encode_wav(samples, rate=16000) in pcm.py`。保持导出名称不变，并继续复用此前阶段，而不是把它们的策略复制一份。

自带的 repair-note.wav 是一句 5.685 秒的口播句子，用操作系统语音在本地合成。配套的 reference.json 包含作者提供的文本和原始 WAV 的哈希。它是一个语音测试夹具（fixture），不是项目真的识别了语音的证明。运行已提交的夹具不需要那个生成工具。

> Implement `decode_wav(data), encode_wav(samples, rate=16000) in pcm.py` in your learner workspace. Preserve the exported names and continue using earlier stages rather than duplicating their policies.
> The authored repair-note.wav is a 5.685-second spoken sentence synthesized locally with the operating system voice. Its companion reference.json contains author-supplied text and a hash of the original WAV. It is a speech fixture, not proof that the project recognized speech. The generation tool is not needed to run the committed fixture.

## Hints · 提示

在解包之前检查声道数、样本位宽和压缩类型。验证字节数等于「声明的帧数 × 2」。测试负样本，以及最大正有符号值处的削波（clipping）。

> Check channels, sample width and compression type before unpacking. Verify the byte count equals the declared frame count times two. Test negative samples and clipping at the largest positive signed value.

## Verify your work · 验证你的实现

```bash
python3 scripts/project_test.py voice-note-transcriber-pipeline --init my-voice-note-transcriber-pipeline
python3 scripts/project_test.py voice-note-transcriber-pipeline --stage 1 --path my-voice-note-transcriber-pipeline --strict
```

初始化只需一次。累积测试会导入你的工作区并保留你此前的源码。跑参考解法（reference solution）只是验证教学实现，永远不会颁发学习者证书。可选的 SDK 检查需要项目 README 里列出的依赖和命令。

> Initialize once. Cumulative tests import your workspace and preserve your earlier source. A reference-solution run verifies the teaching implementation and never grants a learner certificate. Optional SDK checks require the dependencies and commands in the project README.

## Inspect the result · 检查结果

为什么采样率若靠猜测，正确的样本值仍可能产出错误的字幕？处理手机语音便签之前，应该先做哪一步转换？

完整的项目会产出 audio.wav、captions.vtt、transcript.json，以及一个带内嵌播放和 cue 跳转按钮的 HTML 页面。

```bash
cd projects/voice-note-transcriber-pipeline/solution
python3 pipeline.py --input fixtures/repair-note.wav --transcript-file fixtures/reference.json --out voice-output
```

把夹具换成你自己工作流里的一段小输入。把预期结果和观察到的证据放在一起保存，再单独留一组用例用于评估。Provider 请求测试只验证序列化和控制流，不能证明模型质量。

> Why can valid sample values still yield incorrect captions if the sample rate is guessed? Which conversion should happen before processing a phone voice note?
> The completed project produces audio.wav, captions.vtt, transcript.json and an HTML page with embedded playback and cue-seek buttons.
> Replace the fixture with a small input from your own workflow. Keep expected outcomes and observed evidence together, then retain a separate set of cases for evaluation. Provider request tests establish serialization and control flow; they do not establish model quality.

## Primary reference · 主要参考

[Official API documentation](https://docs.python.org/3/library/wave.html)（官方 API 文档）。实现、策略取舍和示例均为原创。

> [Official API documentation](https://docs.python.org/3/library/wave.html). The implementation, policy choices and examples are original.
