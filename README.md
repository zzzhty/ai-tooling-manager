# AI Tooling Manager（ATM）

本地 AI 工具管理器：Rust / Tauri，Linux、Windows 与 macOS；平台验证范围见下文。

中文单窗口工具，为本地 AI 编码工具保管凭据与配置：用命名密钥库管理 key，按用户手动注册的文件和精确字段批量更新 JSON/JSONC 配置。可用于 Z.ai 的 Z Code、VS Code、Visual Studio 等工具，但不假定它们共用一个 key 或固定的配置位置。

本任务的开发、测试、演示和 GUI 冒烟仅使用假 key 与隔离合成配置。没有读取、修改或备份用户现有应用配置；真实密钥应由用户亲自在工具中输入、预览并应用。

## Codex / GLM 额度查询与 Linux 安全存储

应用内置 Codex / GLM 主动额度查询界面：默认不做后台轮询，查不到或无权限的值保持未知，不虚构进度条。Linux 端使用 Secret Service + AES-GCM 安全存储、加密备份和受控文件更新；首次连接会在会话 keyring 中创建本应用专用的随机主密钥。行为、协议来源、支持边界与复现入口见 [本地实现与验证记录](docs/CODEX_GLM_LINUX.md)。

## Skills / harness 分发已移交 OMH（0.3.0 起）

按 [ADR 0032](docs/adr/0032-atm-exits-skills-distribution.md)，ATM 自 0.3.0 起不再包含
skills/harness 分发能力（Rust 实现、CLI、桌面面板与内容锁均已移除）。skills 的安装、
更新、卸载与恢复由 OMH standalone CLI 独立负责：

```bash
python3 -m omh {prepare,install,update,uninstall,status,plan,recover} --harness codex|claude-code
```

真实安装的交接遵循 [ADR 0031](docs/adr/0031-omh-owned-runtime-and-independent-distribution.md)
的单目标单 owner 协议（现任拥有者完整卸载 → 恢复检查 → OMH 安装）；操作手册见
[移交指南](docs/HARNESS_USAGE.md)。历史设计、迁移与恢复记录保留在对应 ADR 与
[退出设计](docs/SKILLS_DISTRIBUTION_EXIT_DESIGN.md)。

## 构建与验证

macOS 使用 Keychain + AES-GCM 和 Application Support 数据目录。合成测试与 `--demo` 注入内存密钥，不访问真实 Keychain。使用已有工具链运行 `scripts/Verify-MacOS.sh`，只构建原生测试可执行文件并受控启动隔离 GUI；不签名发布、安装或迁移用户数据。参见 [macOS 支持说明](docs/MACOS.md)。

依赖 Rust stable（Windows 需 MSVC）、Node 22 与各平台 Tauri 系统依赖（Windows 需 WebView2；Linux 需 D-Bus/GTK/WebKitGTK 开发库）。从仓库根目录运行：

```powershell
# Windows
npm ci
npm run check
npm test
npm run build
cargo fmt --all --check
cargo clippy -p atm-core --all-targets -- -D warnings
cargo test -p atm-core
npm run tauri:build
# 仅创建新的假数据目录，不打开默认真实密钥库
.\target\release\atm-desktop.exe --demo
.\scripts\Test-TauriGui.ps1
```

```bash
# Linux（离线、隔离缓存的全量本地验证）
./scripts/Verify-Local.sh
# 私有 keyring 和原生 GUI 另按验收矩阵的 CI 隔离前置条件执行
```

