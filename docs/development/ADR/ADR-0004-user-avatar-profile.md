# ADR-0004：用户头像与个人中心

| 项 | 值 |
|---|---|
| 状态 | 已采纳 |
| 日期 | 2026-11-10 |
| 决策者 | AI 提案 + 用户确认（2026-11-10：选择「新建个人中心页」+「上传 + 预置头像」） |
| 任务分级 | C（新增 `users` 列 + 新增端点 + 契约变更） |
| 关联任务卡 | TASK-20261110-profile：登录后首页头像 + 个人中心 + 头像更换 |
| 取代 / 被取代 | 无 |

---

## 1. 背景与问题

登录后顶栏仅显示纯文本用户名，用户无个人标识；`users` 表只有 `id / username / password_hash / role / created_at`，没有头像字段；上传能力只存在于管理员端点 `POST /admin/upload`，普通用户无法设置头像；「我的」只有 `/my` 收藏页，缺少统一的个人中心入口。

不解决则：用户无法表达个人身份，收藏/等级等个人数据缺少聚合入口，与「三角色」中注册用户的完整体验不符。

## 2. 决策驱动因素

- `users` 表结构已冻结，任何加列必须走 Alembic 并同步 `DATA_MODEL.md` + `init.sql`（AGENTS §6）
- 上传安全已有成熟实现：`services/upload.save_image`（魔数校验、UUID 文件名、大小上限），复用优于重写
- 前台禁用 Element Plus，个人中心须用自研组件 + CSS 变量还原「清新水墨」风格
- MVP 阶段不引入对象存储 / CDN，头像沿用本地 `/uploads/` 目录
- 普通用户上传属新的攻击面，必须受登录门禁 + 类型/大小校验 + 日志留痕约束

## 3. 备选方案

### 方案 A：仅支持上传本地图片

- 做法：`users.avatar_url` 只存 `/uploads/...`，用户必须自己准备图片
- 优点：实现最少，展示最个性化
- 缺点：新注册用户无头像则永远显示占位字母；需额外准备图片，体验门槛高
- 风险：上传失败率高（尺寸/格式不符）时用户无退路

### 方案 B：仅预置头像（8 选 1）

- 做法：只允许从固定图案中选择
- 优点：零上传风险，无存储增长
- 缺点：用户无法用自己的形象；需求中「更换头像」的个性化表达受限

### 方案 C：上传 + 预置双通道（最终选择）

- 做法：`POST /me/avatar` 支持 multipart 上传（复用 `save_image`）；`PUT /me/avatar` 支持选择 8 个预置 SVG（服务端白名单校验）；`users.avatar_url` 二者共用
- 优点：无图用户可一键选预置，有图用户可上传；预置为服务端静态资源，不占上传目录
- 缺点：两个端点、两条校验分支
- 风险：`avatar_url` 可能被写入任意路径 → 用白名单 + 前缀校验封堵

## 4. 最终选择

**选择：方案 C**

理由：

1. 直接满足「登录后显示头像」与「可更换头像」两个诉求，且新用户开箱即可有头像（驱动因素：注册用户完整体验）
2. 上传复用既有安全实现，预置走静态资源白名单，二者都不新增依赖（驱动因素：MVP 不引对象存储）
3. 单一路径存储（`avatar_url` 一列）避免再拆「头像类型」列，表结构改动最小

## 5. 影响与后果

**正面影响**

- 顶栏与个人中心具备视觉标识；个人数据（等级/统计/收藏）有统一入口
- 头像上传复用统一校验链，安全控制不分裂

**负面影响 / 需要接受的代价**

- 新增 2 个端点、1 列、1 张静态资源目录；接口总数 53 → 55
- 头像文件与茶图共用 `/uploads/`，后续清理策略需一并覆盖

**必须同步的文档与代码**

- [x] [API_CONTRACT.md](../../api/API_CONTRACT.md) / [openapi.yaml](../../api/openapi.yaml)：新增 `POST /me/avatar`、`PUT /me/avatar`；`UserResponse` 增 `avatar_url`
- [x] [DATA_MODEL.md](../../architecture/DATA_MODEL.md) / [init.sql](../../../database/init.sql) / Alembic：`users.avatar_url VARCHAR(255) NULL`，迁移 `0010_user_avatar`
- [x] [MODULE_DESIGN.md](../../architecture/MODULE_DESIGN.md)：me 模块新增 2 端点
- [x] [SECURITY.md](../../architecture/SECURITY.md)：S-35 头像上传与预置白名单
- [x] [TEST_PLAN.md](../../testing/TEST_PLAN.md)：AVATAR-01～AVATAR-05
- [x] [build-log.md](../../../harness/build-log.md)：2026-11-10 条目

## 6. 验证方式

- 后端 pytest：未登录 401 / 非图片 415 / 超限 413 / 非法预置 400 / 正常上传与切换成功
- 手工：登录 → 首页头像出现 → 点击进个人中心 → 上传头像后顶栏即时更新 → 选预置头像后同样生效 → 收藏列表可见
- 命令：`cd backend; python -m pytest -q`、`cd frontend; npm run typecheck; npm run lint`

## 7. 复审条件

- 引入对象存储或 CDN 时（头像地址需改为绝对 URL）
- 需要头像裁剪/审核/敏感图检测时
- 单用户头像历史保留需求出现时（当前为覆盖式替换，`users.avatar_url` 直接改写；旧文件不即时删除，纳入既有 `uploads/` 清理技术债）

## 8. 参考资料

- `backend/app/services/upload.py`（图片校验与落盘）
- `backend/app/routers/admin.py`（既有上传端点范式）
- `docs/architecture/SECURITY.md`（上传类控制项）
