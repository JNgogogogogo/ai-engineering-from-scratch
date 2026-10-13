# Building a Tokenizer from Scratch · 从零构建生产级分词器

> 第 01 课给了你一个玩具。这一课给你一件武器。

> Lesson 01 gave you a toy. This lesson gives you a weapon.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 10, Lesson 01 (Tokenizers: BPE, WordPiece, SentencePiece)
**Time:** ~90 minutes

## Learning Objectives · 学习目标

- 构建一个能处理 Unicode、空白规范化和特殊 token 的生产级 BPE 分词器
- 实现字节级回退（byte-level fallback），让分词器能编码任何输入（包括 emoji、中日韩文字和代码）而不产生未知 token
- 添加预分词（pre-tokenization）正则模式，在应用 BPE 合并之前先按词边界切分文本
- 在语料上训练一个自定义分词器，并在多语言文本上与 tiktoken 比较压缩率

> Build a production-grade BPE tokenizer that handles Unicode, whitespace normalization, and special tokens
> Implement byte-level fallback so the tokenizer can encode any input (including emoji, CJK, and code) without unknown tokens
> Add pre-tokenization regex patterns that split text at word boundaries before applying BPE merges
> Train a custom tokenizer on a corpus and evaluate its compression ratio against tiktoken on multilingual text

## The Problem · 问题在哪

你在第 01 课写的 BPE 分词器能处理英文文本。现在把日语扔给它。或者 emoji。或者混用 tab 和空格的 Python 代码。

它会崩。

崩的原因不是 BPE 错了——而是实现不完整。一个生产级分词器要能处理任何编码的原始字节，在切分之前先做 Unicode 规范化，管理永远不会被合并的特殊 token，把预分词和子词切分串联起来，而且这一切要快到不拖慢一个处理 15 万亿 token 的训练管道。

GPT-2 的分词器有 50,257 个 token。Llama 3 有 128,256。GPT-4 大约 100,000。这些不是玩具数字。这些词表背后的合并表是在几百 GB 文本上训练出来的，而配套的机制——规范化、预分词、特殊 token 注入、聊天模板格式化——才是「能处理 hello world 的分词器」和「能处理整个互联网的分词器」之间的差距。

你就要把这些机制造出来。

> Your BPE tokenizer from Lesson 01 works on English text. Now throw Japanese at it. Or emoji. Or Python code with mixed tabs and spaces.
> It breaks.
> Not because BPE is wrong -- because the implementation is incomplete. A production tokenizer handles raw bytes in any encoding, normalizes Unicode before splitting, manages special tokens that never get merged, chains pre-tokenization with subword splitting, and does all of this fast enough to not bottleneck a training pipeline processing 15 trillion tokens.
> GPT-2's tokenizer has 50,257 tokens. ... the surrounding machinery -- normalization, pre-tokenization, special token injection, chat template formatting -- is what separates a tokenizer that handles "hello world" from one that handles the entire internet.
> You are going to build that machinery.

## The Concept · 概念

### The Full Pipeline · 完整管道

生产级分词器不是一个算法。它是一条五阶段的流水线，每个阶段解决一个不同的问题。

```mermaid
graph LR
    A[Raw Text] --> B[Normalize]
    B --> C[Pre-Tokenize]
    C --> D[BPE Merge]
    D --> E[Special Tokens]
    E --> F[Token IDs]

    style A fill:#1a1a2e,stroke:#e94560,color:#fff
    style B fill:#1a1a2e,stroke:#e94560,color:#fff
    style C fill:#1a1a2e,stroke:#e94560,color:#fff
    style D fill:#1a1a2e,stroke:#e94560,color:#fff
    style E fill:#1a1a2e,stroke:#e94560,color:#fff
    style F fill:#1a1a2e,stroke:#e94560,color:#fff
```

每个阶段都有明确的职责：

