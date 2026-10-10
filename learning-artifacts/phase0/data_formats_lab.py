# 数据管理实测台：格式体积/读写速度对比、划分可复现性、课文 Step 5 划分数学核对
# 课程文档: phases/00-setup-and-tooling/09-data-management/docs/en.md
# 本机: M5 Pro / .venv (uv 创建，无 pip) — 运行: .venv/bin/python data_formats_lab.py

import os
import random
import time
from pathlib import Path

import numpy as np
from datasets import Dataset
import pandas as pd

OUT = Path("/tmp/data_formats_lab")
OUT.mkdir(parents=True, exist_ok=True)

WORDS = ("the model learns from data gradients flow through layers attention weights "
         "training loss decreases validation set checks progress test set final score "
         "embeddings tokens batches epochs learning rate optimizer state checkpoints").split()


def build_dataset(n_rows: int = 20000, seed: int = 0) -> Dataset:
    rng = np.random.default_rng(seed)
    texts = [" ".join(rng.choice(WORDS, size=rng.integers(40, 80))) for _ in range(n_rows)]
    return Dataset.from_dict({
        "id": list(range(n_rows)),
        "text": texts,
        "label": rng.integers(0, 2, n_rows).tolist(),
        "score": rng.random(n_rows).round(4).tolist(),
    })


def bench_formats(ds: Dataset) -> None:
    print("\n=== 1. 格式体积与读写速度（%d 行） ===" % len(ds))
    rows = []
    targets = [
        ("csv", lambda p: ds.to_csv(p), lambda p: Dataset.from_csv(p), lambda p: pd.read_csv(p)),
        ("json", lambda p: ds.to_json(p), lambda p: Dataset.from_json(p), lambda p: pd.read_json(p, lines=True)),
        ("parquet", lambda p: ds.to_parquet(p), lambda p: Dataset.from_parquet(p), lambda p: pd.read_parquet(p)),
    ]
    for name, write, read_ds, read_pd in targets:
        path = OUT / f"lab.{name}"
        t0 = time.perf_counter()
        write(str(path))
        t_write = time.perf_counter() - t0
        size = path.stat().st_size

        t0 = time.perf_counter()
        r1 = read_ds(str(path))
        t_ds = time.perf_counter() - t0

        t0 = time.perf_counter()
        r2 = read_pd(str(path))
        t_pd = time.perf_counter() - t0
        assert len(r1) == len(ds) == len(r2)
        rows.append((name, size, t_write, t_ds, t_pd))

    arrow_dir = OUT / "lab.arrow"
    t0 = time.perf_counter()
    ds.save_to_disk(str(arrow_dir))
    t_write = time.perf_counter() - t0
    size = sum(f.stat().st_size for f in arrow_dir.rglob("*") if f.is_file())
    t0 = time.perf_counter()
    r3 = Dataset.load_from_disk(str(arrow_dir))
    t_ds = time.perf_counter() - t0
    assert len(r3) == len(ds)
    rows.append(("arrow(save_to_disk)", size, t_write, t_ds, float("nan")))

    base = rows[0][1]
    print(f"{'格式':<20}{'体积':>12}{'vs CSV':>9}{'写入 s':>9}{'datasets读 s':>13}{'pandas读 s':>12}")
    for name, size, t_write, t_ds, t_pd in rows:
        ratio = base / size
        pd_s = f"{t_pd:.3f}" if t_pd == t_pd else "—"
        print(f"{name:<20}{size:>10,}B{ratio:>8.1f}x{t_write:>9.3f}{t_ds:>13.3f}{pd_s:>12}")


