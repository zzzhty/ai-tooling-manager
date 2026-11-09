# Skills 分发移交 OMH：操作手册

ATM 0.3.0 起不再包含 skills/harness 分发（[ADR 0032](adr/0032-atm-exits-skills-distribution.md)）。
本页只保留两件事：OMH standalone 的日常命令，以及把既有 ATM 管理安装移交给 OMH 的交接步骤。
历史工作流（Rust 分发、内容锁、python-payloads CI）见各历史 ADR 与 git 历史，不再复述。

## OMH standalone 日常命令

在 OMH 仓库（`oh-my-harness`）内运行；`--home` 默认 `~/.oh-my-harness`，与 ATM 的
`~/.atm` 互不相干：

```bash
python3 -m omh status --harness codex
python3 -m omh plan install --harness codex
python3 -m omh install --harness codex --python /absolute/python3
python3 -m omh update --harness codex --python /absolute/python3
python3 -m omh uninstall --harness codex
python3 -m omh recover --harness codex
```

**解释器要求（实测）**：必须显式 `--python` 指向可创建 venv 的解释器绝对路径。
本机可靠选择是 uv 管理的 CPython
（`~/.local/share/uv/python/cpython-3.13.15-linux-x86_64-gnu/bin/python3.13`）；
`python3` shim 按目录解析不稳定，`/usr/bin/python3` 缺 `python3.14-venv`（ensurepip 不可用）。

## 从 ATM 管理安装交接（一次性）

按 [ADR 0031](adr/0031-omh-owned-runtime-and-independent-distribution.md) 的单目标单
owner 协议执行。ATM 0.3.0 前的发布包仍含 `atm` CLI，先用它完成卸载：

```bash
# 1) 用旧版 ATM CLI 完整卸载其管理的分发（对每个已安装 harness）
atm uninstall skills --harness codex
atm uninstall skills --harness claude-code

# 2) 检查目标：owner 标记（.omh-owner.json）应消失；残留空目录与
#    未持锁的 .omh-owner.lock 可手动清理（flock 锁文件无害）

# 3) OMH 接管安装
python3 -m omh install --harness codex --python <可靠解释器绝对路径>
python3 -m omh status --harness codex   # 期望 receipt 完整、零漂移
```

隔离目录演练记录（2026-11-09）见
[退出设计 §9](SKILLS_DISTRIBUTION_EXIT_DESIGN.md#9-p1-交接演练记录2026-11-09隔离目录)。
交接后 `~/.atm` 中的历史 receipts/缓存保留为记录，不再被任何在用代码读取。
