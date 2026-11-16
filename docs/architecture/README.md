# 架构与数据设计目录（docs/architecture）

| 项 | 值 |
|---|---|
| 定位 | 系统架构、数据模型、安全控制与技术选型的**唯一依据** |
| 变更等级 | 架构分层 / 表结构 / 安全项变更均属 C 类，必须先经用户确认 |
| 留痕 | 重要技术决策另写 [ADR](../development/ADR/README.md)，每次变更记入 [build-log.md](../../harness/build-log.md) |

## 1. 目录内容

| 文件 | 内容 |
|---|---|
| [TECH_STACK.md](TECH_STACK.md) | 技术选型定稿（9 项决策） |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 分层架构与五层职责红线 |
| [MODULE_DESIGN.md](MODULE_DESIGN.md) | 模块划分与端点映射 |
| [DATA_MODEL.md](DATA_MODEL.md) | 9 张表的结构、索引、约束与语义 |
| [SECURITY.md](SECURITY.md) | 33 项安全控制（S-01–S-33） |

数据库建表脚本在 [database/init.sql](../../database/init.sql)，迁移在 `backend/app/alembic/`。

## 2. 按变更类型的同步清单

### 2.1 数据库结构与数据语义变化

- [ ] `DATA_MODEL.md` 对应表 / 字段 / 索引 / ENUM 已更新
- [ ] `database/init.sql` 同步（新建库场景）
- [ ] Alembic 迁移脚本已生成并验证升级/降级
- [ ] [TEST_PLAN.md](../testing/TEST_PLAN.md) 数据库约束用例已调整
- [ ] [MODULE_DESIGN.md](MODULE_DESIGN.md) 若涉及模型归属已更新
- [ ] `DATA_MODEL.md` 末尾「变更记录」追加一行

### 2.2 架构分层 / 模块边界变化

- [ ] `ARCHITECTURE.md` 分层职责与红线已更新
- [ ] `MODULE_DESIGN.md` 模块与端点映射已更新
- [ ] 补充或更新 ADR（说明为什么改、放弃了什么）
- [ ] 受影响的 Service / Repository 迁移清单已列入任务卡

### 2.3 安全控制变化

- [ ] `SECURITY.md` 对应 S 项已更新（增删项需用户确认）
- [ ] `TEST_PLAN.md` 对应用例已新增或调整
- [ ] `API_CONTRACT.md` 若涉及认证/错误响应已同步

### 2.4 技术选型变化

- [ ] `TECH_STACK.md` 决策表已更新
- [ ] 新增 ADR 记录选型对比
- [ ] 依赖清单与构建配置已同步

## 3. 记录原则

- 架构文档描述**最终状态**，不写演进过程；演进原因放 ADR。
- 文档之间冲突时，按 [AGENTS.md](../../AGENTS.md) §10 判定权威版本；仍无法判定则停止实现并升级为 C 类。
- 未同步文档的实现视为未完成。

## 4. 变更记录

| 日期 | 变更内容 | 依据 |
|---|---|---|
| 2026-11-07 | 新增本索引与架构/数据变更同步清单 | 用户要求建立知识沉淀机制 |
