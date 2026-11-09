# ADR 0032: ATM 退出 skills 分发，OMH 独立自治

Status: accepted, 2026-11-09. 设计与决策记录见
[SKILLS_DISTRIBUTION_EXIT_DESIGN.md](../SKILLS_DISTRIBUTION_EXIT_DESIGN.md)。

## Context

ATM 的 Rust 分发实现（distribution/service、skills、projection、harness 桥接，约
16,800 行）与 OMH 1.1.1 起的 standalone 分发器（ADR 0031）功能重叠。实际使用表明
skills 分发由 GUI 应用控制不合适，纯命令行（OMH 自身）更合适。

## Decision

ATM 移除全部 skills/harness 分发能力（Rust 实现、CLI 动词、桌面命令与面板、内容
锁与 payload 生成、python-payloads CI 作业），保留密钥库、配置目标/模板与批量
预览编辑（apply/回滚/备份）、Codex/GLM 额度查询、演示模式（仅 vault/usage 数据）
与安全存储连接。真实分发与更新由 OMH standalone CLI 独立控制。

确认的决策点：

- D1 本地 skills 动词一并移除（`list/install/copy` 等全部）。
- D2 不保留交接期出口：`harness status`/`recover` 随其余分发面一次性删除，
  不设只读过渡版本。
- D3 额度查询保留（CLI 与桌面均保留）。
- D4 `python-payloads` CI 作业删除；OMH 内容测试归 OMH 仓库自身 CI。
- D5 能力移除自版本 0.3.0 生效。
- D6 演示模式仅保留 vault/usage 演示数据。

## Consequences

- 发布包不再内嵌 `harness/`；`content/omh.lock.json`、`policy/harnesses/registry.json`、
  `policy/distribution/`、`scripts/Prepare-Content.py` 删除；Package/Test 脚本收缩。
- 真实 Home 交接严格按 ADR 0031 协议执行：ATM 完整卸载 → 恢复 → 目标检查 →
  OMH standalone 安装；先在隔离演练目录验证全链路，代码移除合入并全绿后才动真实
  `~/.atm`。历史 ADR、迁移与恢复记录永久保留。
- `ATM_ENGINE_SOURCE` 语义随分发退役；文档记录终止版本。
- ADR 0027/0028/0029/0031 中由 ATM 持有的分发职责自 0.3.0 起失效，原文不改写；
  本 ADR 为其现状结论。