- 库格式：Windows 使用 DPAPI CurrentUser 的 `vault.dpapi` / `templates.dpapi`；Linux 使用 Secret Service 主密钥 + AES-GCM 的 `vault.atmvault` / `templates.atmvault`。加密备份统一为 `.atmbackup`。
- JSON/JSONC 更新只替换已注册、已存在的字符串叶节点源字节。模板增加字段白名单和完整待写配置的本地 schema 验证，不创建文件、补齐字段、重排对象或重新序列化整份配置。
- 候选模板从用户明确选择的单个配置中提取类型、结构和字段位置，保存前须确认。样本标量值不进入模板；属性名、JSON Pointer 和文件名提示仍会保留，请检查这些名称本身是否含敏感信息。没有官方应用预设，也不自动发现配置。
- Schema 限定为明确声明的 JSON Schema 2020-12 **受限本地子集**；不支持的约束、其他方言、外部引用和循环引用会被拒绝。不能把本实现称为支持任意 JSON Schema。完整范围、回退注意事项见 [Rust 迁移说明](docs/RUST_MIGRATION.md)。
- 整文件回滚恢复历史原字节，不按当前模板 schema 重写或过滤；确认页会明确此范围，仍拒绝覆盖后续编辑。
- `.github/workflows/rust-ci.yml` 包含 Rust、前端、Windows Tauri 构建、隔离真实 Secret Service 生命周期与 Linux 原生 GUI 冒烟。**存在工作流或测试源码不代表测试已通过**；核对所用精确提交的检查结果，再考虑真实数据。

前端/Rust 依赖还原可能访问 npm/Cargo 包源；应用运行时不抓取 schema 或发送配置。工具链和依赖缓存不齐全时应报告未执行项目；不要把缺少 Windows GUI、WebView2、DPAPI 或 Linux keyring 环境当成通过。`npm run build` 只验证前端产物，不能代替 Tauri 构建与启动。

Linux / Windows / macOS 的功能支持状态、合成 GUI/CLI 验证步骤与「文档声明 / 源码具备 / 本机已运行」证据分级见 [跨平台合成验收矩阵与操作手册](docs/ACCEPTANCE_MATRIX.md)。

## 运行

- Windows x64：`npm run tauri:build` 产出 `target\release\atm-desktop.exe`，需已安装 WebView2 Runtime。
- Linux：同命令产出 `target/release/atm-desktop`，需要可用且已解锁的会话 keyring 与 WebKitGTK 运行库。
- 想先体验假配置：运行时加 `--demo`。每次创建新的独立临时目录，演示数据不会进入默认密钥库；额度查询返回明确的合成假数据。
- vault 或模板打开失败时，配置服务停止编辑并显示恢复提示；Codex 额度查询不受影响，GLM 个人版查询需待密钥库恢复（团队版不受影响）。
- 正常运行的存储位置：Windows 为 `%LOCALAPPDATA%\atm`，Linux 为 `$XDG_DATA_HOME/atm`（默认 `~/.local/share/atm`）。数据目录保持稳定。此轮按空 vault 前提切换 OS 加密身份，不提供旧非空 vault 的兼容解密。目录内 `vault.*` 保存密钥和目标映射，`templates.*` 保存加密模板，`backups\*.atmbackup` 保存完整加密备份。程序只列举自己的备份目录。

### 桌面便携包

发布包只包含 `atm-desktop`、`icons/`、LICENSE 与 README（无 CLI、无内容 payload）。
整体解压后使用；分发与更新见上文 OMH 章节。便携包未签名；Windows 仍需 WebView2，
Linux 桌面仍需 WebKitGTK，会话 keyring 仅供配置加密功能使用。

```bash
npm run build
cargo build --locked --release -p atm
python3 scripts/Package-Release.py --output artifacts/ai-tooling-manager-local
python3 scripts/Test-Distribution.py artifacts/ai-tooling-manager-local.tar.gz
# Windows 使用 .zip；验收在临时目录运行，不读取真实配置。
```

## 使用步骤

1. 在“命名密钥库”输入名称和 key，点击“保存密钥”。输入默认隐藏，保存后清空；列表完全遮罩，不显示尾号或长度。选择已有密钥只回填名称；编辑时新 key 留空表示保留原值。
2. 在“目标与批量更新”手动选择一个已知配置文件，填写工具用途、精确 **JSON Pointer** 字段，并选择命名密钥。保存后再勾选目标。此工具不自动查找配置或密钥。
3. 点击“生成遮罩预览”。检查每个字段状态、编码和阻止项。只有存在的字符串值能被替换，不自动创建字段。重复名称、歧义、非法结构会阻止整文件；其他有效文件可独立应用。
4. 勾选预览页的明确确认，再点击“应用本次预览”。所选文件自预览后有内容、时间或文件身份变化时，拒绝写入并要求重新预览。预览只可使用一次；选择或已保存密钥/映射发生变化后需重新预览。
5. 在“加密备份与回滚”选择备份，先“检查回滚”，再勾选确认并回滚。回滚恢复整个文件的原始字节，也先备份当前内容。文件有后续编辑时拒绝回滚，不提供强制覆盖。回滚预览之后的变化同样会被拒绝。

