# Send real WAV bytes through a recognizer boundary · 把真实 WAV 字节送过识别器边界

> A provider timeout followed by success records attempts=2. Each output row retains start, end, text and the SHA256 of the exact encoded segment. A second segment cannot overlap the previous one, and fractional sample indices are invalid.

**Type:** Build
**Stage:** 3 of 4
**Time:** About 2 hours

## The useful boundary · 有用的边界

先把每个选中的片段编码成完整的 WAV，再调用 provider。真实的 HTTP 适配器（adapter）把 multipart 表单数据（带 model 和 file 字段）发送到显式配置的 audio/transcriptions 端点。它解析返回的文本，并拒绝空结果或畸形结果。端点选择就是显式的上传边界。

```figure
pj-voice-note-transcriber-pipeline-3
```

> Encode each selected span as a complete WAV before calling the provider. The real HTTP adapter sends multipart form data with model and file fields to an explicitly configured audio/transcriptions endpoint. It parses the returned text and rejects an empty or malformed result. Endpoint selection is the explicit upload boundary.

## Work the example · 先把例子算明白

provider 超时一次然后成功，会记录 attempts=2。每行输出都保留 start、end、text 以及精确编码片段的 SHA256。第二个片段不能与前一个重叠，小数样本索引无效。

写代码之前，先写下要返回的字段和预期的副作用次数。再保留一个应当失败的输入，防止成功的例子被硬编码成答案。

> A provider timeout followed by success records attempts=2. Each output row retains start, end, text and the SHA256 of the exact encoded segment. A second segment cannot overlap the previous one, and fractional sample indices are invalid.
> Write the returned fields and the expected side-effect count before coding. Keep a second input that should fail so the successful example cannot become a hard-coded answer.

## Build the contract · 构建契约

在你的学习工作区（learner workspace）里实现 `transcribe(...) in transcribe.py; http_recognizer(endpoint, model, api_key, timeout) in provider.py`。保持导出名称不变，并继续复用此前阶段，而不是复制它们的策略。

允许 0 到 5 次重试，只对 TimeoutError 重试，并统计尝试次数。适配器在远程强制 HTTPS，只对 localhost 或显式给出的环回（loopback）IPv4/IPv6 地址放行 HTTP。校验主机名和端口，拒绝 URL 凭据、fragment 和空白字符。用一个专门的 urllib opener 拒绝一切重定向（其 HTTPRedirectHandler.redirect_request 返回 None）；凭据和音频始终绑定在所选端点上。适配器还检查 WAV 签名、20 MB 上传上限、1 MB 响应上限和不超过 120 秒的超时。TRANSCRIPTION_API_KEY 提供可选认证。受控传输测试验证的是真实的 multipart 序列化；它们不衡量识别准确率。

> Implement `transcribe(...) in transcribe.py; http_recognizer(endpoint, model, api_key, timeout) in provider.py` in your learner workspace. Preserve the exported names and continue using earlier stages rather than duplicating their policies.
> Allow zero through five retries, retry only TimeoutError, and count attempts. The adapter requires HTTPS remotely and permits HTTP only for localhost or an explicit loopback IPv4/IPv6 address. Validate a hostname and port, rejecting URL credentials, fragments and whitespace. Reject every redirect with a dedicated urllib opener whose HTTPRedirectHandler.redirect_request returns None; credentials and audio stay tied to the selected endpoint. It also checks a WAV signature, a 20 MB upload bound, a 1 MB response bound and a timeout of at most 120 seconds. TRANSCRIPTION_API_KEY supplies optional authentication. Controlled transport tests verify real multipart serialization; they do not measure recognition accuracy.

## Hints · 提示

在测试里捕获发出去的请求，确认其中装的是 WAV 字节而不是文件名字符串。让测试端点返回一句不同的保留句（held-out sentence）。把源哈希和文本放在一起，才能把审阅过的转写关联回它真正的音频。

> Capture the outgoing request in a test and confirm it contains the WAV bytes rather than a filename string. Return a distinct held-out sentence from the test endpoint. Keep source hashes next to text so a reviewed transcript can be related to its actual audio.

## Verify your work · 验证你的实现

```bash
python3 scripts/project_test.py voice-note-transcriber-pipeline --init my-voice-note-transcriber-pipeline
python3 scripts/project_test.py voice-note-transcriber-pipeline --stage 3 --path my-voice-note-transcriber-pipeline --strict
```

初始化只需一次。累积测试会导入你的工作区并保留你此前的源码。跑参考解法（reference solution）只是验证教学实现，永远不会颁发学习者证书。可选的 SDK 检查需要项目 README 里列出的依赖和命令。

> Initialize once. Cumulative tests import your workspace and preserve your earlier source. A reference-solution run verifies the teaching implementation and never grants a learner certificate. Optional SDK checks require the dependencies and commands in the project README.

## Inspect the result · 检查结果

为什么认证错误应该立即失败，而不是消耗掉超时重试预算？音频哈希能确立什么，又不能确立什么？

完整的项目会产出 audio.wav、captions.vtt、transcript.json，以及一个带内嵌播放和 cue 跳转按钮的 HTML 页面。

```bash
cd projects/voice-note-transcriber-pipeline/solution
python3 pipeline.py --input fixtures/repair-note.wav --transcript-file fixtures/reference.json --out voice-output
```

把夹具换成你自己工作流里的一段小输入。把预期结果和观察到的证据放在一起保存，再单独留一组用例用于评估。Provider 请求测试只验证序列化和控制流，不能证明模型质量。

> Why should an authentication error fail immediately instead of consuming the timeout retry budget? What does the audio hash establish, and what does it not establish?
> The completed project produces audio.wav, captions.vtt, transcript.json and an HTML page with embedded playback and cue-seek buttons.
> Replace the fixture with a small input from your own workflow. Keep expected outcomes and observed evidence together, then retain a separate set of cases for evaluation. Provider request tests establish serialization and control flow; they do not establish model quality.

## Primary reference · 主要参考

[Official API documentation](https://docs.python.org/3/library/wave.html)（官方 API 文档）。实现、策略取舍和示例均为原创。

> [Official API documentation](https://docs.python.org/3/library/wave.html). The implementation, policy choices and examples are original.
