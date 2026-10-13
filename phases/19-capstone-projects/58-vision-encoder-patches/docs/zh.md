# Vision Encoder Patches · 视觉编码器的图块化

会读像素的视觉模型需要一个「像素分词器」。图块嵌入（patch embedding）就是这个分词器：把图像切成方块网格，把每个方块展平，过一个线性层做投影，再加上一个 2D 位置信号，让 transformer 知道每个方块在原图中的位置。

> A vision model that reads pixels needs a tokenizer for pixels. Patch embedding is that tokenizer. Cut the image into a grid of squares, flatten each square, project it through one linear layer, then add a 2D position signal so the transformer knows where each square sat in the original image.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 19 lessons 30-37 (Track B foundations)
**Time:** ~90 minutes

## Learning Objectives · 学习目标

- 把一张图像分词（tokenize）成定长的图块嵌入序列。
- 实现基于 `Conv2d` 的图块投影，其数学与「先 unfold 再过线性层」完全一致。
- 构建确定性的 2D 正弦位置嵌入（sinusoidal position embedding），让 token 顺序编码空间位置。
- 在合成测试数据（fixture）上验证图块数量、嵌入形状，以及 `Conv2d` 与 unfold 两种写法的等价性。

> Tokenize an image into a fixed-length sequence of patch embeddings.
> Implement a `Conv2d`-based patch projection that matches the math of unfold-then-linear.
> Build a deterministic 2D sinusoidal position embedding so token order encodes spatial position.
> Verify patch count, embedding shape, and `Conv2d`/unfold equivalence on a synthetic fixture.

## The Problem · 问题在哪

transformer 吃的是向量序列，图像却是一个 3 通道网格。把每个像素都当成一个 token 会让序列长度爆炸：一张 224x224 的 RGB 图像是 150,528 个 token，12 层 transformer 的注意力根本负担不起。把整张图当成一个巨大的扁平向量则会丢掉局部性（locality），而注意力层无法把它找回来。编码器前端的任务，就是把像素网格压缩成几百个 token，每个 token 概括一个方块区域。

图块嵌入用一次线性投影解决了这个问题。把 224x224 的图像切成 16x16 的图块（patch），得到 14x14 网格共 196 个图块。每个图块从 `(3, 16, 16) = 768` 个像素值展平成一个向量，再由一个线性层映射到模型的隐藏维度。transformer 看到的是 196 个维度为 `hidden`（通常 768）的 token，外加一个 CLS token。这才是一条网络其余部分嚼得动的序列。

> A transformer eats a sequence of vectors. An image is a 3-channel grid. ... The job of the encoder front end is to compress the pixel grid into a few hundred tokens that each summarize a square region.
> Patch embedding solves this with one linear projection. ... The transformer sees 196 tokens of dimension `hidden` (commonly 768) plus a CLS token. That is a sequence the rest of the network can chew on.

## The Concept · 概念

```mermaid
flowchart LR
  Image[224x224x3 image] --> Cut[cut into 16x16 patches]
  Cut --> Grid[14x14 grid of patches]
  Grid --> Flatten[flatten each patch]
  Flatten --> Proj[linear projection]
  Proj --> Tokens[196 tokens of dim hidden]
  Tokens --> Pos[add 2D sinusoidal position]
  Pos --> Out[final token sequence]
```

### Why patches, not pixels · 为什么用图块，而不是像素

注意力的计算量随序列长度平方增长。196 个 token 的序列，每个头每层要算 `196 * 196 = 38,416` 个注意力分数；150,528 个 token 的序列要算 `150,528 * 150,528 = 22.6 billion`（226 亿）。图块把注意力计算量降了 59 万倍，而单个 16x16 区域携带的信号足以支撑高层视觉任务。代价是丢了图块内部的细粒度空间细节——这正是当下游多模态系统需要精细定位时，往往要再挂一条高分辨率分支的原因。

> Attention is quadratic in sequence length. ... Patches buy a 590,000x reduction in attention compute, and a single 16x16 region carries enough signal for high-level vision tasks. The cost is a loss of fine-grained spatial detail inside one patch, which is why downstream multimodal stacks often run a second high-resolution branch when fine localization matters.

### Why a linear projection is enough · 为什么一层线性投影就够

每个图块被当作一个独立向量来对待。投影层学到的是一组基（basis）：边缘检测器、颜色滤波器、简单纹理。单个线性层很小（ViT-Base 为 `768 * 768 = 589,824` 个参数），训练很快。也存在更深的卷积 stem（「hybrid」ViT），但扁平的线性投影才是标准形态，如今大多数开源权重（open-weight）编码器出厂就是这个形状。

> Each patch is treated as an independent vector. The projection learns a basis: edge detectors, color filters, simple textures. ... Deeper convolutional stems exist (the "hybrid" ViT), but a flat linear projection is the standard, and most modern open-weight encoders ship with this exact shape.

### The `Conv2d` trick · `Conv2d` 技巧

一个不加 padding 的 `Conv2d(in_channels=3, out_channels=hidden, kernel_size=patch_size, stride=patch_size)`，与「先 unfold 再过线性层」给出完全相同的数值结果，因为每个输出位置都是把图块像素与一个滤波器做点积。这个卷积就是图块投影本身，大多数生产代码库都这么写：GPU 上更快，还少一次 reshape。

> A `Conv2d(in_channels=3, out_channels=hidden, kernel_size=patch_size, stride=patch_size)` with no padding gives the same numerical result as unfold-then-linear, because each output position dot-products the patch pixels against one filter. The convolution is the patch projection, and most production codebases ship it that way because it is faster on GPU and uses one fewer reshape.

### Position embeddings · 位置嵌入

