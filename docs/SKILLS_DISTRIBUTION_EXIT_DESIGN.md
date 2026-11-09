# ATM 剥离 skills 分发（Rust 实现）方案设计

状态：已冻结。决策点确认于 2026-11-09（D1 移除 / D2 不保留 / D3 保留 / D4 清理 /
D5 0.3.0 / D6 收缩），结论记录于 [ADR 0032](adr/0032-atm-exits-skills-distribution.md)。
日期：2026-11-09。

## 1. 背景与动机

- 实际使用结论（用户，2026-11-09）：skills 分发不适合由 GUI 应用控制，纯命令行更合适；
  OMH 恢复独立自主更合理。
- ADR 0031 已经落地了双拥有者世界：ATM Rust 分发器与 OMH standalone Python 分发器
  （`python -m omh {prepare,install,update,uninstall,status,plan,recover}`）各持独立
  receipts 与 `.omh-owner.json` 所有权标记。OMH 1.1.1 起 standalone 分发器与共享运行时
  provider 均已具备完整生命周期（计划/事务/journal/恢复/锁/运行时准备）。
- ATM 同时维护一套 Rust 分发实现（~16,800 行：`distribution/` 六模块 + `skills.rs` +
  `projection.rs` + `harness*.rs`），与 OMH standalone 功能重叠，且其内容契约
  （`content/omh.lock.json`、`harness/` 生成、python-payloads CI）持续产生维护成本。
- 结论方向：ATM 收敛回其核心价值——密钥库、配置**预览与编辑**（批量应用）、额度查询；
  skills/harness 的真实分发与更新一律由 OMH 自己的 CLI 控制。

## 2. 目标与非目标

目标：
- 从 ATM（core/CLI/desktop）移除 skills/harness 分发能力（Rust 实现），保留配置预览与
  编辑、密钥库与额度查询。
- 既有真实 Home（`~/.atm`）按 ADR 0031 交接协议平稳移交 OMH，不产生孤儿状态或双拥有者。
- 发布包、CI、脚本、文档随能力移除同步收缩，不留半实现的死代码。

非目标：
- 不修改 OMH 仓库（其 standalone 分发器已就绪；若发现缺口只记录、另行立项）。
- 不改变 vault 数据格式、密钥/模板/目标契约与额度查询协议（未列入移除面）。
- 不重写或删除历史 ADR、迁移记录与恢复数据（AGENTS.md 义务）。

## 3. 移除面清单（分类：删除 D / 保留 K / 移交 H / 归档 A）

### 3.1 crates/atm-core（Rust 核心）

| 项 | 行数 | 分类 | 说明 |
| --- | --- | --- | --- |
| `src/distribution/`（mod/source/source-hub/service/service-relocation/transaction/adapters/hooks/runtime/legacy） | ~6,545 | D | 整个分发服务：导入、计划、receipts、事务、恢复、运行时协议客户端、legacy 交接 |
| `src/harness.rs` / `harness_machine.rs` / `harness_embed.rs` | ~330 | D | CLI/桌面到分发服务的桥接与嵌入清单 |
| `src/skills.rs` | 879 | D（D1） | skills 盘点/安装/保管区/跨根复制（若 D1 选择保留本地动词则改 K 并裁剪分发路径） |
| `src/projection.rs` | 1,105 | D | 本地投影登记与修复（服务于分发） |
| `src/vault.rs` / `templates.rs` / `batch.rs` / `model.rs` / `jsonc.rs` | — | K | 密钥库、模板、批量预览/应用（"预览和编辑"的本体） |
| `src/storage.rs` / `linux.rs` / `macos.rs` / `windows.rs` / `macos_keychain.rs` | — | K | 安全存储（含新近的 storageReady 探测） |
| `src/usage/` | — | K（D3） | Codex/GLM 额度查询 |
| `src/application/`（configuration 等） | — | K | 快照/保存/回滚服务（裁剪 skills 相关字段） |
| `src/tool_catalog.rs` | 152 | 待查 | 若仅服务 skills 面板则随删；若服务配置工具则保留（实施前核验消费者） |

依赖同步删除：Cargo.toml 中仅被分发使用的依赖（如 OMH runtime 协议、压缩/归档相关）。

### 3.2 CLI（atm-cli）