工具名称可填写“VS Code + Visual Studio / 共享用途”。同一规范路径会合并处理为一个文件，只备份并替换一次；该文件内多个不同字段可分别映射不同命名密钥。同一文件的同一字段不能重复注册或重复选择。

## 字段映射与范围

以下是**合成结构示例**，并非 Z Code 官方配置预设：

```jsonc
{
  // 原有注释和换行保留
  "servers": {
    "demo": {
      "env": { "API_KEY": "FAKE_OLD_VALUE" },
      "headers": { "Authorization": "Bearer ${input:demo-key}" }
    }
  }
}
```

- 环境字段映射：`/servers/demo/env/API_KEY`。
- 请求头字段映射：`/servers/demo/headers/Authorization`，按实际要求选择“在值前加 Bearer 前缀”。选此前缀时，密钥库中输入裸 key，避免重复前缀。
- `a/b` 属性名在 Pointer 中写成 `a~1b`，`~name` 写成 `~0name`。数组用从零开始的精确索引，例如 `/servers/0/key`；不支持通配符、点路径或递归搜索。
- `${input:...}`、`${env:...}` 等 `${...}` 引用默认保留；也保守保留 `$(...)`、`{{...}}` 和完整 `%...%` 形式。仅在用户明确选中“替换现有变量引用”时替换。
- 支持 JSON、`//` 和 `/* */` 注释、尾随逗号。替换只作用于目标字符串的源字节范围，其他字段、空白、注释、BOM、编码及换行不重写；不做全局替换、不重新序列化整个配置。
- 支持严格 UTF-8（有或无 BOM）及带 BOM 的 UTF-16 LE/BE。拒绝不支持或损坏的编码，包括 UTF-32。文件限 16 MiB，解析深度限 64，节点限 100,000。
- 第一版**不支持 TOML**：尚无可靠的格式保留实现。不支持网络文件、设备路径、备用数据流、符号链接、目录联接和多硬链接文件。不自动创建缺失文件或字段。

## 安全与结果含义

密钥库及完整备份（包括原文、路径和校验信息）均加密保存：Windows 通过 DPAPI **CurrentUser**，Linux 通过 Secret Service、macOS 通过 Keychain 中本应用专用的主密钥加 AES-GCM。没有应用自定义可导出的主密码，也没有明文密钥导出、遥测、云同步或自动重启功能；额度查询仅由用户主动触发。

DPAPI / 会话 keyring / Keychain 不能防御同一用户下的恶意进程、已解锁会话或运行时内存读取。管理器在编辑与应用时需要在内存中持有明文；目标配置也按目标应用要求保存明文。不要把这类本机加密文件当作跨电脑备份；不同用户/电脑环境通常不能直接解密，本工具不承诺迁移恢复。

配置修改可能被应用监测，并由应用自己触发 MCP 重启或重新加载。确认页对此作了提示。请在配置编辑处于空闲状态时应用，减少并发保存。工具不会主动重启任何应用。

批量操作是**逐文件原子替换，不是跨文件事务**。每个文件先校验、保存并刷新完整加密备份，再在同目录暂存新配置、重新校验并通过 Windows `ReplaceFile`（Linux/macOS 同类原子替换）替换。文件锁拒绝普通并发写入；替换需要允许删除共享，Windows 不提供本工具可用的“按预计文件身份比较并替换”原语，最终路径校验与替换间仍有极短的路径替换竞态。替换后再验证内容，有变化则报告需核查；不假称完全消除外部保存竞态。

同目录 `.atm-*.tmp` 是原子替换所需的**明文新配置暂存文件**，不是备份；正常与失败路径会清理，清理被占用阻止时结果区明确报告路径。突发断电或进程被强制终止可能留下暂存文件；请仅在已知目标目录检查这些文件。加密备份始终保持加密。