投影出来的 token 本身不带任何顺序信息。2D 正弦嵌入给每个 token 一个固定信号，编码它的 `(row, col)` 位置。嵌入维度的一半用多个频率的 sin/cos 编码行位置，另一半编码列位置。这个编码是确定性的，所以换分辨率不用重训，而且能干净地插值到训练时从未见过的网格。

> Tokens carry no order out of the projection. The 2D sinusoidal embedding gives each token a fixed signal that encodes its `(row, col)` position. ... The encoding is deterministic so you can swap resolutions without retraining, and it interpolates cleanly to grids the model never saw at training time.

| 组件 | 形状 | 参数量 |
|------|------|--------|
| 图块投影（`Conv2d`） | `(hidden, 3, patch, patch)` | `3 * P * P * hidden + hidden` |
| 位置嵌入（固定） | `(num_patches, hidden)` | 0（计算得出，非学习） |
| CLS token（可学习） | `(1, hidden)` | `hidden` |

以 224 分辨率的 ViT-Base/16 为例：投影 590,592 个参数，CLS token 768 个，正弦位置嵌入为零。下一课（59）会在这个前端之上叠一个 12 层 transformer。

### Equivalence as a sanity check · 用等价性做健全性检查

图块这一步有两种拼法：`Conv2d` 投影，和显式的「先 unfold 再线性层」。同样的权重必须产出同样的输出。产不出，就说明 unfold 的数学写错了，编码器其余部分全都盖在沙子上。本课的测试检验的正是这个等价性。

> The patch step has two spellings: a `Conv2d` projection and an explicit unfold-then-linear. They must produce the same output for the same weights. If they do not, the unfold math is wrong, and the rest of the encoder is built on sand. The tests in this lesson exercise that equivalence.

```figure
ch-patch-tokenizer
```

## Build It · 动手造

`code/main.py` 实现了：

- `PatchEmbed`：一个包着 `Conv2d` 做图块投影的 `nn.Module`。
- `sinusoidal_2d(grid_h, grid_w, dim)`：构建 2D 位置表的无状态函数。
- `VisionFrontEnd`：把图块嵌入、前置 CLS、位置相加组合成一次前向传播。
- 辅助函数 `synthesize_image(seed)`：用 `numpy.random` 构建确定性的 224x224x3 测试图。
- 一个演示：把一张测试图送进前端，打印输出形状、CLS token 范数，以及位置嵌入的一行。

运行：

```bash
python3 code/main.py
```

输出：224x224 测试图被分词成形状为 `(1, 197, 768)` 的序列。第一个 token 是 CLS，其后 196 个是图块 token。位置嵌入的范数在同一行内部均匀一致，这正是正弦编码的签名。

> Output: the 224x224 fixture is tokenized to a sequence of shape `(1, 197, 768)`. The first token is the CLS; the next 196 are patch tokens. The position embedding norms are uniform within a row, which is the sinusoidal signature.

## Use It · 实战用法

同样的图块前端出现在每一个现代视觉-语言模型里：CLIP ViT-L/14、SigLIP、DINOv2、Qwen-VL 系列、InternVL 系列，全部从 `Conv2d` 图块投影加一个位置信号起步。家族之间的差异都在下游（CLS 池化 vs 无 CLS 池化、register token、图块尺寸 14 vs 16、靠插值位置实现的动态分辨率）。本课这个前端，就是上述所有模型脚下共同的基座。

> The same patch front end shows up in every modern vision-language model: CLIP ViT-L/14, SigLIP, DINOv2, the Qwen-VL family, and the InternVL stack all start from a `Conv2d` patch projection plus a position signal. ... The frontend in this lesson is the substrate every one of those models stands on.

## Tests · 测试

`code/test_main.py` 覆盖：

- 图块数量符合 `(image_size / patch_size) ** 2`
- 输出形状符合 `(batch, num_patches + 1, hidden)`
- 在小测试数据上，`Conv2d` 投影与手写「先 unfold 再线性层」结果相等
- 正弦位置表在多次调用间保持确定性
- CLS token 沿 batch 维广播且不泄漏

运行：

```bash
python3 -m unittest code/test_main.py
```

## Exercises · 练习

1. 把正弦位置换成可学习的 `nn.Parameter`，在一个微小的合成分类任务上比较第一个 epoch 的 loss。固定分辨率下可学习位置占优；训练后再改分辨率时正弦位置占优。

2. 把 `Conv2d` 换成显式的 `nn.Unfold` 加 `nn.Linear`，断言两者输出在浮点容差内一致。同一套数学，两种拼法。

3. 增加对非正方形图块尺寸的支持（例如宽幅输入用 32x16），并验证位置表能处理非正方形网格。

4. 在 batch size 为 1、8、64 时对图块这一步做性能分析（profile）。图块投影很少是瓶颈；下游的注意力层才是大头。

5. 把前端当作冻结的特征提取器，在一个 4 类合成形状数据集（圆、方、三角、星）上训练。CLS token 的输出应当能线性分开。

## Key Terms · 术语表

| 术语 | 含义 |
|------|------|
| Patch（图块） | 图像的一个正方形子区域，典型为 14x14 或 16x16 |
| Patch embedding（图块嵌入） | 把展平后的单个图块线性投影到隐藏维度 |
| Sequence length（序列长度） | 图块分词之后的 token 数，通常再加上 CLS |
| Sinusoidal position（正弦位置） | 编码 2D 网格坐标的固定 sin/cos 信号 |
| CLS token | 前置到序列开头、用作池化头的可学习向量 |

## Further Reading · 延伸阅读

- An Image is Worth 16x16 Words（ViT, 2021）——「图块嵌入」这一原始表述的出处。
- Attention Is All You Need（2017）—— 正弦位置公式的出处，本课把它推广到 2D。
- DINOv2 论文 —— register token，这个扩展你可以作为练习 6 加上。
