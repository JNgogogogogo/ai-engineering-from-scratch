"""Dockerfile 分层分析与镜像体积估算 —— 0/07 Docker for AI 配套脚本。

Lesson: phases/00-setup-and-tooling/07-docker-for-ai/docs/en.md
Learner artifact: 把「Dockerfile 每一层是什么、改哪层会导致重建」变成可读的表。
纯标准库，不需要 docker daemon 运行（daemon 没起也能用）。

运行：
    uv run python learning-artifacts/phase0/dockerfile_layer_analyzer.py <Dockerfile 路径>
    # 不带参数则分析课程自带的 Dockerfile
"""

import re
import sys
from pathlib import Path

# 常见包的近似体积（MB）。用于估算，不是精确值。
#
# ⚠️ 精度说明：这里只给「量级」，用来比较层之间谁贵，不用于预测最终镜像大小。
#   ·CPU 版 torch 实际约 200 MB，但表里按 2500 MB 算（跟CUDA 版同值）——
#     所以「CPU 版镜像更小」这个结论成立，但这张表证明不了
#   · 不同平台的 wheel 大小差异很大（x86_64 vs arm64）
#   · 唯一准确的数字是 docker images 报出来的 SIZE
#   · 想要真值：docker build 后跑 docker history <image> 看每层真实大小
PKG_SIZE = {
    # CUDA / 深度学习框架（torch 同值，实际 CPU 版约 200 MB）
    "torch": 2500, "torchvision": 70, "torchaudio": 40,
    "tensorflow": 600, "jax": 80, "jaxlib": 80,
    "pytorch": 2500, "cudnn": 800,
    # 科学计算
    "numpy": 40, "scipy": 35, "pandas": 60, "scikit-learn": 35,
    "polars": 30, "sympy": 10,
    # 可视化
    "matplotlib": 35, "seaborn": 3, "plotly": 15, "bokeh": 15,
    # AI 生态
    "transformers": 20, "datasets": 15, "accelerate": 10,
    "safetensors": 5, "tokenizers": 10, "huggingface-hub": 5,
    "peft": 10, "bitsandbytes": 90, "flash-attn": 120,
    "sentencepiece": 8, "einops": 1,
    # Notebook
    "jupyter": 30, "jupyterlab": 400, "notebook": 40,
    "ipython": 12, "ipykernel": 12, "ipywidgets": 8,
    # 构建工具
    "build-essential": 200, "curl": 5, "git": 30, "wget": 4,
    "software-properties-common": 20, "ca-certificates": 1,
    # 常见 API / 工具
    "openai": 3, "anthropic": 1, "httpx": 2, "requests": 1,
    "pydantic": 5, "fastapi": 3, "uvicorn": 2, "flask": 2,
    "qdrant-client": 3, "chromadb": 60, "sentence-transformers": 30,
}

# 基础镜像体积（MB）
BASE_SIZE = {
    "nvidia/cuda": 1500,          # runtime 变体
    "pytorch/pytorch": 6000,
    "python:3.12-slim": 150,
    "python:3.12": 1000,
    "ubuntu": 80,
    "debian": 75,
}

RE_FROM = re.compile(r"^\s*FROM\s+(--platform=\S+\s+)?(\S+)", re.I)
RE_RUN = re.compile(r"^\s*RUN\s+(.*)", re.I | re.S)
# 注意：不能加 ^ 行首锚点。Dockerfile 的续行合并后，所有包名都在同一行的中间，
# `torch==2.6.0+cu124` 前面还有别的包，用 ^ 会一个都匹配不到。
RE_PKG = re.compile(r"([A-Za-z0-9_.\-]+)(?:\[[^\]]*\])?\s*[=<>~!]")
RE_CMD = re.compile(r"^\s*CMD\s+", re.I)


def parse_layers(text):
    """把 Dockerfile 拆成层。支持续行（行尾反斜杠）。

    关键：先把续行合并成「逻辑行」，再解析。否则一条跨 10 行的 RUN 会被
    拆成 10 个独立条目，后9 行因匹配不到 RUN/CMD 等关键字而被静默丢弃
    （这个 bug 让 torch 层的 2.6 GB 估成了 0）。
    """
    lines = text.split("\n")
    logical, buf = [], ""
    for raw in lines:
        s = raw.rstrip()
        stripped = s.strip()
        if not buf:
            # 顶层注释与空行直接跳过（但续行中间不能跳）
            if not stripped or stripped.startswith("#"):
                continue
        if s.endswith("\\"):
            buf += s[:-1] + " "
            continue
        logical.append((buf + s).strip())
        buf = ""
    if buf.strip():
        logical.append(buf.strip())

    layers, cur_run = [], None
    for ln in logical:
        m = RE_FROM.match(ln)
        if m:
            layers.append({"kind": "FROM", "raw": ln, "platform": m.group(1),
                           "image": m.group(2)})
            continue
        m = RE_RUN.match(ln)
        if m:
            if cur_run:
                layers.append(cur_run)
            cur_run = {"kind": "RUN", "raw": m.group(1)}
            continue
        op = ln.split()[0].upper() if ln.split() else ""
        if op in {"ENV", "WORKDIR", "CMD", "EXPOSE", "VOLUME", "COPY", "ADD",
                  "ENTRYPOINT", "ARG", "LABEL", "USER", "SHELL", "HEALTHCHECK"}:
            if cur_run:
                layers.append(cur_run); cur_run = None
            layers.append({"kind": op, "raw": ln})
        elif cur_run:
            # 续行的后续部分，补进当前 RUN
            cur_run["raw"] += " " + ln
    if cur_run:
        layers.append(cur_run)
    return layers