| 命令组 | 分类 |
| --- | --- |
| `harness bootstrap/sync/adopt/status/recover/migrate/plan/runtime/verify-source/import/fetch/export` | D（`status`/`recover` 的去留见 D2：交接期保留只读 status + 恢复出口，之后删除） |
| `install/uninstall/update/repair/check skills --harness <ID>` | D |
| `uninstall/check hooks --harness codex` | D（skill-watcher 退役诊断随之失去对象） |
| `list/install/uninstall/copy/publish/project/unproject/unpublish/check/update/restore/purge skills`（本地动词） | D（D1） |
| vault/配置/额度相关动词 | K |

### 3.3 桌面应用（apps/desktop）

| 项 | 分类 |
| --- | --- |
| `harness_status/harness_capabilities/harness_diagnose/harness_execute` 命令 + HarnessPanel | D |
| `skills_inventory/install/uninstall/restore/purge/copy` 命令 + SkillsPanel | D（D1） |
| vault 面板（密钥/模板/目标/预览/应用/回滚）、usage 面板、存储连接 | K |
| `main.rs` Service 中分发状态字段、`build.rs` 嵌入清单、capabilities ACL 中 skills/harness 条目 | D |
| smoke-tests 中 GUI 冒烟的分发断言 | 收缩 |

### 3.4 脚本 / CI / 内容契约

| 项 | 分类 |
| --- | --- |
| `scripts/Prepare-Content.py` | D（ATM 不再物化 `harness/`） |
| `content/omh.lock.json` | D（版本钉定职责归还 OMH 仓库自身） |
| `policy/harnesses/registry.json`、`policy/distribution/` | D（目标路径所有权归 OMH；按 identifier-evolution 属持久契约，删除前记录归档位置） |
| `scripts/Package-Release.py` / `Test-Distribution.py` | 改造：包内不再含 `harness/`，分发生命周期断言删除，CLI+desktop+LICENSE/README 保留 |
| CI：`python-payloads` 作业 | D（D4：OMH 内容测试由 OMH 仓库自己的 CI 承担） |
| CI：`cli-only`/`linux-desktop`/`desktop`/`macos-desktop` 中 Prepare-Content 与分发验收步骤 | 收缩（其余检查保留） |
| `scripts/source-manifest.json` | 同步增删 |

### 3.5 文档与 ADR

| 项 | 分类 |
| --- | --- |
| 新增 ADR 0032《ATM 退出 skills 分发，OMH 独立自治》 | 新增 |
| `docs/HARNESS_USAGE.md` | 重写为《分发能力移交 OMH 指南》（交接步骤 + OMH CLI 指引），历史内容归档 |
| ADR 0027/0028/0029/0031、`RUST_MIGRATION.md`、迁移与恢复数据 | A（保留原文，不回写） |
| `AGENTS.md` 中分发相关条目 | 重写（与代码删除同一变更内完成） |

## 4. 真实 Home 与持久契约处置（identifier-evolution 分类）

持久/跨仓身份一律走"显式迁移"类（第二行）处理：

| 状态 | 位置 | 处置 |
| --- | --- | --- |
| 分发 receipts、desiredHarnesses（claude-code/codex @1.1.1 ready） | `~/.atm/state/` | 交接期由 ATM 最后一个含分发版本执行 `uninstall --harness` 完整卸载（ADR 0031 协议），随后 OMH standalone install 接管；卸载后 ATM 侧状态文件保留为历史记录，不删除不改写 |
| `.omh-owner.json` / `.omh-owner.lock`（目标侧） | `~/.codex/`、`~/.claude/` 等 | 随完整卸载由 ATM 摘除；OMH install 时重写 |
| 运行时（`~/.atm/runtimes/`，OMH provider 所建） | ADR 0031 已归 OMH 协议 | 交接演练中按 OMH standalone `prepare`/`recover` 语义处置；不由 ATM 代码路径触碰 |
| 内容缓存 `~/.atm/cache/content/<identity>` | `~/.atm/cache/` | ATM 退出后无消费者；保留至交接完成后清理（显式、单独一步） |
| `relocation.json` 等迁移史 | `~/.atm/state/` | 永久保留（历史证据） |
| `ATM_HOME`、`.atm` 布局、vault 文件格式 | — | 不变（保留面继续使用） |
| `ATM_ENGINE_SOURCE` 语义 | 环境变量 | 随分发删除一并退役；文档记录其历史语义与终止版本 |

回滚：交接在专用演练目录先走一遍完整 卸载→恢复→检查→OMH 安装 流程并留存证据后，
才动真实 Home。代码回滚点 = 分支/PR 边界；真实 Home 回滚点 = 卸载前备份
（沿用 `~/.local/state/atm-deployments/` 交接目录惯例）。

