# 茶·图鉴 —— 安全方案（SECURITY）

| 项 | 值 |
|---|---|
| 文档版本 | **v1.3** |
| 创建日期 | 2026-11-07 |
| 分析依据 | [PRD.md](../product/PRD.md) v1.1 · [ARCHITECTURE.md](./ARCHITECTURE.md) v1.0 · [DATA_MODEL.md](./DATA_MODEL.md) v1.5 · [API_CONTRACT.md](../api/API_CONTRACT.md) v1.6 · [database/init.sql](../../database/init.sql) · `backend/app/` |
| 适用范围 | **MVP（PRD §2.1）+ 已确认实现的 S1–S17 全项**；R1–R5 与 X1–X13 不实现 |
| 配套测试 | [TEST_PLAN.md](../testing/TEST_PLAN.md)（用例逐条回溯到本文控制编号 S-01–S-35） |
| 文档地位 | 安全控制的唯一依据；任何控制变更必须同步修改本文控制编号与对应测试用例 |

---

## 0. 结论摘要

本方案把安全要求拆成 **35 个可验证控制项（S-01–S-35）**，每一项都落到具体层、具体文件或具体数据库约束，并在 [TEST_PLAN.md](../testing/TEST_PLAN.md) 中绑定测试用例。

六条硬性目标与落点：

| 硬性目标 | 核心控制 | 落点 |
|---|---|---|
| 密码不得明文存储、不得出现在日志或响应体 | S-01 / S-02 / S-03 | `core/security.py` + `users.password_hash` + `schemas/auth.py` + 日志白名单 |
| 用户只能读改自己的收藏、笔记、分享 | S-12 / S-13 | `services/` 权限判断 + `repositories/` 强制 `user_id` 过滤 + 分享所有权校验 |
| 普通用户不得访问管理员接口（需求写作 `/api/admin/**`，实际前缀 `/api/v1/admin/**`） | S-11 | `routers/admin.py` 路由级 `Depends(get_admin_user)` + `core/auth_deps.py` |
| 撤销令牌不可复活；下架茶不可收藏、不出现在列表与搜索 | S-16 / S-17 / S-18 | `share_tokens.is_active` 单向状态机 + 公开查询强制 `is_active=1` |
| 上传限制类型与大小 | S-23 | `services/upload.py`：5 MB 流式上限 + 魔数校验 + UUID 文件名 + 路径白名单 |
| 防重复提交与非法参数 | S-19 / S-20 / S-24 / S-25 / S-26 / S-27 | Pydantic 约束 + 唯一索引 + 事务 + 行锁 + `IntegrityError` 幂等处理 |

**上线前必须先关闭的三个 P0 缺口（详见 §5）**：`core/auth_deps.py` 尚未创建、`main.py` 未注册全局异常处理器、默认 `SECRET_KEY` / `DEBUG=True` / 种子管理员密码未轮换。

---

## 1. 资产、角色与信任边界

### 1.1 需要保护的资产

| 资产 | 位置 | 泄露/篡改后果 | 主要控制 |
|---|---|---|---|
| 用户密码哈希 | `users.password_hash` | 撞库、账号接管 | S-01、S-02、S-03、S-30 |
| 会话 Cookie | 浏览器 `tea_session` | 身份冒用 | S-06–S-09 |
| 私有品鉴笔记 | `favorite_items.tasting_note` | 用户隐私泄露 | S-12、S-26 |
| 分享令牌 | `share_tokens.token` | 未授权访问清单 | S-13、S-15–S-17 |
| 管理员能力 | `users.role='admin'` | 茶品数据被改、上下架失控 | S-11、S-28 |
| 上传文件 | `uploads/` | 恶意文件、磁盘占满、路径穿越 | S-22、S-23、S-24 |
| 服务端密钥 | `SECRET_KEY`（`.env`） | 伪造任意用户会话 | S-30 |
| 审计记录 | `operation_logs` | 无法追责 | S-28、S-29 |

### 1.2 角色与权限边界

| 能力 | 游客 | `role=user` | `role=admin` |
|---|---|---|---|
| 茶品列表/搜索/详情/首页数据 | 允许 | 允许 | 允许 |
| 查看有效分享（只读） | 允许 | 允许 | 允许 |
| 收藏/取消/清单/笔记/生成或撤销自己的分享/一键收藏 | 拒绝 `40100` | 允许 | 允许 |
| `/api/v1/admin/**` | 拒绝 `40100` | 拒绝 `40300` | 允许 |
| 一键收藏自己的分享 | — | 拒绝 `40300` | 拒绝 `40300` |

角色判定源固定为 `users.role`，**不写入 Cookie、不由前端传入、不做本地缓存**（见 S-08）。

### 1.3 信任边界

```
浏览器（不可信输入）
  │  query / path / JSON / multipart / Cookie（全部可被篡改）
  ▼
Nginx（TLS、请求体上限、安全响应头）
  │  同源反向代理
  ▼
FastAPI（唯一业务边界：身份、权限、参数校验、事务）
  │  仅通过 SQLAlchemy ORM
  ▼
MySQL（不对公网暴露；最小权限账号）
```

**铁律**：

1. 客户端传来的 `user_id`、`role`、`is_active`、`favorite_count`、`list_id`、`owner_id` 一律不可信；服务端只使用“验签 Cookie 中的 `uid`”和“数据库中的 `users.role`”。
2. 前端路由守卫、按钮禁用、必填提示只承担交互体验，**不构成安全控制**（S-14）。
3. 所有授权判断在 `services/` 完成；`repositories/` 只执行 Service 给出的 `WHERE` 条件（ARCHITECTURE §3.3 红线）。
4. 数据库是最后一道防线：唯一索引、外键、`ENUM`、`NOT NULL` 用于兜底并发与非法状态。

---

## 2. 安全控制清单（逐项落位）

