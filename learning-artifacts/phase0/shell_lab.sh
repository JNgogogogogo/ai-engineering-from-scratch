#!/usr/bin/env bash
# 0/10 终端与 Shell 实测台：管道/重定向/进程控制/别名脚本跨平台坑
# 课程文档: phases/00-setup-and-tooling/10-terminal-and-shell/docs/en.md
# 运行: bash learning-artifacts/phase0/shell_lab.sh

set -u
LAB=/tmp/shell_lab
rm -rf "$LAB"; mkdir -p "$LAB"; cd "$LAB"

echo "=== 0. 环境事实 ==="
echo "SHELL=$SHELL"
for c in tmux htop watch nvtop nvidia-smi bc rsync; do
    if command -v "$c" >/dev/null 2>&1; then echo "  $c: $(command -v $c)"; else echo "  $c: 未安装"; fi
done

echo ""
echo "=== 1. 造假训练日志（1000 epoch，loss=1/i） ==="
for i in $(seq 1 1000); do
    echo "epoch $i loss: $(echo "scale=4; 1/$i" | bc)"
done > train.log
echo "  行数: $(wc -l < train.log | tr -d ' ')"; echo "  首行: $(head -1 train.log)"

echo ""
echo "=== 2. 管道三连 grep | awk | wc ==="
n=$(grep "loss:" train.log | awk '{print $NF}' | wc -l | tr -d ' ')
echo "  loss 值条数: ${n}  (课文练习 3 的套路, awk 的 NF = 最后一个字段)"
last=$(grep "loss:" train.log | awk '{print $NF}' | tail -1)
echo "  最终 loss: $last"
t0=$(date +%s%N 2>/dev/null || python3 -c 'import time;print(time.time_ns())')
grep "loss:" train.log | awk '{print $NF}' > losses.txt
t1=$(date +%s%N 2>/dev/null || python3 -c 'import time;print(time.time_ns())')
echo "  提取 1000 条到 losses.txt 耗时: $(( (t1 - t0) / 1000000 )) ms"

echo ""
echo "=== 3. 重定向：stdout/stderr 分离 + 顺序陷阱 ==="
cat > noisy.py <<'EOF'
import sys
print("stdout: training epoch 1")
print("stderr: WARNING: learning rate too high", file=sys.stderr)
EOF
PY="$(command -v python3)"
"$PY" noisy.py > out.log 2> err.log
echo "  [> out 2> err] out.log: $(cat out.log)"
echo "  [> out 2> err] err.log: $(cat err.log)"
echo "  --- 顺序陷阱：2>&1 放前面 ---"
"$PY" noisy.py 2>&1 > wrong.log 2>/dev/null
echo "  [2>&1 > f] wrong.log 只有: $(cat wrong.log)   ← stderr 从未进文件"
"$PY" noisy.py > right.log 2>&1
echo "  [> f 2>&1] right.log 有 $(wc -l < right.log | tr -d ' ') 行（stdout+stderr 都在）"

echo ""
echo "=== 4. 进程替换 diff <(...) <(...) ==="
head -500 train.log > exp1.log; tail -500 train.log > exp2.log
d=$(diff <(grep "loss:" exp1.log) <(grep "loss:" exp2.log) | wc -l | tr -d ' ')
echo "  两组实验日志的 loss 行 diff 行数: $d"

echo ""
echo "=== 5. 后台任务 jobs / kill ==="
sleep 30 &
sleep 0.2
echo "  jobs 输出: $(jobs)"
kill %1 2>/dev/null && echo "  kill %1 成功（30 秒的 sleep 秒死）"
wait 2>/dev/null
nohup sleep 1 >/dev/null 2>&1 &
echo "  nohup sleep 1 已脱离会话启动 (pid $!)"

echo ""
echo "=== 6. memhogs 别名在 macOS 的 bug ==="
out=$(ps aux --sort=-%mem 2>/dev/null | head -11)
if [ -z "$out" ]; then
    echo "  课文 memhogs: ps aux --sort=-%mem | head → 空输出！"
    echo "  原因: BSD ps 不认 --sort（GNU 专用）；报错被 2>/dev/null 吞掉，"
    echo "        管道退出码取 head 的 0，|| 后备分支永不触发。"
fi
echo "  macOS 正确写法 ps aux -m | head -3:"
ps aux -m | head -3 | sed 's/^/    /'

echo ""
echo "=== 7. BSD 工具链兼容性 ==="
hs=$(printf "1.5K\n2M\n900\n" | sort -rh | head -1)
echo "  sort -rh: $hs $([ "$hs" = "2M" ] && echo '（支持 human 可排序）' || echo '（不支持！）')"
if echo hi | grep --line-buffered hi >/dev/null 2>&1; then
    echo "  grep --line-buffered: 支持（watchloss 别名可用）"
else
    echo "  grep --line-buffered: 不支持"
fi

echo ""
echo "=== 8. 磁盘账 ==="
df -h / | tail -1 | awk '{print "  根卷剩余: "$4" / "$2}'
du -sh "$HOME/.cache/huggingface/datasets" 2>/dev/null | sed 's/^/  HF datasets 缓存: /'
du -sh "$HOME/Documents/WKS/agent/ai-engineering-from-scratch/.venv" 2>/dev/null | sed 's/^/  .venv: /'

echo ""
echo "完成。产物目录: $LAB"