| 阶段 | 它做什么 | 为什么重要 |
|-------|-------------|----------------|
| Normalize（规范化） | NFKC Unicode 规范化，可选小写化，可选去音调符号 | "fi" 连字（U+FB01）变成 "fi"（两个字符）。不做这一步，同一个词会得到不同的 token。 |
| Pre-Tokenize（预切分） | 在 BPE 之前把文本切成块 | 防止 BPE 跨词边界合并。"the cat" 永远不应该产生 "e c" 这样的 token。 |
| BPE Merge（BPE 合并） | 把学到的合并规则应用到字节序列上 | 核心压缩步骤。把原始字节变成子词 token。 |
| Special Tokens（特殊 token） | 注入 [BOS]、[EOS]、[PAD]、聊天模板标记 | 这些 token 有固定 ID，永远不参与 BPE 合并。模型需要它们来表达结构。 |
| ID Mapping（ID 映射） | 把 token 字符串转换成整数 ID | 模型看到的是整数，不是字符串。 |

> A production tokenizer is not one algorithm. It is a pipeline of five stages, each solving a different problem.
> Each stage has a specific job

### Byte-Level BPE · 字节级 BPE

第 01 课的分词器在 UTF-8 字节上操作。这个选择是对的。但我们跳过了一件重要的事：当这些字节不是合法 UTF-8 时会怎样？

字节级 BPE 的解法是把每个可能的字节值（0-255）都当作合法 token。你的基础词表恰好 256 个条目。任何文件——文本、二进制、损坏的——都能被分词，且不会产生未知 token。

GPT-2 加了一个小技巧：把每个字节映射到一个可打印的 Unicode 字符，让词表保持人类可读。字节 0x20（空格）在他们的映射里变成字符 "G"。这纯粹是外观处理，算法并不在乎。

真正的威力：字节级 BPE 能处理地球上所有语言。一个汉字是 3 个 UTF-8 字节。日语可能 3-4 字节。阿拉伯语、天城文、emoji——全都是字节序列。BPE 算法在这些字节序列里找模式的方式，和它在英语 ASCII 字节里找模式的方式一模一样。

> Lesson 01's tokenizer operated on UTF-8 bytes. That was the right call. But we skipped something important: what happens when those bytes are not valid UTF-8?
> Byte-level BPE solves this by treating every possible byte value (0-255) as a valid token. Your base vocabulary is exactly 256 entries. Any file -- text, binary, corrupted -- can be tokenized without producing an unknown token.
> The real power: byte-level BPE handles every language on earth. ... The BPE algorithm finds patterns in these byte sequences exactly the same way it finds patterns in English ASCII bytes.

### Pre-Tokenization · 预分词

在 BPE 碰你的文本之前，先要把它切成块。这能防止合并算法造出跨词边界的 token。

GPT-2 用一个正则模式来切分文本：

```
'(?:[sdmt]|ll|ve|re)| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+
```

这个模式会切分缩写（"don't" 变成 "don" + "'t"）、带可选前导空格的单词、数字、标点和空白。前导空格保留并附着在单词上——所以 "the cat" 变成 [" the", " cat"]，而不是 ["the", " ", "cat"]。

Llama 用 SentencePiece，完全跳过正则。它把原始字节流当作一条长序列，让 BPE 算法自己去琢磨边界在哪。这更简单，但也给了 BPE 更大的自由去造跨词 token。

这个选择有后果。GPT-2 的正则阻止分词器学到「上一个词末尾的 the 和下一个词开头的 the 应该合并」。SentencePiece 允许这种合并，有时压缩效率更高，但 token 的可解释性更差。

> Before BPE touches your text, you need to split it into chunks. This prevents the merge algorithm from creating tokens that span word boundaries.
> This pattern splits on contractions ("don't" becomes "don" + "'t"), words with optional leading spaces, numbers, punctuation, and whitespace. ... so "the cat" becomes [" the", " cat"], not ["the", " ", "cat"].
> Llama uses SentencePiece, which skips regex entirely. ... This is simpler but gives BPE more freedom to create cross-word tokens.
> The choice matters. ... SentencePiece allows it, which sometimes produces more efficient compression but less interpretable tokens.

### Special Tokens · 特殊 token

每个生产级分词器都会为结构性标记保留一些 token ID：