def pkgs_in(text):
    """列出这一层涉及的已知包名。

    两路配合，因为包名在续行合并后形态不统一：
      ·带版本约束的 `torch==2.6.0+cu124` → 正则抓「名字+版本符号」
      · 完全裸的 `numpy pandas` → 靠 pip install 段落按空白分词
    踩过的坑：正则加 ^ 行首锚点会一个都匹配不到（续行合并后包名在行中间）。
    """
    found = {m.group(1).lower() for m in RE_PKG.finditer(text)}
    found = {n for n in found if n in PKG_SIZE}

    # 裸包名路径：只在 pip install 段落里找
    if "pip install" in text:
        body = text.split("pip install", 1)[1]
        body = re.split(r"--index-url|-i\s+\S+|&&|\|\||;", body)[0]
        for tok in body.replace("\\", " ").split():
            name = tok.split("[")[0].split("=")[0].split("<")[0] \
                   .split(">")[0].split("!")[0].split("~")[0].lower()
            if name in PKG_SIZE:
                found.add(name)
    return sorted(found)


def estimate(layers):
    total = 0
    rows = []
    for i, l in enumerate(layers, 1):
        size, note = 0, ""
        if l["kind"] == "FROM":
            img = l["image"]
            size = next((v for k, v in BASE_SIZE.items() if k in img), 800)
            variant = "devel" if "devel" in img else ("runtime" if "runtime" in img else "")
            note = f"基础镜像{('（' + variant + ' 变体）') if variant else ''}"
        elif l["kind"] == "RUN":
            ps = pkgs_in(l["raw"])
            if ps:
                size = sum(PKG_SIZE[p] for p in ps)
                note = f"{len(ps)} 个包: {', '.join(ps[:4])}"
                if len(ps) > 4:
                    note += f" 等"
            if "--no-cache-dir" in l["raw"] or "rm -rf" in l["raw"]:
                note += "（已清缓存）"
        rows.append((i, l, size, note))
        total += size
    return rows, total


