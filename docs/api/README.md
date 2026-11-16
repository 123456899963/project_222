# 接口规范目录（docs/api）

| 项 | 值 |
|---|---|
| 定位 | 前后端联调与字段命名的**唯一依据** |
| 变更等级 | 任何接口变更均属 C 类，必须先经用户确认（见 [DEVELOPMENT_GUIDE.md](../development/DEVELOPMENT_GUIDE.md) §2.5） |
| 留痕 | 每次接口变更同步记入 [build-log.md](../../harness/build-log.md) |

## 1. 目录内容

| 文件 | 内容 | 权威性 |
|---|---|---|
| [API_CONTRACT.md](API_CONTRACT.md) | 60 个业务端点的请求/响应、错误码、分页与排序、认证约定 | 字段与行为描述的唯一依据 |
| [openapi.yaml](openapi.yaml) | 机器可读的 OpenAPI 定义，供文档与联调工具使用 | 与 API_CONTRACT 必须逐字一致 |

两份文件**同时有效**：任何改动必须一起改，不允许只改其一。

## 2. 变更同步清单

修改任何端点、字段、类型、错误码、分页或排序时，逐项确认：

- [ ] `API_CONTRACT.md` 对应端点章节已更新（含示例）
- [ ] `openapi.yaml` 同步更新（路径、schema、参数、错误响应）
- [ ] 前端 `frontend/src/types/` 与 `frontend/src/api/` 同步
- [ ] 后端 `schemas/` 与 `routers/` 实现一致
- [ ] [TEST_PLAN.md](../testing/TEST_PLAN.md) 对应用例已新增或调整
- [ ] [MODULE_DESIGN.md](../architecture/MODULE_DESIGN.md) 的端点映射未失效
- [ ] `API_CONTRACT.md` 末尾「变更记录」追加一行
- [ ] [build-log.md](../../harness/build-log.md) 记录本次变更与验证证据

## 3. 硬性约定（摘要）

- 统一前缀 `/api/v1`，统一响应 `{ code, message, data }`；成功只看 `code === 0` 且 HTTP 200。
- 业务失败 `HTTP status = code // 100`；FastAPI 422 必须重映射为 `400 / 40000`。
- 字段 `snake_case`，空值 `null`，时间 UTC + ISO8601 带 `Z`。
- 认证为 HttpOnly Cookie `tea_session`，不使用 `Authorization` 头。
- 分页默认 `page_size=12`、上限 50、越界夹取，排序次级键 `id DESC`。

> 以上仅为摘要，冲突时以 [API_CONTRACT.md](API_CONTRACT.md) 正文为准。

## 4. 变更记录

| 日期 | 变更内容 | 依据 |
|---|---|---|
| 2026-11-07 | 新增本索引与接口变更同步清单 | 用户要求建立知识沉淀机制 |
| 2026-11-11 | 新增 `PUT /auth/password`，业务端点 56 → 57 | 用户确认采用 `session_version` 方案 |
| 2026-11-11 | 新增 `GET /admin/operation-logs` 管理员操作日志查询，业务端点 57 → 58 | 用户确认新增后台日志查询页 |
| 2026-11-12 | 新增 `PUT/DELETE /admin/teas/{tea_id}/brewing-guide`，业务端点 58 → 60；茶品详情返回 `brewing_guide` | 用户确认分步冲泡教程（ADR-0005） |