| Token | 用途 | 使用者 |
|-------|---------|---------|
| `[BOS]` / `<s>` | 序列开始 | Llama 3, GPT |
| `[EOS]` / `</s>` | 序列结束 | 所有模型 |
| `[PAD]` | 批对齐用的填充 | BERT, T5 |
| `[UNK]` | 未知 token（字节级 BPE 会消除它） | BERT, WordPiece |
| `<\|im_start\|>` | 聊天消息边界开始 | ChatGPT, Qwen |
| `<\|im_end\|>` | 聊天消息边界结束 | ChatGPT, Qwen |
| `<\|user\|>` | 用户回合标记 | Llama 3 |
| `<\|assistant\|>` | 助手回合标记 | Llama 3 |

特殊 token 永远不会被 BPE 切开。它们在合并算法运行之前被精确匹配、替换成固定 ID，而周围的文本则正常分词。

> Every production tokenizer reserves token IDs for structural markers
> Special tokens are never split by BPE. They are matched exactly before the merge algorithm runs, replaced with their fixed ID, and the surrounding text is tokenized normally.

### Chat Templates · 聊天模板

大多数人在这里犯迷糊，大多数实现在这里出错。

当你给聊天模型发消息时，API 接受一个消息列表：

```
[
  {"role": "system", "content": "You are helpful."},
  {"role": "user", "content": "Hello"},
  {"role": "assistant", "content": "Hi there!"}
]
```

模型看到的不是 JSON，而是一条扁平的 token 序列。聊天模板（chat template）用特殊 token 把消息转换成那条扁平序列。每个模型的做法都不一样：

```
Llama 3:
<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are helpful.<|eot_id|><|start_header_id|>user<|end_header_id|>

Hello<|eot_id|><|start_header_id|>assistant<|end_header_id|>

Hi there!<|eot_id|>

ChatGPT:
<|im_start|>system
You are helpful.<|im_end|>
<|im_start|>user
Hello<|im_end|>
<|im_start|>assistant
Hi there!<|im_end|>
```

模板搞错了，模型就会输出垃圾。它是在某一种精确格式上训练出来的。任何偏差——少一个换行、token 换了位置、多一个空格——都会把输入推到训练分布之外。

> This is where most people get confused and most implementations break.
> The model does not see JSON. It sees a flat token sequence. The chat template converts messages into that flat sequence using special tokens. Every model does this differently
> Get the template wrong and the model produces garbage. It was trained on one exact format. Any deviation -- a missing newline, a swapped token, an extra space -- puts the input outside the training distribution.

### Speed · 速度

对生产级分词来说，Python 太慢了。

tiktoken（OpenAI）用 Rust 编写，带 Python 绑定。HuggingFace tokenizers 也是 Rust。SentencePiece 是 C++。它们比纯 Python 快 10-100 倍。

给个体感：以每秒 100 万 token 的速度（很快的 Python）给 Llama 3 预训练用的 15 万亿 token 分词，需要 174 天。以每秒 1 亿 token 的速度（Rust），只需要 1.7 天。

你用 Python 构建是为了理解算法。在生产环境里，你会用编译实现，只碰 Python 封装层。

```figure
weight-tying
```

> Python is too slow for production tokenization.
> tiktoken (OpenAI) is written in Rust with Python bindings. HuggingFace tokenizers is also Rust. SentencePiece is C++. These achieve 10-100x speedups over pure Python.
> For perspective: tokenizing 15 trillion tokens for Llama 3 pre-training at 1 million tokens per second (fast Python) would take 174 days. At 100 million tokens per second (Rust), it takes 1.7 days.
> You are building in Python to understand the algorithm. In production, you would use a compiled implementation and only touch the Python wrapper.

## Build It · 动手造

### Step 1: Byte-Level Encoding · 步骤 1：字节级编码

地基。把任意字符串转成字节序列，把每个字节映射成一个可打印字符用于显示，并能反转这个过程。

```python
def bytes_to_tokens(text):
    return list(text.encode("utf-8"))

def tokens_to_text(token_bytes):
    return bytes(token_bytes).decode("utf-8", errors="replace")
```

在多语言文本上测试，看看字节数：

```python
texts = [
    ("English", "hello"),
    ("Chinese", "你好"),
    ("Emoji", "🔥"),
    ("Mixed", "hello你好🔥"),
]

for label, text in texts:
    b = bytes_to_tokens(text)
    print(f"{label}: {len(text)} chars -> {len(b)} bytes -> {b}")
```