def main():
    default = ("phases/00-setup-and-tooling/07-docker-for-ai/code/Dockerfile")
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(default)
    if not path.exists():
        print(f"找不到 {path}")
        return

    layers = parse_layers(path.read_text())
    rows, total = estimate(layers)

    print("=" * 78)
    print(f"Dockerfile 分层分析：{path}")
    print("=" * 78)
    print(f"{'#':>3}  {'类型':<10} {'估体积':>10}  说明")
    print("-" * 78)
    for i, l, size, note in rows:
        raw = l["raw"].replace("\n", " ")
        raw = re.sub(r"\s+", " ", raw)
        kind = l["kind"]
        head = raw if kind in {"ENV", "WORKDIR", "CMD", "EXPOSE", "VOLUME"} else f"{kind}: {raw[:40]}"
        print(f"{i:>3}  {kind:<10} {size:>7} MB  {note or head[:46]}")
    print("-" * 78)
    print(f"{'合计':>14}{total:>7} MB  （估算，实际以 docker images 为准）")
    print()

    # 最贵的一层
    worst = max(rows, key=lambda r: r[2])
    print(f"最贵的一层：第 {worst[0]} 层 {worst[1]['kind']} —— {worst[2]} MB")
    print()

    # 缓存失效影响
    print("=" * 78)
    print("改哪一层会导致重建多少")
    print("=" * 78)
    for i, l, size, _ in rows:
        if l["kind"] not in {"RUN", "COPY", "ADD"}:
            continue
        after = sum(s for _, _, s, _ in rows[i - 1:])
        print(f"  改第 {i:>2} 层（{l['kind']:<5}）→ 需重建第 {i}~{len(rows)} 层，"
              f"合计 ~{after} MB")
    print()
    print("  提示：把变化最频繁的指令（如拷代码）放最后，重建范围最小。")
    print("       本课 Dockerfile 把 torch 装在倒数第二层就是这个道理。")

    # 平台诊断
    from_layer = next((l for l in layers if l["kind"] == "FROM"), None)
    if from_layer:
        print()
        print("=" * 78)
        print("平台与 GPU 诊断")
        print("=" * 78)
        if from_layer.get("platform"):
            print(f"  已固定平台：{from_layer['platform'].strip()}")
            print("  → Apple Silicon 上构建会成功（走 x86_64 模拟）")
            print("  → 但容器内没有 GPU，macOS 本来就没有 CUDA")
        else:
            print("  未固定平台 —— Apple Silicon 上装 cu124 版 torch 会失败")
            print("  → PyTorch 的 cu124 wheel 只发 x86_64，没有 arm64")
        if "--gpus" in path.read_text() or "--gpus" in str(path.parent / "docker-compose.yml"):
            print("  检测到 --gpus all：NVIDIA GPU 专用，Mac 上要去掉")

    # 反模式扫描
    print()
    print("=" * 78)
    print("反模式扫描")
    print("=" * 78)
    text = path.read_text()
    # 全局关缓存的两种等价写法：ENV PIP_NO_CACHE_DIR=1 或命令行 --no-cache-dir。
    # 只查命令行会漏掉前者，所以要先看 ENV。
    # 注意 ENV 可能是续行多行写的，要扫整个文件而不是只扫单行。
    env_no_cache = bool(re.search(r"PIP_NO_CACHE_DIR\s*=\s*[\"']?1", text))

    issues = []
    for l in [x for x in layers if x["kind"] == "RUN"]:
        raw = l["raw"]
        if "apt-get update" in raw and "apt-get install" not in raw:
            issues.append((l, "apt-get update 单独成层 → 下面的 install 会命中过期索引，"
                              "应合并成一条 RUN"))
        if "pip install" in raw and "--no-cache-dir" not in raw and not env_no_cache:
            issues.append((l, "pip install 缺 --no-cache-dir，且未设 ENV PIP_NO_CACHE_DIR=1"
                              " → pip 缓存会固化进这一层，重建时全部重下"))
        if "ADD http" in raw:
            issues.append((l, "ADD 远程 URL 不校验哈希；建议改 curl + sha256sum -c"))
        if "latest" in raw:
            issues.append((l, "用了 :latest 标签 → 不可复现"))

    if env_no_cache:
        print("  [全局] ENV PIP_NO_CACHE_DIR=1  → 等价于每层加 --no-cache-dir，检查通过")
    if issues:
        for l, msg in issues:
            first = l["raw"].replace("\n", " ")[:52]
            print(f"  [RUN] {first}")
            print(f"         → {msg}")
    else:
        print("  没扫到常见问题")

    # --- 未钉版本的包，逐个列出（区分「该钉」与「本就该取最新」）---
    print()
    print("=" * 78)
    print("依赖版本钉死情况")
    print("=" * 78)
    # pip / setuptools / wheel 是构建工具，取最新版是合理的
    TOOLS = {"pip", "setuptools", "wheel"}
    loose = []
    for l in layers:
        if l["kind"] != "RUN" or "pip install" not in l["raw"]:
            continue
        # 拆出 pip install 的包列表（去掉 index-url 等选项）
        body = l["raw"].split("pip install", 1)[1]
        body = re.split(r"--index-url|-i\s+\S+", body)[0]
        for tok in body.replace("\\", " ").split():
            m = re.match(r"^([A-Za-z0-9_.\-]+)(\[[^\]]*\])?([=<>~!].*)?$", tok)
            if not m:
                continue
            name = m.group(1).lower()
            ver = m.group(3)
            if name in TOOLS:
                continue
            if ver:
                if not re.search(r"[=<>~!]=\d", ver):
                    loose.append((name, ver.strip(), "用了范围约束但无下限"))
            elif name in PKG_SIZE:
                loose.append((name, None, "完全没写版本"))
    if loose:
        seen = set()
        for name, ver, why in loose:
            if name in seen:
                continue
            seen.add(name)
            print(f"  {name:<16s} {ver or '(无)':<14s} {why}")
        print()
        print("  影响：镜像重建时可能拿到不同的包，行为不可复现。")
        print("  建议：钉到次版本（numpy==2.2.6），或提交 lockfile 用 requirements.lock。")
    else:
        print("  ✅ 所有包都钉了精确版本")

    print()
    print("=" * 78)
    print("供应链安全检查")
    print("=" * 78)
    # 只扫实际指令，剥掉注释行。否则「# 绝不 curl | bash」这句注释
    # 会被当成真的管道执行而误报。
    code = "\n".join(l for l in text.split("\n") if not l.lstrip().startswith("#"))
    if re.search(r"\|\s*(?:sudo\s+)?(?:ba|z|k|da)?sh\b", code):
        print("  ⚠️  有 curl ... | bash 管道执行 —— 中间人改脚本就会被直接执行")
        print("     应改成：curl -o /tmp/x && sha256sum -c && 执行")
    else:
        print("  ✅ 没有裸管道执行 shell 的写法")
    if "sha256sum -c" in code:
        print("  ✅ 有 sha256 校验（下载→校验→执行 三步分开）")
    if re.search(r"FROM\s+\S+:latest", code):
        print("  ⚠️  FROM 用了 :latest —— 上游一更新你的构建就变了")
    else:
        print("  ✅ FROM钉了具体版本")
    if re.search(r"[=<>~!]=\d", code):
        print("  ✅ 关键依赖钉了精确版本")
    else:
        print("  ⚠️  没有钉任何精确版本")


if __name__ == "__main__":
    main()