def bench_splits(ds: Dataset) -> None:
    print("\n=== 2. 划分可复现性（seed） ===")
    a = ds.train_test_split(test_size=0.2, seed=42)
    b = ds.train_test_split(test_size=0.2, seed=42)
    c = ds.train_test_split(test_size=0.2, seed=7)
    d1 = ds.train_test_split(test_size=0.2)
    d2 = ds.train_test_split(test_size=0.2)
    same_seed_same = a["test"]["id"] == b["test"]["id"]
    diff_seed_same = a["test"]["id"] == c["test"]["id"]
    overlap = len(set(a["test"]["id"]) & set(c["test"]["id"])) / len(a["test"])
    no_seed_same = d1["test"]["id"] == d2["test"]["id"]
    print(f"  同 seed=42 两次 -> 完全一致: {same_seed_same}")
    print(f"  seed=42 vs 7   -> 完全一致: {diff_seed_same}（id 重合率 {overlap:.1%}，约等于随机重合 20%）")
    print(f"  不设 seed 两次 -> 完全一致: {no_seed_same}")

    print("\n=== 3. 划分数学核对：课文 Step 5 vs data_utils.make_splits ===")
    n = len(ds)
    sp = ds.train_test_split(test_size=0.2, seed=42)
    tv = sp["train"].train_test_split(test_size=0.125, seed=42)
    tr, va, te = len(tv["train"]), len(tv["test"]), len(sp["test"])
    print(f"  课文 Step 5 代码：train {tr} ({tr/n:.0%}) / val {va} ({va/n:.0%}) / test {te} ({te/n:.0%})")
    print(f"  课文文字声称：   train 80% / val 10% / test 10%   <-- 不一致！")
    sp1 = ds.train_test_split(test_size=0.2, seed=42)
    frac = 0.1 / 0.2
    sp2 = sp1["test"].train_test_split(test_size=1.0 - frac, seed=42)
    tr, va, te = len(sp1["train"]), len(sp2["train"]), len(sp2["test"])
    print(f"  data_utils.py：  train {tr} ({tr/n:.0%}) / val {va} ({va/n:.0%}) / test {te} ({te/n:.0%})  <-- 与文字一致")

    print("\n=== 4. 练习 4 的 70/15/15 ===")
    s1 = ds.train_test_split(test_size=0.3, seed=42)
    s2 = s1["test"].train_test_split(test_size=0.5, seed=42)
    tr, va, te = len(s1["train"]), len(s2["train"]), len(s2["test"])
    print(f"  train {tr} ({tr/n:.0%}) / val {va} ({va/n:.0%}) / test {te} ({te/n:.0%})")


def bench_network() -> None:
    print("\n=== 5. Hugging Face 网络实测（10 秒超时） ===")
    import socket
    socket.setdefaulttimeout(10)
    for endpoint, tag in ((os.environ.get("HF_ENDPOINT", "https://huggingface.co"), "huggingface.co"),
                          ("https://hf-mirror.com", "hf-mirror.com")):
        try:
            os.environ["HF_ENDPOINT"] = endpoint
            from datasets import load_dataset
            ds = load_dataset("lhoestq/demo1", split="train")
            print(f"  {tag}: OK，{len(ds)} 行，列={ds.column_names}")
            return
        except Exception as e:
            print(f"  {tag}: FAIL（{type(e).__name__}: {str(e)[:80]}）")


def bench_cache() -> None:
    print("\n=== 6. HF 缓存目录 ===")
    for sub in ("datasets", "hub", "xet"):
        p = Path.home() / ".cache" / "huggingface" / sub
        if not p.exists():
            print(f"  {sub}: 不存在")
            continue
        files = [f for f in p.rglob("*") if f.is_file()]
        total = sum(f.stat().st_size for f in files)
        print(f"  {sub}: {len(files)} 个文件，{total/1024/1024:.1f} MB")


if __name__ == "__main__":
    random.seed(0)
    ds = build_dataset()
    print(f"合成数据集：{len(ds)} 行 x {len(ds.column_names)} 列（id/text/label/score）")
    bench_formats(ds)
    bench_splits(ds)
    bench_network()
    bench_cache()
    print("\n完成。产物目录:", OUT)