"hello" 是 5 字节。"你好" 是 6 字节（每个字 3 字节）。火焰 emoji 是 4 字节。字节级分词器不在乎这是什么语言。字节就是字节。

> The foundation. Convert any string into a sequence of bytes, map each byte to a printable character for display, and reverse the process.
> "hello" is 5 bytes. "你好" is 6 bytes (3 per character). The fire emoji is 4 bytes. The byte-level tokenizer does not care what language it is. Bytes are bytes.

### Step 2: Pre-Tokenizer with Regex · 步骤 2：带正则的预分词器

用 GPT-2 的正则模式把文本切成块。每个块会被 BPE 独立分词。

```python
import re

try:
    import regex
    GPT2_PATTERN = regex.compile(
        r"""'(?:[sdmt]|ll|ve|re)| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""
    )
except ImportError:
    GPT2_PATTERN = re.compile(
        r"""'(?:[sdmt]|ll|ve|re)| ?[a-zA-Z]+| ?[0-9]+| ?[^\s\w]+|\s+(?!\S)|\s+"""
    )

def pre_tokenize(text):
    return [match.group() for match in GPT2_PATTERN.finditer(text)]
```

`regex` 模块支持 Unicode 属性转义（`\p{L}` 表示字母，`\p{N}` 表示数字）。标准库的 `re` 模块不支持，所以我们回退到 ASCII 字符类。要做生产级多语言分词器，请安装 `regex`。

试试看：

```python
print(pre_tokenize("Hello, world! Don't stop."))
# [' Hello', ',', ' world', '!', " Don", "'t", ' stop', '.']
```

前导空格附着在单词上。缩写在撇号处切开。标点自成一块。BPE 永远不会跨这些边界合并 token。

> Split text into chunks using the GPT-2 regex pattern. Each chunk gets tokenized independently by BPE.
> The `regex` module supports Unicode property escapes (`\p{L}` for letters, `\p{N}` for numbers). The standard library `re` module does not, so we fall back to ASCII character classes. For production multilingual tokenizers, install `regex`.
> The leading space stays attached to the word. Contractions split at the apostrophe. Punctuation becomes its own chunk. BPE will never merge tokens across these boundaries.

### Step 3: BPE on Byte Sequences · 步骤 3：在字节序列上跑 BPE

第 01 课的核心算法，但现在作用在预切分的块上、各自独立处理。

```python
from collections import Counter

def get_byte_pairs(chunks):
    pairs = Counter()
    for chunk in chunks:
        byte_seq = list(chunk.encode("utf-8"))
        for i in range(len(byte_seq) - 1):
            pairs[(byte_seq[i], byte_seq[i + 1])] += 1
    return pairs

def apply_merge(byte_seq, pair, new_id):
    merged = []
    i = 0
    while i < len(byte_seq):
        if i < len(byte_seq) - 1 and byte_seq[i] == pair[0] and byte_seq[i + 1] == pair[1]:
            merged.append(new_id)
            i += 2
        else:
            merged.append(byte_seq[i])
            i += 1
    return merged
```

> The core algorithm from Lesson 01, but now operating on pre-tokenized chunks independently.

### Step 4: Special Token Handling · 步骤 4：特殊 token 处理

特殊 token 需要精确匹配和固定 ID。它们完全绕过 BPE。

```python
class SpecialTokenHandler:
    def __init__(self):
        self.special_tokens = {}
        self.pattern = None

    def add_token(self, token_str, token_id):
        self.special_tokens[token_str] = token_id
        escaped = [re.escape(t) for t in sorted(self.special_tokens.keys(), key=len, reverse=True)]
        self.pattern = re.compile("|".join(escaped))

    def split_with_specials(self, text):
        if not self.pattern:
            return [(text, False)]
        parts = []
        last_end = 0
        for match in self.pattern.finditer(text):
            if match.start() > last_end:
                parts.append((text[last_end:match.start()], False))
            parts.append((match.group(), True))
            last_end = match.end()
        if last_end < len(text):
            parts.append((text[last_end:], False))
        return parts
```

> Special tokens need exact matching and fixed IDs. They bypass BPE entirely.

### Step 5: Full Tokenizer Class · 步骤 5：完整分词器类

