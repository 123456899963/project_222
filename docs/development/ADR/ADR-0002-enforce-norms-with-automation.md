# ADR-0002：用自动化闸门落实项目规范

| 项 | 值 |
|---|---|
| 状态 | 已采纳 |
| 日期 | 2026-11-07 |
| 决策者 | AI 提案 + 用户确认（"全部优化一下"） |
| 任务分级 | C（修改 CI 关键流程与项目规范） |
| 关联任务卡 | TASK-20261107-NORMS |
| 取代 / 被取代 | 无 |

---

## 1. 背景与问题

审计发现项目规范"写得完整但执行薄弱"：AGENTS.md 与 DEVELOPMENT_GUIDE 定义了五层架构、UI 禁用 Element Plus、测试必须实跑、接口/数据库变更必须同步文档，但仓库中同时存在 Element Plus 全局注册、Service 直连查询、测试骨架缺失、CI 仍是 Next.js 模板、包管理器 npm/pnpm 混用等问题。

如果继续只靠 AI 自觉，规范会在每次赶进度时被绕过，且违规不可被发现。需要把**可机械判定**的规则变成 CI 闸门，把**需要判断**的规则变成必填证据。

## 2. 决策驱动因素

- 项目为单人/学生开发，无法承担复杂平台，但 GitHub Actions 免费可用。
- 已有多处历史遗留，不能一次性全部修复，需要"允许基线 + 阻止新增"。
- 规则分散在 AGENTS、DEVELOPMENT_GUIDE、TASK_TEMPLATE，人工维护必然漂移。
- 接口契约、数据库结构与测试计划是前后端联调的唯一依据，必须可校验。

## 3. 备选方案

### 方案 A：继续依赖 AI 自觉 + 人工 review

- 做法：只完善文档，不增加脚本与 CI。
- 优点：零成本、不改变现有流程。
- 缺点：违规不可见；新会话无法判断历史遗留；同类错误会反复出现。
- 风险：规范逐渐失真，最终无人遵守。

### 方案 B：一次性修复全部历史遗留，再启用严格门禁

- 做法：先重构 Element Plus、Repository 下沉、补齐 60 条用例，再开启 CI 阻断。
- 优点：门禁干净，没有例外。
- 缺点：范围过大，会与业务开发争抢时间；容易引入回归。
- 风险：重构期间无法交付业务功能。

### 方案 C：基线 + 自动闸门 + 渐进清理（最终选择）

- 做法：登记已知遗留为基线；新增静态检查脚本与 CI；历史遗留只警告、新违规阻断；触达相关代码时逐步清理。
- 优点：当天即可生效；不阻塞业务；违规可度量、可收敛。
- 缺点：需要维护基线列表；检查脚本本身需要测试。
- 风险：基线长期不清理会变成"合法违规"。

## 4. 最终选择

**选择：方案 C**

理由：

1. 符合当前 MVP 阶段"先让规则可执行，再逐步还债"的现实约束。
2. 基线机制直接对应审计发现的"规范与现状脱节"问题。
3. 自动化只覆盖可机械判定的规则，避免用脚本替代架构判断。

## 5. 影响与后果

**正面影响**

- 包管理器、UI 禁用、五层红线、常量口径、文档链接、ADR/build-log 同步从"口头规则"变成可运行检查。
- 新 AI 进入项目时能看到 §3.1 基线与检查命令，不会把历史遗留当成新错误。

**负面影响 / 需要接受的代价**

- 每次新增依赖或修改配置都要同步 ADR 与文档。
- 基线列表需要人工维护；检查脚本可能误报，需要调整规则而不是直接绕过。

**必须同步的文档与代码**（逐项确认，未完成不得标记"已采纳"）

- [x] [API_CONTRACT.md](../../api/API_CONTRACT.md) / [openapi.yaml](../../api/openapi.yaml)：无接口行为变更
- [x] [DATA_MODEL.md](../../architecture/DATA_MODEL.md) / [init.sql](../../../database/init.sql) / Alembic：无表结构变更
- [x] [ARCHITECTURE.md](../../architecture/ARCHITECTURE.md) / [MODULE_DESIGN.md](../../architecture/MODULE_DESIGN.md)：无分层变更
- [x] [SECURITY.md](../../architecture/SECURITY.md)：无安全项变更
- [x] [TEST_PLAN.md](../../testing/TEST_PLAN.md)：新增冒烟测试，不改变 60 条用例口径
- [x] [build-log.md](../../../harness/build-log.md)：2026-11-07 规范自动化条目
- [x] [AGENTS.md](../../../AGENTS.md)：§0 速览、§3.1 基线、§10 索引、§11 豁免
- [x] [DEVELOPMENT_GUIDE.md](../DEVELOPMENT_GUIDE.md)：v1.2 分级边界、npm、ADR 时点

## 6. 验证方式

- `python scripts/check_all.py` 全部通过。
- `cd backend; python -m ruff check app tests; python -m pytest -q` 通过。
- `cd frontend; npm run lint; npm run typecheck; npm run test:run` 通过。
- GitHub Actions 在 push/PR 上执行同一组命令。

## 7. 复审条件

- 基线违规连续两个季度未减少；
- CI 因环境/依赖问题连续失败超过 3 次；
- 引入新的构建工具或测试框架，需要调整闸门实现。

## 8. 参考资料

- [AGENTS.md](../../../AGENTS.md) §0 / §3.1 / §10 / §11
- [DEVELOPMENT_GUIDE.md](../DEVELOPMENT_GUIDE.md) v1.2
- [TASK_TEMPLATE.md](../../../harness/TASK_TEMPLATE.md)
- `scripts/check_*.py` 与 `.github/workflows/ci.yml`