> **落点分层约定**：Router（鉴权入口、HTTP 语义）→ Service（业务规则、事务、归属判断）→ Repository（查询条件、参数化）→ Schema（输入/输出 DTO）→ Model/DB（唯一索引、外键、枚举、软失效）→ 部署层（Nginx、MySQL、环境变量）。每条控制至少落在一个层；密码、权限、归属、撤销、下架等关键控制必须跨层兜底（Router 拒绝 + Service 判断 + DB 约束）。
>
> 表中“落点”均指代码实际位置或数据库对象；“验证”列对应 TEST_PLAN 用例编号。标注“待创建”的文件是 ARCHITECTURE 五层骨架中尚未落地的部分，属于 §5 的 P0/P1 整改项。

### 2.1 密码与认证

| ID | 控制目标 | 落点（层 / 文件 / 约束） | 实现要求 | 验证 |
|---|---|---|---|---|
| **S-01** | 密码只以 bcrypt 哈希存储 | `core/security.py` [hash_password / verify_password](file:///d:/项目二/backend/app/core/security.py#L10-L17)；`services/auth.py` [register](file:///d:/项目二/backend/app/services/auth.py#L8-L18)；`models/user.py` [password_hash](file:///d:/项目二/backend/app/models/user.py#L16)；`database/init.sql` [users.password_hash](file:///d:/项目二/database/init.sql#L30-L39) | 统一使用 `bcrypt.hashpw(..., bcrypt.gensalt(rounds=10))`（PRD §4.3 / `init.sql` 注释指定 cost=10；当前代码未显式传 `rounds`，实际为默认 12，强度不降低但与文档不一致，需统一）；数据库列名固定 `password_hash`，**不得新增明文列**；种子数据也必须是哈希 | AUTH-01、AUTH-02、TEA-01 |
| **S-02** | 密码不得出现在任何响应体 | `schemas/auth.py` [UserResponse](file:///d:/项目二/backend/app/schemas/auth.py#L14-L19)；API_CONTRACT §2.1 `User` 仅 5 字段（id / username / role / avatar_url / created_at）；Router 只返回显式字段字典 | 禁止把 ORM `User` 直接 `model_dump()` 或 `dict()` 返回；响应 DTO 不声明 `password` / `password_hash`；`/auth/register`、`/auth/login`、`/auth/me`、`/lists`、`/me/avatar` 全部使用 DTO | AUTH-04、AUTH-09、AVATAR-02 |
| **S-03** | 密码不得写入日志 | `services/auth.py` 不含任何 logger；`core/` 增加日志白名单（待补）；`main.py` 不记录请求体 | 禁止打印/记录 `request.body`、表单字段、`password`；uvicorn access log 只记录方法/路径/状态码，不记录 body 与 Cookie 头；错误日志只记录异常类型与堆栈，不记录入参 | AUTH-09、DEF-03 |
| **S-04** | 登录失败提示统一，降低账号枚举 | `services/auth.py` [login](file:///d:/项目二/backend/app/services/auth.py#L21-L26)；`core/response.py` [BadCredentials](file:///d:/项目二/backend/app/core/response.py#L28-L36) | 用户名不存在与密码错误统一返回 `40110`“用户名或密码错误”；对不存在的用户也执行一次固定 bcrypt 比对（dummy hash），避免响应时间差暴露账号是否存在 | AUTH-05 |
| **S-05** | 用户名唯一且大小写不敏感 | `database/init.sql` [uk_users_username](file:///d:/项目二/database/init.sql#L37)；`services/auth.py` [register 前置查询](file:///d:/项目二/backend/app/services/auth.py#L8-L18) | 应用层先查重给出友好提示；并发注册以唯一索引兜底，捕获 `IntegrityError` 转 `40910`，不得 500；`utf8mb4_unicode_ci` 使 `TeaFan ≡ teafan` | AUTH-02 |
| **S-33** | 登录失败锁定（S14） | `services/auth.py` [login / _is_locked / _record_failure](file:///d:/项目二/backend/app/services/auth.py)；`repositories/login_attempt_repo.py`；`models/login_attempt.py`；`core/config.py` [LOGIN_*](file:///d:/项目二/backend/app/core/config.py) | 15 分钟窗口内同一用户名或同一 IP 失败 ≥ 5 次 → 锁定并返回 `42900` / HTTP 429；锁定判定先于账号校验，锁定期间正确密码同样拒绝，不泄露账号是否存在；只记录失败事件，不记录密码明文；每次登录清理 24 小时前记录，成功登录清空该用户名记录；阈值与窗口由配置项控制 | AUTH-10、AUTH-11、AUTH-12、AUTH-13 |
| **S-34** | 用户贡献与审核门禁（S10–S13） | `routers/contributions.py`、`routers/admin.py`（依赖 `get_current_user` / `get_admin_user`）；`services/contributions.py`；`schemas/contribution.py`；`repositories/contribution_repo.py`；`models/contribution.py` | 提交必须登录；查询与删除仅限本人记录，非本人一律 `40440` 不泄露存在性；仅 `pending` 可删除/审核，已处理记录永久保留；审核队列与通过/拒绝仅管理员；`payload` 由服务端组装，请求体 `extra=forbid`，客户端无法伪造 `status`/`reviewer_id`/`reviewed_at`；新茶提交先经 `tea_name_category_map` 茶类一致性校验与名称相似度查重（>90% 拦截）；拒绝理由必填 1–200 字并回传用户端；审核动作写入 `operation_logs` | CONTRIB-01–CONTRIB-08 |
| **S-35** | 头像变更（ADR-0004） | `routers/me.py`（`get_current_user`）；`services/me.py`（`AVATAR_PRESETS` 白名单）；`services/upload.py` [save_image](file:///d:/项目二/backend/app/services/upload.py)；`repositories/user_repo.py` [update_avatar / add_avatar_log](file:///d:/项目二/backend/app/repositories/user_repo.py)；`schemas/auth.py` `AvatarPresetRequest` | 两个端点均须登录，只能改本人头像；`avatar_url` 由服务端生成，请求体 `extra=forbid` 拒绝客户端直传 URL；上传仅 JPEG/PNG/WebP 且校验魔数，≤ 5 MB，UUID 文件名防路径穿越；预置头像取值必须命中 `tea-01`～`tea-08` 白名单，越界 `40000`；每次变更写入 `operation_logs`（`avatar_update`）且不记录敏感信息；旧头像文件不做即时删除，纳入既有 `uploads/` 清理技术债 | AVATAR-01～AVATAR-05 |

### 2.2 会话

| ID | 控制目标 | 落点（层 / 文件 / 约束） | 实现要求 | 验证 |
|---|---|---|---|---|
| **S-06** | 会话令牌不可伪造、载荷最小 | `core/security.py` [create_session_token / parse_session_token / verify_session_token](file:///d:/项目二/backend/app/core/security.py) | itsdangerous `URLSafeTimedSerializer(SECRET_KEY)`；载荷仅 `{"uid": <int>, "sv": <int>}`（`sv` = `users.session_version`），不含角色、用户名、密码；旧格式无 `sv` 按 0 处理；任何解析失败返回 `None` → `40100` | AUTH-06、AUTH-07、AUTH-16 |
| **S-07** | Cookie 属性安全、有效期 30 天 | `routers/auth.py` [register / login Set-Cookie](file:///d:/项目二/backend/app/routers/auth.py#L13-L40)；`core/config.py` [SESSION_EXPIRE_DAYS](file:///d:/项目二/backend/app/core/config.py#L17-L19) | `HttpOnly=true`、`SameSite=Lax`、`Path=/`、`Max-Age=2592000`；生产 HTTPS 下 `Secure=true`；不设置 `Domain`；登出/改密 `delete_cookie` 使用相同 `path`/`samesite`。`SameSite=Lax` + 仅同源 JSON 写接口 + CORS 白名单共同缓解 CSRF，MVP 不引入独立 CSRF token（若未来改为跨站部署或表单提交，再补 token 与 Origin 校验）。`Secure` 由 `COOKIE_SECURE` 控制：显式值优先，未设置时默认 `not DEBUG`；纯 HTTP 演示部署必须显式设为 `false`（见 §5 G-02 关闭记录） | AUTH-01、AUTH-08 |
| **S-08** | 每次请求验签并实时读取角色 | `core/auth_deps.py` `get_current_user` / `get_admin_user` / `get_optional_user`；各 Router 通过 `Depends` 注入 | 验签取得 `uid` + `sv` → 按 `uid` 查 `users` → 不存在或 `sv != users.session_version` 返回 `40100`；`get_admin_user` 再判断 `role == 'admin'`，否则 `40300`；角色每次查库，Cookie 中不缓存角色，改库后立即生效 | AUTH-04、AUTH-06、AUTH-16、PERM-04 |
| **S-09** | 会话过期语义明确 | `core/security.py` [parse_session_token max_age](file:///d:/项目二/backend/app/core/security.py)；`config.py` `SESSION_EXPIRE_DAYS=30` | `SignatureExpired` / `BadSignature` 统一 `40100`；不区分“过期/伪造/用户不存在/会话版本失效”，避免信息泄露 | AUTH-07 |
| **S-10** | 会话撤销边界与登出/改密吊销 | DATA_MODEL §1（不建 `sessions` 表）；`users.session_version`（0011 迁移）；`routers/auth.py` `logout` 递增版本、`PUT /auth/password` 递增版本；`repositories/user_repo.py` `revoke_sessions` / `update_password` | **登出时若携带有效 Cookie，则 `session_version + 1` 并提交，该用户全部旧 Cookie 立即失效（`40100`）**；未登录/无效 Cookie 仅清 Cookie，保持幂等。**修改密码同样 `session_version + 1`**。因无 `sessions` 表，吊销粒度为用户级：登出会使该用户所有设备会话失效；未登出前被窃取的 Cookie 在 30 天内仍可能有效（残余风险，见 §5 G-12）。响应同时清除当前 Cookie | AUTH-08、AUTH-16 |

### 2.3 授权与资源归属

| ID | 控制目标 | 落点（层 / 文件 / 约束） | 实现要求 | 验证 |
|---|---|---|---|---|
| **S-11** | `/api/v1/admin/**` 全部要求 `role=admin` | `routers/admin.py` 路由级依赖 `dependencies=[Depends(get_admin_user)]`；`core/auth_deps.py`；`main.py` [admin 路由注册](file:///d:/项目二/backend/app/main.py#L31-L37) | 使用 Router 级依赖一次覆盖全部管理端点，避免逐端点遗漏；Service 方法保留二次断言（防御性）；未登录 `40100`，非管理员 `40300`；`/uploads` 静态目录只读，不提供写入 | PERM-01、PERM-02、UPLOAD-05 |
| **S-12** | 用户只能读改自己的收藏、清单、笔记 | `services/favorites.py` / `services/lists.py`；`repositories/favorite_repo.py`；`models/favorite.py` [uk_favorite_user_tea](file:///d:/项目二/backend/app/models/favorite.py#L39-L43) | 所有查询/更新/删除的 `WHERE` 必须包含 `user_id = current_user.id`；**接口不接收 `user_id` 参数**；写笔记时先查 `favorite_items WHERE user_id=? AND tea_id=?`，不存在返回 `40430`；`GET /lists` 只查当前用户清单，`PUT /lists/title` 只改 `UNIQUE(user_id)` 命中的那一行 | FAV-06、NOTE-01、NOTE-02、NOTE-05、PERM-03 |
| **S-13** | 分享撤销必须校验清单所有权 | `services/shares.py` `revoke()`；`repositories/share_repo.py` | 按 `token` 取令牌 → JOIN `collection_lists` 得到 `user_id` → 与当前用户比较；不一致 `40300`；不存在 `40410`；服务层不允许直接按 `token` 删除 | SHARE-07、SHARE-09、PERM-03 |
| **S-14** | 前端守卫不是安全边界 | `frontend/src/router/index.ts`（路由守卫）；`frontend/src/stores/` | 前端 `/admin` 守卫、按钮禁用仅用于体验；所有权限必须由后端 `get_admin_user` / Service 归属判断兜底；不得仅靠隐藏按钮保护管理能力 | PERM-01、UPLOAD-05 |

### 2.4 分享令牌与上下架

| ID | 控制目标 | 落点（层 / 文件 / 约束） | 实现要求 | 验证 |
|---|---|---|---|---|
| **S-15** | 令牌具备足够熵、大小写敏感、全局唯一 | `services/shares.py` 生成逻辑；`database/init.sql` [token utf8mb4_bin](file:///d:/项目二/database/init.sql#L137-L147)；`models/favorite.py` [ShareToken](file:///d:/项目二/backend/app/models/favorite.py#L46-L71) | 8 位字符集 `A-Z a-z 0-9 - _`，使用 `secrets.choice`（禁止 `random`）；`utf8mb4_bin` 保证 `k7X9m2 ≠ K7X9M2`；`uk_share_token` 唯一；碰撞时捕获 `IntegrityError` 重试（最多 3 次） | SHARE-01、SHARE-06 |
| **S-16** | 撤销不可复活，旧令牌永久失效 | `share_tokens.is_active` + `revoked_at`；`services/shares.py` `generate()` / `revoke()` | 撤销只执行 `UPDATE ... SET is_active=0, revoked_at=NOW()`；**Repository 不暴露任何 `is_active=1` 的更新方法**；再次分享必须 `INSERT` 新令牌；DB 行永不删除；代码评审检查不存在“复活”语句 | SHARE-03、SHARE-04 |
| **S-17** | 撤销/不存在/有效的访问语义严格区分 | `services/shares.py` `get_public()` / `copy()`（待创建） | 令牌不存在 → `40410`；令牌存在但 `is_active=0` → 公开查看返回 HTTP 200 + `revoked=true`、`items=[]`、`tea_count=0`；一键收藏返回 `40900`；有效令牌只返回公开字段，不返回笔记与所有者身份 | SHARE-04、SHARE-05、SHARE-09 |
| **S-18** | 下架软失效，全链路隐藏但保留占位 | `teas.is_active`（`init.sql` [L65](file:///d:/项目二/database/init.sql#L61-L72)）；`repositories/tea_repo.py` 公开查询；`services/teas.py` / `favorites.py` / `lists.py` / `shares.py`（待创建） | 公开列表/搜索/热门/随机统一加 `WHERE is_active=1`；详情下架返回 `40401`；收藏下架茶返回 `40401`；取消收藏与状态查询**不校验** `is_active`；清单/分享保留条目并返回 `is_available=false`；一键收藏跳过；**永不物理删除茶品** | TEA-06、TEA-07、LIST-09、FAV-05、SHARE-08 |

### 2.5 输入校验与文件上传

| ID | 控制目标 | 落点（层 / 文件 / 约束） | 实现要求 | 验证 |
|---|---|---|---|---|
| **S-19** | 所有输入字段有明确类型、长度、范围、枚举 | `schemas/auth.py`、`schemas/tea.py`（现有）；`schemas/favorites.py` / `lists.py` / `shares.py` / `admin.py`（待创建）；`database/init.sql` 的 `ENUM` 列 | 用户名 3–20 且 `^[A-Za-z0-9\u4e00-\u9fa5]{3,20}$`；密码 6–64（上限为安全加固，已与 API 契约 §4.1.2 对齐）；清单标题 2–20（trim 后非空）；keyword 1–50；笔记 ≤20,000 字符（S-24 安全上限，已与 API 契约 §4.4.3 v1.1 对齐）；`category`/`season`/`fermentation` 仅六/六/五值；`water_temp` 70.0–100.0；`tea_amount`、`brew_time` >0 且 ≤999.9；分页 `page≥1`、`page_size 1–50` 越界夹取；非法枚举一律 `40000`，不静默丢弃 | AUTH-03、TEA-02、TEA-03、TEA-04、LIST-04、LIST-06、LIST-07、NOTE-04 |
| **S-20** | 防批量赋值与未知字段 | 所有 Pydantic Schema；Service 显式字段映射 | 请求 DTO 设置 `model_config = ConfigDict(extra='forbid')`（或在 Service 中显式取字段）；**禁止 `User(**request.dict())`、`Tea(**body)` 这类整包映射**；`role`、`user_id`、`is_active`、`favorite_count` 永不从请求体读取；管理员新增/编辑只接受契约列出的字段 | AUTH-01、TEA-02、TEA-05、DEF-01 |
| **S-21** | 防 SQL 注入与通配符滥用 | `repositories/*.py`（待创建）；`services/teas.py` 关键词查询 | 100% SQLAlchemy ORM 参数化；禁止 `text()` / 字符串拼接 SQL / `f-string` 进 SQL；`keyword` 使用绑定参数并转义 `%`、`_` 通配符；数据库生产账号禁用 `FILE`、`SUPER`，只授予业务库 CRUD | LIST-02、LIST-03、LIST-05、LIST-08 |
| **S-22** | 防 XSS 与恶意内容 | 前端 Vue 模板默认转义；`frontend/src/` 禁止对笔记使用 `v-html`；`services/upload.py` 拒绝 SVG；Nginx 响应头 | 笔记、茶名、产地等用户/管理员文本一律作为纯文本渲染；禁止 `v-html`、`innerHTML` 渲染笔记；上传拒绝 `image/svg+xml`、`image/gif`；返回 `X-Content-Type-Options: nosniff`；生产 Nginx 增加 `Content-Security-Policy`（至少 `default-src 'self'`）与 `X-Frame-Options: DENY` | UPLOAD-03、NOTE-01 |
| **S-23** | 上传类型、大小、路径三重限制 | `services/upload.py` **待创建**（或 `routers/admin.py` 内实现）；`core/config.py` [MAX_UPLOAD_SIZE_MB](file:///d:/项目二/backend/app/core/config.py#L28-L30)；`main.py` [StaticFiles 挂载](file:///d:/项目二/backend/app/main.py#L39-L42) | ① 读取上传流时累计字节，超过 `5 × 1024 × 1024` 立即中止 → `41300`；② 用 `python-magic`（Windows 需 libmagic）或 `Pillow.Image.verify()` 读取文件头判定真实类型，只允许 `image/jpeg`、`image/png`、`image/webp`，失败 → `41500`；③ 扩展名由服务端 MIME 映射决定，不用原文件名；④ 落盘名为 `uploads/{YYYY}/{MM}/{uuid}.{ext}`；⑤ 写入前 `Path.resolve()` 必须位于 `UPLOAD_DIR.resolve()` 内，防 `../`；⑥ 不提供删除接口，下架不删图 | UPLOAD-01–UPLOAD-05 |
| **S-24** | 超长字段与超大请求体防护 | `schemas/*.py` 的 `max_length`；`services/lists.py` 笔记截断校验；Nginx `client_max_body_size 6m`；MySQL `TEXT` 上限 65,535 字节 | 笔记在 Pydantic/Service 层限制 **20,000 字符**（覆盖 TEXT 约 21,845 个中文字符的物理上限），超过 → `40000`，绝不把 DB 的 `Data too long` 暴露为 500；标题/名称/产地/URL 按契约长度限制；上传与 JSON 请求体在 Nginx 层限制 6 MB；`keyword` 50 字符上限 | TEA-04、LIST-06、NOTE-04、DEF-02 |

### 2.6 数据一致性、并发与重复提交

| ID | 控制目标 | 落点（层 / 文件 / 约束） | 实现要求 | 验证 |
|---|---|---|---|---|
| **S-25** | 收藏/取消幂等，计数不漂移 | `models/favorite.py` [uk_favorite_user_tea](file:///d:/项目二/backend/app/models/favorite.py#L39-L43)；`services/favorites.py`（待创建）；`repositories/favorite_repo.py`（待创建） | 收藏与计数变更在同一事务；新增 `+1`，取消 `GREATEST(favorite_count-1, 0)`；重复收藏捕获 `IntegrityError` 按“已收藏”返回；重复取消按“未收藏”返回；一键收藏先差集再批量插入，只对差集计数 `+N`；提供离线对账脚本（不进请求链路） | FAV-01–FAV-04、FAV-07、SHARE-08、SHARE-10 |
| **S-26** | 重复提交与并发写入有明确策略 | 各 Service 事务边界；`share_tokens` 行锁；`favorite_items` 唯一索引；前端提交锁 | 见下方“重复提交防护矩阵”。所有并发场景以数据库约束 + 事务为最终裁决，应用层只做幂等兼容，不用 `INSERT IGNORE` 吞掉外键错误 | FAV-02、FAV-04、SHARE-02、SHARE-10、DEF-01 |
| **S-27** | 单用户唯一清单 | `database/init.sql` [uk_list_user](file:///d:/项目二/database/init.sql#L98-L109)；`models/collection_list.py` [UniqueConstraint](file:///d:/项目二/backend/app/models/collection_list.py#L34-L36) | `get_or_create` 首次创建；并发创建捕获 `IntegrityError` 后改为“已存在”并读取，不返回 409/500 | LIST-01（首次调用）、SHARE-01（生成前惰性创建） |

**重复提交防护矩阵（S-26 展开）**：

| 端点 | 重复提交后果 | 防护落点 | 预期 |
|---|---|---|---|
| `POST /favorites/{tea_id}` | 多行、重复计数 | `uk_favorite_user_tea` + 同事务 + `IntegrityError` 幂等 | 始终 1 行，计数只 +1 |
| `DELETE /favorites/{tea_id}` | 负计数 | 先查后删 + `GREATEST(...,0)` | 幂等，计数不低于 0 |
| `PUT /lists/notes/{tea_id}` | 覆盖写 | PUT 幂等语义 | 重复提交同值，结果一致 |
| `PUT /lists/title` | 覆盖写 | PUT 幂等语义 | 重复提交同值，结果一致 |
| `POST /shares/generate` | 多个有效令牌 | 事务内 `SELECT ... FOR UPDATE` 锁清单行 → 有 `is_active=1` 则复用 | 并发生成只产生 1 个有效令牌 |
| `POST /shares/{token}/copy` | 重复收藏/重复计数 | 先差集 + 唯一索引 + 同事务 | `added` 只计真实新增，汇总不重复 |
| `POST /admin/teas` | 产生重复茶品 | 前端提交锁（Pinia loading）+ 后端 `operation_logs` 可追溯；茶名允许重复（不同产区），**不设唯一约束** | 单次点击只发 1 个请求；直接并发双 POST 会创建 2 行，属已知设计取舍（PRD 未要求茶名唯一） |
| `POST /admin/upload` | 多个图片文件 | UUID 命名；无删除接口 | 每次上传独立文件，不影响业务一致性 |

### 2.7 审计与日志

| ID | 控制目标 | 落点（层 / 文件 / 约束） | 实现要求 | 验证 |
|---|---|---|---|---|
| **S-28** | 管理员写操作可追溯 | `models/operation_log.py` [OperationLog](file:///d:/项目二/backend/app/models/operation_log.py#L10-L33)；`services/admin.py`（待创建） | 新增/编辑/上下架/小贴士/上传各写 1 行日志，与业务写操作**同一事务**；`action` 为 `create_tea` / `update_tea` / `toggle_tea` / `upload_image`；不记录 GET；`user_id` 使用 `SET NULL`；`target_id` 弱引用不建外键；`detail` 只存名称/方向/大小摘要 | TEA-01、TEA-05、TEA-06、UPLOAD-01 |
| **S-29** | 日志不成为新的泄露面 | 日志配置（待补）；`operation_logs.detail` | 不记录密码、Cookie、完整分享令牌、笔记正文；`detail` ≤500 字符；错误日志只记异常与堆栈；访问日志保留方法/路径/状态码/耗时；生产日志访问权限受限并保留 ≥30 天 | AUTH-09、DEF-03 |

### 2.8 配置、部署与供应链

| ID | 控制目标 | 落点（层 / 文件 / 约束） | 实现要求 | 验证 |
|---|---|---|---|---|
| **S-30** | 配置与错误信息加固 | `core/config.py` [SECRET_KEY / DEBUG](file:///d:/项目二/backend/app/core/config.py#L5-L19)、[UPLOAD_DIR / MAX_UPLOAD_SIZE_MB](file:///d:/项目二/backend/app/core/config.py#L28-L30)；`main.py` [CORS](file:///d:/项目二/backend/app/main.py#L23-L29)；`core/response.py` [异常处理器](file:///d:/项目二/backend/app/core/response.py#L39-L48) | 生产 `DEBUG=False`，`SECRET_KEY` 由环境变量注入且 ≥32 字节随机；`.env` 加入 `.gitignore`；CORS 仅白名单且 `allow_credentials=True`；生产关闭 `/docs`、`/redoc`、`/openapi.json` 或加管理员保护；500 响应只返回 `50000`“服务器内部错误”，不含堆栈/SQL/表名；MySQL 不对公网开放，连接账号非 root；Nginx 启用 TLS、HSTS、`nosniff`、`X-Frame-Options`、CSP | DEF-01、DEF-02、DEF-03 |
| **S-31** | 种子管理员账号上线前必须改密 | `database/init.sql` [种子 admin](file:///d:/项目二/database/init.sql#L174-L180)；`core/config.py` [ADMIN_USERNAME / ADMIN_PASSWORD](file:///d:/项目二/backend/app/core/config.py#L32-L34) | `admin/admin123` 只允许存在于开发/演示环境；上线前用离线脚本以 bcrypt 重写 `users.password_hash`，验证旧密码返回 `40110`、新密码可登录；禁止把默认凭据写入生产 `.env`、部署脚本或 README；该动作计入上线检查单并由负责人签字 | DEF-04 |
| **S-32** | 依赖与供应链可控 | `backend/requirements.txt`、`frontend/package.json`、lock 文件 | 固定版本；禁止使用与 `bcrypt 4.x` 冲突的 `passlib`（TECH_STACK §4.5 已决策直接用 bcrypt）；上线前执行 `pip-audit` / `npm audit`，高危漏洞必须修复或记录风险接受；不使用来源不明的包 | DEF-04（上线检查） |

---

## 3. OWASP Top 10（2021）逐项对照

| 类别 | 本项目处理方式 | 不处理的部分与理由 | 主要落点 | 用例 |
|---|---|---|---|---|
| **A01 失效的访问控制** | 后端统一 `get_current_user` / `get_admin_user`；`/admin/**` 路由级依赖；Service 层归属校验；公开分享只读且不含笔记/所有者信息；收藏/笔记查询强制 `user_id` | 不做管理员 IP 白名单、不做二次因子；MVP 为单管理员、同源部署，收益低且增加运维复杂度。前端路由守卫不视为控制 | S-11–S-14、S-17 | PERM-01–04、NOTE-05、SHARE-07、SHARE-09 |
| **A02 加密机制失效** | bcrypt 存密码；itsdangerous 签名 Cookie；生产 TLS；密钥走环境变量；响应/日志无密码 | **不做笔记字段级加密**：笔记为非身份类隐私文本，加密会引入密钥管理与检索代价；数据库不对公网暴露、访问账号最小化已覆盖主要风险。**不做密码明文哈希替代**（禁止 MD5/SHA1） | S-01–S-03、S-06、S-30 | AUTH-01、AUTH-09 |
| **A03 注入** | 100% ORM 参数化；禁止 raw SQL/字符串拼接；`keyword` 绑定并转义 `%`/`_`；上传文件名服务端生成；Vue 默认转义、禁止 `v-html` 渲染笔记 | 不做 WAF/IPS；MVP 无复杂查询与命令执行面，ORM + 输入白名单已足够。SQL 注入的残余风险由只读/最小权限 DB 账号兜底 | S-19–S-23 | LIST-02、LIST-03、LIST-05、UPLOAD-03、NOTE-01 |
| **A04 不安全设计** | 明确角色矩阵、单清单、软失效、撤销不可逆、幂等与事务边界；业务上限（分页 50、上传 5 MB、笔记 20,000 字符、keyword 50）；**登录失败锁定（S14 → S-33）** | **不做验证码**：MVP 以失败锁定覆盖暴力破解；**不做全站限流**：单机演示环境，Nginx `limit_req` 作为上线可选项记录在 §6。风险接受 | S-04、S-33、S-19、S-24–S-27 | AUTH-05、AUTH-10–AUTH-13、FAV-02、SHARE-02 |
| **A05 安全配置错误** | `DEBUG=False`、随机 `SECRET_KEY`、CORS 白名单、生产关闭文档页、统一 500 文案、MySQL 不对外、非 root 账号 | 不做自动化配置基线扫描/容器镜像加固：MVP 尚未容器化（X3 第二阶段）；以 §6 上线检查单替代 | S-30、S-31 | DEF-01–DEF-04 |
| **A06 易受攻击和过时的组件** | 固定版本、`pip-audit`/`npm audit`、避免 `passlib` 兼容坑、直接使用官方 `bcrypt` | 不做自动化 SBOM/持续依赖机器人：课程项目无 CI 供应链流水线；上线前人工审计一次并记录 | S-32 | DEF-04（上线检查） |
| **A07 身份识别与认证失败** | bcrypt、统一失败提示、**登录失败锁定（用户名 + IP 双维度）**、30 天签名 Cookie、`HttpOnly`/`SameSite`、登出清 Cookie、角色实时读库、**改密后 `session_version` 吊销全部旧会话** | **不做密码找回、邮箱/微信登录**：PRD FR-4.4 明确排除；**登出后旧 Cookie 可重放**：无服务端会话表的设计取舍（S-10），MVP 接受；改密已可强制使旧会话失效，若需“登出即下线”仍须新增 `sessions` 表 | S-01–S-10、S-33 | AUTH-01–AUTH-16 |
| **A08 软件和数据完整性失效** | 不反序列化不可信二进制；仅 JSON/multipart；Alembic 版本化迁移；`operation_logs` 记录管理员写入；上传魔数校验 | 不做代码签名/镜像签名：无发布制品、无容器；依赖完整性由 S-32 兜底 | S-23、S-28、S-32 | TEA-01、UPLOAD-03 |
| **A09 安全日志与监控失效** | uvicorn access log + 业务异常日志 + `operation_logs`；日志不含密码/Cookie/笔记正文；审计与账号生命周期解耦 | **不做集中日志、告警、SIEM**：单机 MVP 无运维平台；以“日志文件权限 + 保留 30 天 + 上线检查”替代。风险接受 | S-03、S-28、S-29 | AUTH-09、TEA-01、DEF-03 |
| **A10 服务端请求伪造（SSRF）** | **不适用**：服务端从不根据用户输入发起 HTTP 请求；`main_image_url` 仅作为字符串返回浏览器，由浏览器直接加载；上传文件落本地磁盘，不做远程抓取 | 若未来增加“远程图片导入/代理”，必须增加域名/IP 白名单、禁止内网地址与重定向跟随；当前无此功能，不引入控制 | — | — |

---

## 4. 业务规则—控制—用例对照

| 业务规则（PRD/契约） | 控制 | 关键实现位置 | 用例 |
|---|---|---|---|
| 密码 bcrypt、不回显、不落日志 | S-01–S-03 | `core/security.py`、`schemas/auth.py`、日志白名单 | AUTH-01、AUTH-04、AUTH-09 |
| 会话 30 天、HttpOnly、过期/伪造拒绝 | S-06–S-09 | `core/security.py`、`routers/auth.py`、`core/auth_deps.py` | AUTH-06–AUTH-08 |
| 用户只读改自己的收藏/笔记/清单 | S-12 | `services/favorites.py`、`services/lists.py`、`repositories/favorite_repo.py` | FAV-06、NOTE-01、NOTE-05、PERM-03 |
| 管理员接口全部 `role=admin` | S-11 | `routers/admin.py`、`core/auth_deps.py` | PERM-01、PERM-02 |
| 分享撤销需所有者、撤销不可复活 | S-13、S-16、S-17 | `services/shares.py`、`share_tokens` 状态列 | SHARE-03、SHARE-04、SHARE-07、SHARE-09 |
| 游客未登录可看有效分享、撤销后不可看内容 | S-17 | `services/shares.py` `get_public()` | SHARE-04、SHARE-05 |
| 下架茶不可收藏、不出现在列表/搜索/推荐 | S-18 | `repositories/tea_repo.py`、`services/teas.py`、`services/favorites.py` | TEA-06、TEA-07、FAV-05 |
| 上传仅 JPEG/PNG/WebP、≤5 MB、无路径穿越 | S-23、S-24 | `services/upload.py`、`core/config.py` | UPLOAD-01–UPLOAD-05 |
| 防重复提交与非法参数 | S-19、S-20、S-24–S-27 | Pydantic、唯一索引、事务、行锁 | AUTH-03、TEA-02–TEA-04、LIST-04、LIST-06、FAV-02、SHARE-02、SHARE-10、DEF-01 |
| 管理员写操作留痕 | S-28 | `services/admin.py`、`operation_logs` | TEA-01、TEA-05、TEA-06、UPLOAD-01 |
| 种子管理员上线前改密 | S-31 | `database/init.sql`、上线检查单 | DEF-04 |

---

## 5. 当前脚手架落地差距与整改优先级

> 以下为“文档已定、代码未落地”或“代码与契约不一致”的差距。**P0 未关闭不得上线**。

| # | 差距 | 具体位置 | 风险 | 优先级 | 整改要求 |
|---|---|---|---|---|---|
| G-01 | `core/auth_deps.py` 不存在，`/auth/me` 仍是 `TODO` | `routers/auth.py` [me](file:///d:/项目二/backend/app/routers/auth.py#L50-L54) | 所有受保护接口目前无法正确鉴权 | **P0** | 新增 `get_current_user` / `get_admin_user`；全部受保护 Router 注入 |
| G-02 | ~~注册/登录响应不符合契约：只返回 `user_id`、`username`，无 `role`/`created_at`；Cookie 未设 `secure`~~ **已关闭（2026-11-12）**：已按 API_CONTRACT §4.1 返回 `User`；Cookie 统一由 `_cookie_kwargs()` 设置 `HttpOnly` / `SameSite=Lax` / `Path=/`，`Secure` 由 `COOKIE_SECURE` 控制（默认 `not DEBUG`），`delete_cookie` 使用相同属性 | `routers/auth.py`、`core/config.py` | 无 | P1 | 已完成；回归用例 `test_cookie_secure_derived_from_debug`、`test_login_cookie_secure_attribute_follows_config` |
| G-03 | 全局异常处理器已定义但未注册 | `main.py` [create_app](file:///d:/项目二/backend/app/main.py#L15-L48)；`core/response.py` [register_exception_handlers](file:///d:/项目二/backend/app/core/response.py#L39-L48) | 业务异常会变成 500 或泄露 FastAPI 默认错误结构 | **P0** | 在 `create_app()` 中调用 `register_exception_handlers(app)`，并把 `RequestValidationError` 统一映射为 `40000` |
| G-04 | `repositories/` 与收藏/清单/分享/管理员/上传的 Service、Schema 尚未创建 | `backend/app/` | 五层架构与权限判断无落点，安全要求无法执行 | **P0** | 按 ARCHITECTURE §3 补齐，并严格遵循 §2 各控制的落点 |
| G-05 | 上传校验未实现 | `routers/admin.py`（待补） | 任意类型/大小文件可落盘 | **P0** | 按 S-23 实现流式大小限制、魔数校验、UUID 命名、路径白名单 |
| G-06 | `share_tokens` 只有 `(list_id, is_active)` 普通索引，并发生成可能产生两个有效令牌 | `database/init.sql` [idx_share_list_active](file:///d:/项目二/database/init.sql#L147) | 清单存在多个有效分享，撤销后另一个仍可访问 | **P1** | Service 内 `SELECT ... FOR UPDATE` 锁清单行；或增加“有效令牌唯一”的生成列/唯一索引（需同步 DATA_MODEL） |
| G-07 | 默认 `SECRET_KEY` 可预测、`DEBUG=True`、种子 `admin/admin123` | [config.py](file:///d:/项目二/backend/app/core/config.py#L5-L34)、[init.sql](file:///d:/项目二/database/init.sql#L174-L180) | 伪造会话、调试信息泄露、默认管理员接管 | **P0** | 生产环境变量注入随机密钥；`DEBUG=False`；上线前轮换管理员密码（S-31） |
| G-08 | 生产 `/docs`、`/redoc`、`/openapi.json` 未关闭 | `main.py` FastAPI 默认 | 暴露全部接口与参数结构 | **P1** | 生产禁用或加管理员保护 |
| G-09 | 笔记无长度上限，但 MySQL `TEXT` 上限 65,535 字节 | `schemas`（待补） | 超长笔记触发 DB 错误 → 500 | **P1** | Pydantic/Service 限制 20,000 字符，超限 `40000`（S-24） |
| G-10 | 登录未做等时比对 | `services/auth.py` [login](file:///d:/项目二/backend/app/services/auth.py#L21-L26) | 响应时间可区分账号是否存在（低风险） | **P2** | 对不存在用户执行 dummy bcrypt 校验（S-04） |
| G-11 | 无登录失败锁定/全站限流 | 全局限流未配置 | 暴力尝试、资源耗尽 | **风险接受** | PRD FR-4.4 明确不做锁定；上线可选 Nginx `limit_req`（§6） |
| G-12 | 未登出即被窃取的 Cookie 仍可在 30 天内重放 | 无 `sessions` 表（S-10） | 令牌泄露后难以按设备撤销 | **已缓解（2026-11-11）** | 登出/改密均递增 `session_version`，吊销该用户全部旧会话；残余风险为“用户未主动登出期间令牌被窃取”，后续可引入 `sessions` 表做设备级撤销 |

---

## 6. 上线前安全验收清单

> 逐项勾选并由负责人签字；任一 P0 项未通过，禁止上线。

- [ ] **P0** `core/auth_deps.py` 已实现，`get_current_user` / `get_admin_user` 覆盖所有受保护接口；未登录 `40100`、非管理员 `40300` 已实测。
- [ ] **P0** `main.py` 已注册全局异常处理器；`RequestValidationError` → HTTP 400 + `40000`；未捕获异常 → `50000` 且无堆栈/SQL。
- [ ] **P0** `SECRET_KEY` 已用 `python -c "import secrets; print(secrets.token_urlsafe(48))"` 生成并注入环境变量；`.env` 未提交仓库；`DEBUG=False`。
- [ ] **P0** 管理员种子密码已轮换：旧密码 `40110`，新密码可登录；`users.password_hash` 为 `$2b$` 开头；生产环境不存在 `admin123` 字样。
- [ ] **P0** 上传接口：>5 MB 返回 `41300`；伪造扩展名/SVG/GIF 返回 `41500`；落盘路径在 `uploads/` 内且文件名为 UUID。
- [ ] **P0** `/api/v1/admin/**` 8 个端点用普通用户 Cookie 全部返回 `40300`，用游客 Cookie/无 Cookie 全部返回 `40100`。
- [ ] **P1** 生产 Cookie 带 `Secure`；`HttpOnly`、`SameSite=Lax`、`Path=/`、`Max-Age=2592000` 全部正确。
- [ ] **P1** `/docs`、`/redoc`、`/openapi.json` 在生产关闭或仅管理员可访问。
- [ ] **P1** CORS 仅保留生产域名；`allow_credentials=True` 且未使用 `*` 通配源。
- [ ] **P1** 分享并发生成只产生 1 个有效令牌；撤销后旧令牌访问为 `revoked=true`、`items=[]`，一键收藏 `40900`。
- [ ] **P1** 下架茶在列表/搜索/热门/随机/详情/收藏全部不可见或拒绝；清单/分享保留 `is_available=false` 占位。
- [ ] **P1** MySQL 仅监听 `127.0.0.1`；生产账号非 root，仅业务库 CRUD 权限；数据库备份可用。
- [ ] **P2** Nginx 配置 TLS、HSTS、`X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、CSP、`client_max_body_size 6m`；可选 `limit_req` 保护登录接口。
- [ ] **P2** `pip-audit` / `npm audit` 已执行，高危漏洞已修复或书面接受。
- [ ] **P2** 日志抽查：注册/登录/笔记/上传后，日志中不含密码、Cookie、笔记正文、完整分享令牌。

---

## 7. 变更记录

| 版本 | 日期 | 内容 |
|---|---|---|
| v1.0 | 2026-11-07 | 基于 PRD/ARCHITECTURE/DATA_MODEL/API_CONTRACT 建立 32 项安全控制、OWASP Top 10 对照、落地差距清单与上线检查单；配套 60 条测试用例 |
| v1.1 | 2026-11-09 | 批次二：新增 S-33 登录失败锁定（S14，用户名 + IP 双维度、`42900`/HTTP 429、24 小时清理、不泄露账号存在性）；A04/A07 风险条目同步；用例增至 70 条 |
| v1.2 | 2026-11-09 | 批次四：新增 S-34 用户贡献与审核门禁（S10–S13：提交需登录、仅本人可见/删除、仅 pending 可处理、审核仅管理员、映射与查重校验、拒绝理由必填、操作日志留痕）；适用范围改为 MVP + S1–S17 全项；配套用例增至 84 条 |
| v1.3 | 2026-11-10 | ADR-0004 头像：新增 S-35 头像变更（登录鉴权、服务端生成地址、魔数+5 MB 限制、预置白名单、`operation_logs` 留痕）；S-02 字段范围补 `avatar_url` 与 `/me/avatar`；配套用例增至 89 条 |
| v1.4 | 2026-11-11 | 自助修改密码（`PUT /auth/password`）：会话载荷增加 `sv`（`users.session_version`，0011 迁移）；S-06/S-08 同步载荷与校验语义，S-10 更新为“登出仍不可吊销、改密可吊销全部旧会话”；A07 风险条目同步；新增 AUTH-14～AUTH-16 用例 |
| v1.5 | 2026-11-11 | 登出会话吊销：`POST /auth/logout` 携带有效 Cookie 时递增 `users.session_version`，旧 Cookie 立即 `40100`；S-10 更新为“登出与改密均可吊销全部旧会话（用户级）”；G-12 风险由“接受”改为“已缓解”；AUTH-08 期望同步 |