把所有环节串起来：规范化、按特殊 token 切分、预分词、BPE 合并、映射到 ID。

```python
import unicodedata

class ProductionTokenizer:
    def __init__(self):
        self.merges = {}
        self.vocab = {i: bytes([i]) for i in range(256)}
        self.special_handler = SpecialTokenHandler()
        self.next_id = 256

    def normalize(self, text):
        return unicodedata.normalize("NFKC", text)

    def train(self, text, num_merges):
        text = self.normalize(text)
        chunks = pre_tokenize(text)
        chunk_bytes = [list(chunk.encode("utf-8")) for chunk in chunks]

        for i in range(num_merges):
            pairs = Counter()
            for seq in chunk_bytes:
                for j in range(len(seq) - 1):
                    pairs[(seq[j], seq[j + 1])] += 1
            if not pairs:
                break
            best = max(pairs, key=pairs.get)
            new_id = self.next_id
            self.next_id += 1
            self.merges[best] = new_id
            self.vocab[new_id] = self.vocab[best[0]] + self.vocab[best[1]]
            chunk_bytes = [apply_merge(seq, best, new_id) for seq in chunk_bytes]

    def add_special_token(self, token_str):
        token_id = self.next_id
        self.next_id += 1
        self.special_handler.add_token(token_str, token_id)
        self.vocab[token_id] = token_str.encode("utf-8")
        return token_id

    def encode(self, text):
        text = self.normalize(text)
        parts = self.special_handler.split_with_specials(text)
        all_ids = []
        for part_text, is_special in parts:
            if is_special:
                all_ids.append(self.special_handler.special_tokens[part_text])
            else:
                for chunk in pre_tokenize(part_text):
                    byte_seq = list(chunk.encode("utf-8"))
                    for pair, new_id in self.merges.items():
                        byte_seq = apply_merge(byte_seq, pair, new_id)
                    all_ids.extend(byte_seq)
        return all_ids

    def decode(self, ids):
        byte_parts = []
        for token_id in ids:
            if token_id in self.vocab:
                byte_parts.append(self.vocab[token_id])
        return b"".join(byte_parts).decode("utf-8", errors="replace")

    def vocab_size(self):
        return len(self.vocab)
```

> Chain everything together: normalize, split on special tokens, pre-tokenize, BPE merge, map to IDs.

### Step 6: Multilingual Test · 步骤 6：多语言测试

真正的考验。把英语、中文、emoji 和代码都扔给它。

```python
corpus = (
    "The quick brown fox jumps over the lazy dog. "
    "The quick brown fox runs through the forest. "
    "Machine learning models process natural language. "
    "Deep learning transforms how we build software. "
    "def train(model, data): return model.fit(data) "
    "def predict(model, x): return model(x) "
)

tok = ProductionTokenizer()
tok.train(corpus, num_merges=50)

bos = tok.add_special_token("<|begin|>")
eos = tok.add_special_token("<|end|>")

test_texts = [
    "The quick brown fox.",
    "你好世界",
    "Hello 🌍 World",
    "def foo(x): return x + 1",
    f"<|begin|>Hello<|end|>",
]

for text in test_texts:
    ids = tok.encode(text)
    decoded = tok.decode(ids)
    print(f"Input:   {text}")
    print(f"Tokens:  {len(ids)} ids")
    print(f"Decoded: {decoded}")
    print()
```

每个汉字产生 3 字节。emoji 产生 4 字节。没有一个会让分词器崩溃，没有一个会产生未知 token。这就是字节级 BPE 的威力。

> Chinese characters produce 3 bytes each. The emoji produces 4 bytes. None of these crash the tokenizer. None produce unknown tokens. That is the power of byte-level BPE.

## Use It · 实战用法

### Comparing Real Tokenizers · 对比真实的分词器

加载 Llama 3、GPT-4 和 Mistral 的真实分词器，看看它们各自如何处理同一段多语言段落。

```python
import tiktoken

gpt4_enc = tiktoken.get_encoding("cl100k_base")

test_paragraph = "Machine learning is powerful. 机器学习很强大。 L'apprentissage automatique est puissant. 🤖💪"

tokens = gpt4_enc.encode(test_paragraph)
pieces = [gpt4_enc.decode([t]) for t in tokens]
print(f"GPT-4 ({len(tokens)} tokens): {pieces}")
```

