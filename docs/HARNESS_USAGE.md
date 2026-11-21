# Skills 分发移交 OMH：操作手册

ATM 0.3.0 起不再包含 skills/harness 分发（[ADR 0032](adr/0032-atm-exits-skills-distribution.md)）。
本页只保留两件事：OMH standalone 的日常命令，以及把既有 ATM 管理安装移交给 OMH 的交接步骤。
历史工作流（Rust 分发、内容锁、python-payloads CI）见各历史 ADR 与 git 历史，不再复述。

## OMH standalone 日常命令

以下命令以 [OMH v1.3.0](https://github.com/zzzhty/oh-my-harness/releases/tag/v1.3.0) 为准。
需要 Python 3.11 或更新版本；`--home` 默认 `~/.oh-my-harness`，与 ATM 的 `~/.atm` 互不相干。

从可用的 OMH 源码副本执行查询或指定目标操作：

```bash
python3 -B -m omh status
python3 -B -m omh status --harness codex --skills-root "$HOME/.codex/skills"
python3 -B -m omh plan --operation install --harness codex
python3 -B -m omh install --harness codex --python /absolute/python3
python3 -B -m omh refresh --harness codex --python /absolute/python3
python3 -B -m omh uninstall --harness codex
python3 -B -m omh recover --harness codex
```

`status` 不指定路径时列出总览。确认单个安装应传入它的实际 `--skills-root`，
自定义目标在 `plan`、`install`、`refresh`、`uninstall` 和 `recover` 中也应使用同一路径。
上例中的 `/absolute/python3` 应替换为可创建 venv 的实际解释器绝对路径。

升级正式发布应从安装器建立的**托管源码副本**执行（默认 `~/.oh-my-harness/repo`），
或在 POSIX 使用该安装创建的 `omh` 启动器：

```bash
python3 -B -m omh update
python3 -B -m omh update --to v1.3.0
```

`update` 会刷新所有已登记目标，不接受 `--harness` 或 `--python`。
开发副本用 `refresh` 将当前检出的源码重新投影到指定目标，不执行版本升级。

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
python3 -B -m omh install --harness codex --python /absolute/python3
python3 -B -m omh status --harness codex --skills-root "$HOME/.codex/skills"   # 期望 receipt 完整、零漂移
```

隔离目录演练记录（2026-11-09）见
[退出设计 §9](SKILLS_DISTRIBUTION_EXIT_DESIGN.md#9-p1-交接演练记录2026-11-09隔离目录)。
交接后 `~/.atm` 中的历史 receipts/缓存保留为记录，不再被任何在用代码读取。

## 文档回归检查（仅解析参数）

从 ATM 源码仓库运行 `python3 -B scripts/check_omh_examples.py /absolute/path/to/omh-v1.3.0`。
传入 OMH v1.3.0 的源码副本；脚本使用该版本的参数解析器，不执行文档中的命令。