结果区逐文件报告“成功 / 跳过 / 冲突 / 失败 / 已写入需核查 / 结果未确认”。部分文件失败时，其他成功文件不会自动撤销。用户可针对成功文件检查并回滚；失败文件的已有备份也保留，若原文没有改变，回滚会显示无需恢复。没有把 key、配置原文、框架原始异常或堆栈写入日志的路径；应用不创建持久日志。

## 官方参考

- [VS Code MCP configuration reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration)：说明 `servers`、环境变量、HTTP 请求头及 `${input:...}` 输入变量。这些结构可以帮助用户手动定位字段，但程序不假定服务器名、变量名或用户配置路径。
- [Visual Studio MCP servers](https://learn.microsoft.com/en-us/visualstudio/ide/mcp-servers?view=vs-2022)：说明配置位置与应用自动重新加载行为。官方文档不同示例的结构存在差异，工具因此不内置 Visual Studio 字段或路径预设。
- [Windows DPAPI CryptProtectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata)、[ReplaceFile](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilea)。

参考核验日期：2026-10-12 UTC。Z Code 的路径和字段由用户自行注册；未把合成演示误标成官方预设。

## 源码与重现验证

- `crates/atm-core`：`application/` 统一配置预览/模板/额度编排，桌面仅保留 IPC、授权与窗口适配。另含 DPAPI / Secret Service / Keychain 安全存储、命名密钥库、规范路径与指纹、JSONC 源范围编辑、结构模板与 schema 校验、批量处理和回滚、Codex/GLM 额度探测。
- `apps/desktop`：Tauri 2 壳（`src-tauri`，Tauri commands 与窗口构建）和 TypeScript 前端（`src`，单窗口界面、隔离演示、额度界面）。
- `apps/desktop/tests` 与 `crates/atm-core/tests`：前端 vitest 测试与 Rust 核心/服务测试，全部用 `FAKE_` 值和每次新建的隔离目录。
- `scripts/Verify-Local.sh`：离线源码与合成测试验证（fmt、clippy、Rust 测试、前端检查/测试/构建、显式源码文件清单与凭据模式审计），在子进程内关闭真实对象 opt-in，详见[隔离说明](docs/ACCEPTANCE_MATRIX.md#linux-本地离线检查)。macOS 原生隔离 GUI 使用 `scripts/Verify-MacOS.sh`；源码检查不能替代原生验证。
- `scripts/Test-LinuxKeyring.sh` / `Test-LinuxGui.sh` / `Test-TauriGui.ps1`：隔离 keyring 生命周期、Linux 原生 GUI 与 Windows Tauri GUI 冒烟。
- `scripts/Audit-TrackedSource.ps1`：核对 Git 内实际源码的精确清单、可读性、包装头与明显凭据模式；本机能读和编译不代表没有公司透明加密，核查结论见 `docs/源码包与透明加密核查.md`。
- `.github/workflows/rust-ci.yml`：Rust/前端静态检查与测试、Windows Tauri 构建、隔离真实 Secret Service 生命周期、Linux GUI 冒烟及 macOS arm64 原生隔离 GUI。工作流只请求源码读取权限，不使用真实 key 或部署服务。
- `docs/验证报告.md`（C# 历史基线）与 `docs/CODEX_GLM_LINUX.md`：构建、测试及 GUI 渲染证据；历史报告仅覆盖其标注的提交。

```bash
# 不安装额外工具；在已有 Rust/Node 工具链的 shell 中运行
./scripts/Verify-Local.sh
```

本地构建/验证脚本不执行 Git 提交、推送或仓库创建；用户另行授权的 GitHub 发布仅包含明确清单中的本项目源码与文档。


## 公开前的数据边界

准备分发源码或变更仓库可见性前，先检查[公开前的数据边界](docs/publication-safety.md)。当前文件清理不代表历史、PR diff 或构建产物已经脱敏。

ATM 已退出分发（[ADR 0032](docs/adr/0032-atm-exits-skills-distribution.md)）；OMH standalone 是唯一的 skills/harness 分发者，单目标单 owner 协议见 [ADR 0031](docs/adr/0031-omh-owned-runtime-and-independent-distribution.md)。