```python
from transformers import AutoTokenizer

llama_tok = AutoTokenizer.from_pretrained("meta-llama/Meta-Llama-3-8B")
mistral_tok = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-v0.1")

for name, tok in [("Llama 3", llama_tok), ("Mistral", mistral_tok)]:
    tokens = tok.encode(test_paragraph)
    pieces = tok.convert_ids_to_tokens(tokens)
    print(f"{name} ({len(tokens)} tokens): {pieces[:20]}...")
```

同一段文本，你会看到不同的 token 数。128K 词表的 Llama 3 在合并常见模式上更激进。100K 的 GPT-4 居中。32K 的 Mistral 产出更多 token，但嵌入层更小。

权衡永远不变：更大的词表意味着更短的序列，但更多参数。

> Load the actual tokenizers from Llama 3, GPT-4, and Mistral. See how each handles the same multilingual paragraph.
> You will see different token counts for the same text. Llama 3 with 128K vocabulary is more aggressive at merging common patterns. GPT-4 with 100K sits in the middle. Mistral with 32K produces more tokens but has a smaller embedding layer.
> The tradeoff is always the same: larger vocabulary means shorter sequences but more parameters.

## Ship It · 交付

本课产出一个用于构建和调试生产级分词器的提示词。见 `outputs/prompt-tokenizer-builder.md`。

> This lesson produces a prompt for building and debugging production tokenizers. See `outputs/prompt-tokenizer-builder.md`.

## Exercises · 练习

1. **简单：** 加一个 `get_token_bytes(id)` 方法，显示任意 token ID 的原始字节。用它检查你最常用的合并 token 到底代表什么。
2. **中等：** 实现 Llama 风格的预分词器：按空白和数字切分，但保留前导空格。在同一语料上把它的词表与 GPT-2 正则方案做比较。
3. **困难：** 加一个聊天模板方法，接受 `{"role": ..., "content": ...}` 消息列表，为 Llama 3 聊天格式生成正确的 token 序列。与 HuggingFace 的实现对拍验证。

## Key Terms · 关键术语

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|----------------------|
| Byte-level BPE | "在字节上工作的分词器" | 以 256 个字节值为基础词表的 BPE——任何输入都不会产生未知 token |
| Pre-tokenization | "BPE 之前先切分" | 用正则或规则做的切分，防止 BPE 跨词边界合并 |
| NFKC normalization | "Unicode 清理" | 先规范分解再兼容组合——"fi" 连字变成 "fi"，全角 "A" 变成 "A" |
| Chat template | "消息如何变成 token" | 把 role/content 消息列表转换成扁平 token 序列的精确格式——每个模型各不相同，必须与训练格式一致 |
| Special tokens | "控制 token" | 绕过 BPE 的保留 token ID——[BOS]、[EOS]、[PAD]、聊天标记——在合并前被精确匹配 |
| Fertility | "每个词几个 token" | 输出 token 数与输入词数之比——GPT-4 上英语是 1.3，韩语 2-3，越高浪费的上下文越多 |
| tiktoken | "OpenAI 的分词器" | Rust 实现的 BPE，带 Python 绑定——比纯 Python 快 10-100 倍 |
| Merge table | "词表" | 训练中学到的字节对合并的有序列表——这是分词器学到的全部知识 |

## Further Reading · 延伸阅读

- [OpenAI tiktoken source](https://github.com/openai/tiktoken) —— GPT-3.5/4 使用的 Rust BPE 实现
- [HuggingFace tokenizers](https://github.com/huggingface/tokenizers) —— 支持 BPE、WordPiece、Unigram 的 Rust 分词器库
- [Llama 3 paper (Meta, 2024)](https://arxiv.org/abs/2407.21783) —— 128K 词表与分词器训练的细节
- [SentencePiece (Kudo & Richardson, 2018)](https://arxiv.org/abs/1808.06226) —— 语言无关的分词方案
- [GPT-2 tokenizer source](https://github.com/openai/gpt-2/blob/master/src/encoder.py) —— 最初的字节到 Unicode 映射
