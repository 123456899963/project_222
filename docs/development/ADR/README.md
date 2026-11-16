# 架构决策记录（ADR）目录

| 项 | 值 |
|---|---|
| 创建日期 | 2026-11-07 |
| 适用范围 | 本项目 MVP 阶段的重要架构与技术决策 |
| 流程依据 | [DEVELOPMENT_GUIDE.md](../DEVELOPMENT_GUIDE.md) · [AGENTS.md](../../../AGENTS.md) §10.1 |
| 定位 | 只回答"**为什么这样做**"；具体规则仍以各权威文档为准 |

---

## 1. 用途

权威文档（PRD / API_CONTRACT / DATA_MODEL / ARCHITECTURE / SECURITY / TECH_STACK）回答"**是什么**"，
ADR 回答"**为什么选它、放弃了什么**"。当半年后有人问"为什么用 Cookie 会话而不是 JWT""为什么同步 SQLAlchemy"，
答案应当能在某个 ADR 里找到，而不是散落在对话记录里。

**ADR 不替代权威文档**：决策落地后，结论必须同步进对应权威文档，ADR 只做引用与留痕。

## 2. 什么时候必须写

命中任一即写：

| 触发场景 | 示例 |
|---|---|
| 引入 / 更换 / 移除核心技术依赖 | 引入 Redis、更换 ORM、前台引入 UI 框架 |
| 架构分层、模块边界、目录约定变化 | 调整五层职责、允许 Router 直查库 |
| 数据库结构、索引、字符集、迁移策略 | 加列、改 ENUM、软失效策略调整 |
| 认证、会话、权限的实现方式 | Cookie 会话改 JWT、调整管理员门禁 |
| 跨端点的接口约定 | 统一响应体、错误码映射、分页与排序口径 |
| 部署、构建、环境配置策略 | Nginx 反代方案、CI 流水线重建 |
| C 类技术决策经用户确认 | 任何经确认的架构 / 契约 / 数据取舍 |
| 两份文档冲突需要仲裁 | 按 AGENTS §10 判定后仍存疑的技术取舍 |

## 3. 什么时候不写

| 场景 | 应该记在哪里 |
|---|---|
| 单文件小改动、样式微调、文案修正 | 不需要单独记录，必要时写 build-log |
| 已有权威文档明确规定、实现与文档一致的常规开发 | [build-log.md](../../../harness/build-log.md) |
| 未改变任何设计选择的普通 Bug 修复 | [build-log.md](../../../harness/build-log.md) |
| 范围外需求（S1–S17 / X1–X13）的讨论 | 不记录，先按 C 类走需求变更 |

> 判定口诀：**"为什么"在现有权威文档里能找到吗？** 能找到 → build-log；找不到 → ADR。

## 4. 命名、编号与状态

- 文件名：`ADR-0001-<kebab-case-slug>.md`，四位编号**全局递增、不复用**。
- 模板：[TEMPLATE.md](TEMPLATE.md)
- 状态取值：
  - `提议`（Proposed）：已写出，尚未确认
  - `已采纳`（Accepted）：已确认并在项目中生效
  - `已废弃`（Deprecated）：不再适用
  - `已被取代`（Superseded by ADR-xxxx）：由新 ADR 替代
- **已采纳的 ADR 不允许改写结论**。结论变化时：新建 ADR → 在新 ADR 中写明"取代 ADR-xxxx" → 回到旧文件只改状态行。
- 每个 ADR 必须写清：**原因、备选方案（至少 2 个）、最终选择、影响与需同步的文档**。
- **时点要求**：C 类决策在编码前先写"提议"ADR，随方案一起交给用户确认；确认后改"已采纳"，实施后由 build-log 引用。禁止实施完再补写"为什么"。

## 5. 索引

| 编号 | 标题 | 状态 | 日期 | 关联 |
|---|---|---|---|---|
| [ADR-0001](ADR-0001-knowledge-capture-mechanism.md) | 建立开发知识沉淀机制 | 已采纳 | 2026-11-07 | AGENTS.md §10.1 |
| [ADR-0002](ADR-0002-enforce-norms-with-automation.md) | 用自动化闸门落实项目规范 | 已采纳 | 2026-11-07 | AGENTS.md §0/§3.1；DEVELOPMENT_GUIDE v1.2 |
| [ADR-0003](ADR-0003-content-expansion.md) | 内容扩展（S4 图片集 / S5 视频 / R7 首页背景）数据模型与素材方案 | 已采纳 | 2026-11-09 | DATA_MODEL v1.1；API_CONTRACT v1.2；PLANS_扩展 |
| [ADR-0004](ADR-0004-user-avatar-profile.md) | 用户头像与个人中心（`users.avatar_url` + 上传/预置双通道） | 已采纳 | 2026-11-10 | DATA_MODEL；API_CONTRACT；SECURITY S-35 |
| [ADR-0005](ADR-0005-tea-brewing-guide.md) | 茶品分步冲泡教程的数据模型与录入方式 | 提议 | 2026-11-12 | DATA_MODEL；API_CONTRACT；PAGE_SPECS |

> 新增 ADR 后必须在本表追加一行；本表与目录内文件不一致视为文档缺陷。

## 6. 与其它文档的关系

| 文档 | 关系 |
|---|---|
| [PRD.md](../../product/PRD.md) | 业务规则唯一依据；ADR 不得改变业务规则，涉及业务取舍须先经用户确认 |
| [API_CONTRACT.md](../../api/API_CONTRACT.md) / [openapi.yaml](../../api/openapi.yaml) | 接口唯一依据；ADR 中的接口结论必须落到这两份文件 |
| [DATA_MODEL.md](../../architecture/DATA_MODEL.md) / [init.sql](../../../database/init.sql) | 数据唯一依据；结构类 ADR 必须同步迁移脚本 |
| [ARCHITECTURE.md](../../architecture/ARCHITECTURE.md) / [SECURITY.md](../../architecture/SECURITY.md) | 分层与安全唯一依据 |
| [build-log.md](../../../harness/build-log.md) | 记录"做了什么、测了什么"；ADR 记录"为什么" |

## 7. 变更记录

| 版本 | 日期 | 变更内容 | 依据 |
|---|---|---|---|
| v1.0 | 2026-11-07 | 首次建立 ADR 目录、触发条件、编号与状态规则 | 用户要求 |
| v1.1 | 2026-11-07 | 增加 C 类决策的 ADR 时点要求；新增 ADR-0002 索引 | 规范有效性审计后的整体优化 |