## 5. 移交后的责任边界

- **ATM**：密钥库（创建/编辑/掩码）、配置目标与模板、批量**预览与编辑**（apply/回滚/备份）、
  Codex/GLM 额度查询、演示模式、安全存储连接。发布包 = CLI + desktop（无 payload）。
- **OMH**：内容版本钉定、skills/harness 的安装/更新/卸载/状态/恢复、Python 运行时、
  目标所有权标记；用户经 `python -m omh …` 直接驱动。
- 两者唯一交集：都读/写用户家目录下的目标文件，但**永不同时拥有同一目标**
  （`.omh-owner.json` 单一拥有者原则，ADR 0031 延续）。

## 6. 实施阶段与验证门

| 阶段 | 内容 | 验证门 |
| --- | --- | --- |
| P0 | 本设计决策点全部确认；ADR 0032 定稿（accepted） | 评审通过 |
| P1 | 交接演练：隔离目录完成 ATM 卸载→恢复→检查→OMH standalone 安装→状态核对全链路 | 演练证据存档；OMH 侧 receipts ready |
| P2 | 代码移除（3.1–3.3）+ AGENTS.md/文档重写 + 清单更新，单一 PR | `cargo fmt/clippy/test`（core/cli/desktop）、前端 `check/test/build`、全矩阵 CI 绿 |
| P3 | 脚本/CI/包形态收缩（3.4） | Test-Distribution（收缩版）+ Package-Release 新形态验收通过 |
| P4 | 真实 Home 交接（按 P1 演练步骤）+ 本地安装刷新 + 发布版本 | `~/.atm` 无 ATM 活动 receipts；OMH `status` ready；用户验收 |

P2 与 P3 可并行为两个 PR；P4 必须最后，且要求 P1–P3 全绿。

## 7. 风险与对策

- **交接中断**（卸载后 OMH 安装失败）：ADR 0031 要求卸载即完整恢复 + 目标检查；
  演练目录先验证；真实 Home 有卸载前备份。
- **遗漏消费者**（隐性依赖分发模块）：P2 前用 `cargo -p atm-core --no-default-features
  --all-targets` + 反向依赖 grep 全量核验；`tool_catalog.rs` 等待查项先行确认。
- **CI 断层**（python-payloads 删除后 OMH 测试无家）：D4 先确认 OMH 仓库 CI 覆盖后再删。
- **用户习惯断层**：HARNESS_USAGE 重写版提供逐条命令映射（旧 ATM 命令 → OMH 等价命令）。

## 9. P1 交接演练记录（2026-11-09，隔离目录）

ATM 本地分发工作区与 OMH standalone（74f6145 工作区）在 `/tmp/atm-omh-drill.*`
完成全链路：ATM bootstrap/install（receipt ready）→ uninstall（receipts/desired 清空，
owner 标记摘除；残留空目录与未持锁的 `.omh-owner.lock`，列为真实交接的检查清理项）→
目标检查 → OMH `install`（130 文件、maintenance+workflow 双运行时、owner=omh）→
OMH `status`（零漂移、无需恢复）。

环境结论：`python3`（uv shim）按目录解析不稳定；`/usr/bin/python3` 缺
`python3.14-venv`（ensurepip 不可用）；可靠解释器为绝对路径
`~/.local/share/uv/python/cpython-3.13.15-linux-x86_64-gnu/bin/python3.13`
（真实 Home 现有运行时即由它创建）。P4 必须显式 `--python` 该绝对路径。

## 8. 决策点（需确认后冻结设计）

- **D1 本地 skills 动词**：`list/install/copy` 等本地（非 `--harness`）skills 管理是否
  一并移除？建议：**一并移除**（ATM 彻底聚焦 vault+额度；本地整理用 OMH/文件工具即可）。
- **D2 交接期保留面**：最后一个含分发版本是否保留只读 `harness status` 与 `recover`
  作为交接出口？建议：**保留一个发布周期**（版本 0.3.0），0.4.0 删除。
- **D3 额度查询**：确认保留（与分发无关，GUI/CLI 均留）。默认保留。
- **D4 python-payloads 作业**：确认 OMH 仓库自身 CI 已覆盖其内容测试后再删；未确认前
  该作业保留但改为仅跑锁定内容测试（不做分发验收）。
- **D5 版本与发布**：能力移除从 **0.3.0** 起（语义化：移除公共 CLI 面）。
- **D6 演示模式**：demo 模式随分发断言收缩，仅保留 vault/usage 的演示数据。
