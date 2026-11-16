# 茶·图鉴 —— 测试方案（TEST PLAN）

| 项 | 值 |
|---|---|
| 文档版本 | **v1.7** |
| 创建日期 | 2026-11-07 |
| 测试对象 | MVP 后端 60 个 REST 端点 + 14 张表约束 + 安全控制 S-01–S-35 |
| 依据 | [PRD.md](../product/PRD.md) v1.3 · [API_CONTRACT.md](../api/API_CONTRACT.md) v1.11 · [DATA_MODEL.md](../architecture/DATA_MODEL.md) v1.7 · [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) v1.0 · [SECURITY.md](../architecture/SECURITY.md) v1.4 |
| 用例总数 | **100 条**（高 56 / 中 41 / 低 3） |
| 覆盖类型 | 正向、反向、边界；含越权、并发重复提交、超长字段、非法枚举 |
| 交付边界 | 用例按模块在 `backend/tests/`（pytest）与 `frontend/src/utils/*.spec.ts`（Vitest 纯函数）落地 |

---

## 1. 目的与范围

### 1.1 目的

1. 验证 MVP 六模块（茶品列表/首页/详情/注册登录/收藏清单与分享/管理员后台）的业务闭环。
2. 验证 [SECURITY.md](../architecture/SECURITY.md) 中 34 项安全控制是否真实生效，尤其是密码、越权、管理员门禁、分享撤销、下架隐藏、上传限制、重复提交、登录锁定、贡献审核门禁。
3. 为每条用例提供可回溯的接口路径 / 安全控制编号，便于对照 API 契约与 SECURITY.md。

### 1.2 范围内

- 认证与会话：注册、登录、登出、当前用户、Cookie 有效期与篡改。
- 茶品：列表、筛选、搜索、排序、分页、分类/产地计数、热门、随机、详情。
- 收藏：收藏、取消、状态查询、计数一致性。
- 清单与笔记：默认清单、多清单（新建/改名/删除/迁移）、品鉴笔记读写。
- 分享：生成、复用、撤销、游客查看、一键收藏、撤销后语义。
- 管理员：茶品新增/编辑/上下架/小贴士/统计/上传。
- 用户贡献：新茶提交（映射 + 查重）、科普投稿、我的提交、管理员审核队列与通过/拒绝。
- 数据库约束：唯一索引、外键、枚举、软失效状态。
- 安全控制：S-01–S-35（逐条在用例“对应接口/安全项”列标注）。

### 1.3 范围外

- API_CONTRACT §1.12 / PRD §2.3 明确不在本期范围内的能力，不设用例。
- 第二阶段能力（PRD §6 S1–S17）不设用例。
- 纯性能/压力测试、渗透测试、浏览器兼容性、UI 视觉走查不设用例；并发仅验证“重复提交/唯一性”，不做吞吐量指标。
- 前端组件单测与 E2E 不在本方案中展开，仅保留 PERM-04 这类“前端不可作为安全边界”的说明。

---

## 2. 测试策略与执行方式

| 层 | 方式 | 说明 |
|---|---|---|
| API 集成测试 | pytest + httpx / FastAPI `TestClient`，每个用例携带独立 Cookie Jar | 覆盖 40 个端点；记录 HTTP 状态码、`code`、`data` 与数据库状态 |
| 数据库断言 | 用例步骤中直接查询 `users` / `teas` / `favorite_items` / `share_tokens` / `collection_lists` / `operation_logs` | 不仅看响应，还要看落库结果 |
| 并发测试 | `ThreadPoolExecutor` 20 线程，每线程独立 Session/客户端 | 仅用于 FAV-02、FAV-04、MLIST-01、SHARE-02、SHARE-10 |
| 日志检查 | 采集后端 stdout/日志文件 | AUTH-09、DEF-03、DEF-04 使用 |
| 手工/脚本辅助 | 上传文件构造、角色改库、密码轮换脚本 | 上传用真实文件字节；角色与密码用 SQL/运维脚本 |

**执行约定**：

- 每条用例执行前把数据库恢复到 §3 基线（事务回滚或 fixture 重建）；并发用例必须真实提交，执行后清理。
- 断言同时检查 HTTP 状态码与响应体 `code`；业务失败时 `data` 必须为 `null`。
- 所有错误响应不得出现堆栈、SQL、表名、Pydantic 原始错误结构。
- 时间相关用例不真实等待 30 天：过期场景通过 `verify_session_token(max_age_days=0)` 或测试用不同 `SECRET_KEY` 签发令牌来模拟。

---

## 3. 环境与数据基线

### 3.1 环境

| 项 | 值 |
|---|---|
| 数据库 | MySQL 5.7.19+，独立测试库 `tea_guide_test`，执行 `database/init.sql` 后追加 fixture |
| 后端 | FastAPI + SQLAlchemy 2.0（同步）+ PyMySQL；`SESSION_EXPIRE_DAYS=30`、`MAX_UPLOAD_SIZE_MB=5` |
| 时间 | 统一 UTC；断言 `created_at` 为 ISO8601 `Z` 秒级 |
| 上传 | 临时 `uploads/` 目录，用例后清理；测试图片用真实 JPEG/PNG/WebP 字节 |
| 网关 | DEF-02 需要启用等价 Nginx 限制：`client_max_body_size 6m` |

### 3.2 账号基线

| 账号 | 密码 | 角色 | 用途 |
|---|---|---|---|
| `admin` | `admin123`（种子） | admin | 管理员用例；DEF-04 验证上线前改密 |
| `user_a` | `Tea1234` | user | 清单 A、分享 TA/TR、笔记归属 |
| `user_b` | `Tea1234` | user | 清单 B、分享 TB、越权对比 |
| `user_c` | `Tea1234` | user | 无收藏、无令牌，用于生成分享/一键收藏并发 |

### 3.3 数据基线

| 对象 | 基线 |
|---|---|
| `teas` 1–6 | 种子六款，全部 `is_active=1` |
| `teas` 7 | 测试用“可下架茶”，初始 `is_active=1`，A 已收藏并加入 TA/TB |
| `teas` 8–13 | fixture 追加 6 款在架茶，保证在架总数 ≥13，用于分页 |
| `teas` 99 | 不存在，用于 40400 |
| A 的清单 | 标题“我的收藏”；收藏 `tea 1`（笔记“A-原始笔记”）、`tea 7` |
| B 的清单 | 标题“B的收藏”；收藏 `tea 1`、`tea 2` |
| 分享 TA | A 的有效令牌，携带 `tea 1`、`tea 7` |
| 分享 TR | A 的已撤销令牌（`is_active=0`、`revoked_at` 非空） |
| 分享 TB | B 的有效令牌，携带 `tea 1`、`tea 2`、`tea 3`、`tea 7` |
| `operation_logs` | 仅由用例产生；断言前记录初始行数 |

---

## 4. 优先级与判定标准

| 优先级 | 含义 | 判定 |
|---|---|---|
| **高** | 核心业务闭环、安全红线、数据一致性 | 任一失败 → 阻断发布（S1） |
| **中** | 重要体验、契约一致性、边界行为 | 失败 → 发布前修复（S2） |
| **低** | 低频边界、可观测性优化 | 失败 → 排期修复，可带风险发布（S3） |

**单条用例通过条件**：HTTP 状态码、业务 `code`、`data` 结构、数据库最终状态、日志/文件副作用全部符合“预期结果”，且无 500、无越权、无敏感信息泄露。

---

## 5. 用例明细

> 列说明：“对应接口/安全项”同时给出 API 路径与 SECURITY 控制编号；“前置条件”只列本用例额外依赖，公共基线见 §3。

### 5.1 认证与会话（16 条）

| 编号 | 模块 | 优先级 | 对应接口/安全项 | 前置条件 | 操作步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| **TC-AUTH-01** | 认证 | 高 | `POST /api/v1/auth/register`；S-01/S-02/S-06/S-07 | 用户名 `newuser1` 不存在 | ① 提交 `{"username":"newuser1","password":"tea2026"}`；② 记录响应与 `Set-Cookie`；③ 查 `users` 表 | ① HTTP 200、`code=0`，`data` 含 `id/username/role=user/created_at`；② `tea_session` 为 HttpOnly、SameSite=Lax、Path=/、Max-Age=2592000；③ `password_hash` 以 `$2b$` 开头且不等于明文；响应中无任何密码字段 |
| **TC-AUTH-02** | 认证 | 高 | `POST /api/v1/auth/register`；S-05/S-01 | `user_a` 已存在 | ① 用 `User_A`/`USER_A` 等大小写变体注册；② 查 `users` 行数 | ① HTTP 409、`code=40910`；② 无新增行，`users` 总数不变；③ 不返回 500、不泄露已有账号信息 |
| **TC-AUTH-03** | 认证 | 中 | `POST /api/v1/auth/register`；S-19/S-24 | 准备互不重复的用户名 | ① 用户名 2 字符；② 3 字符；③ 20 字符；④ 21 字符；⑤ 密码 5 字符；⑥ 6 字符；⑦ 64 字符；⑧ 65 字符；⑨ 1000 字符；⑩ 用户名前后空格 `"  ab  "` | ①④⑨ 返回 400/`40000`；②③⑥⑦ 返回 200/`code=0`；⑤⑧ 返回 400/`40000`；⑩ trim 后 2 字符 → `40000`；全程无 500、无 DB 截断 |
| **TC-AUTH-04** | 认证 | 高 | `POST /api/v1/auth/login`、`GET /api/v1/auth/me`；S-01/S-02/S-08 | 种子 `admin` 与 `user_a` 存在 | ① 登录 `admin/admin123`；② 登录 `user_a/Tea1234`；③ 分别用返回 Cookie 调 `/auth/me` | ① 两次均 200/`code=0`，`data.role` 分别为 `admin`、`user`；② 均下发 `tea_session`；③ `/auth/me` 返回同一 `id/username/role`；所有响应不含 `password_hash` |
| **TC-AUTH-05** | 认证 | 高 | `POST /api/v1/auth/login`；S-04/S-03 | 准备 `ghost` 不存在 | ① 登录 `ghost/Any123`；② 登录 `user_a/WrongPwd`；③ 对比两次响应 | ① ② 均 HTTP 401、`code=40110`、message 完全相同“用户名或密码错误”；③ 不区分用户名不存在/密码错误，不设置 Cookie，响应时间差不超过 100 ms |
| **TC-AUTH-06** | 认证 | 高 | `GET /auth/me`、`POST /favorites/1`、`GET /lists`、`PUT /lists/1`、`POST /shares/generate`、`POST /shares/TB/copy`；S-08/S-09/S-11 | 无 Cookie / 无有效会话 | ① 逐个调用上述接口；② 查 `favorite_items`、`collection_lists`、`share_tokens` | ① 全部 HTTP 401、`code=40100`；② 数据库无任何新增/修改；③ 不返回业务数据 |
| **TC-AUTH-07** | 认证 | 中 | `GET /api/v1/auth/me`；S-06/S-09 | 已有合法 `tea_session` | ① 篡改 Cookie 最后一个字符后请求；② 用另一 `SECRET_KEY` 签发的同结构 Cookie 请求；③ 用 `verify_session_token(token, max_age_days=0)` 验证过期分支 | ① ② ③ 均判定无效 → HTTP 401/`code=40100`；不泄露“签名错误/过期/用户不存在”的具体原因 |
| **TC-AUTH-08** | 认证 | 中 | `POST /api/v1/auth/logout`；S-07/S-10 | `user_a` 已登录 | ① 调登出；② 记录 `Set-Cookie`；③ 用未携带旧 Cookie 的客户端调 `/auth/me`；④ 用新客户端重放旧 Cookie；⑤ 查 `users.session_version` | ① 200/`code=0`、`data=null`；② 删除 Cookie：`Max-Age=0`、Path=/、HttpOnly、SameSite=Lax；③ 401/`40100`；④ 旧 Cookie 已被吊销 → 401/`40100`；⑤ `session_version` 较登出前 +1 |
| **TC-AUTH-09** | 认证 | 高 | 注册/登录/`/auth/me`；S-02/S-03/S-29 | 可读取后端日志文件 | ① 依次执行注册、登录、`/auth/me`；② 递归遍历响应 JSON 的 key 与 value；③ 在后端日志中检索本次密码明文与 `password` 关键字 | ① 响应中不存在 `password`/`password_hash` 字段或明文值；② 日志中无密码明文、无 Cookie 值；③ 错误日志只含异常类型/堆栈，不含请求体 |
| **TC-AUTH-10** | 认证 | 高 | `POST /api/v1/auth/login`；S-33/S-14 | 同一用户名 15 分钟内无失败记录 | ① 用错误密码连续登录 5 次；② 第 6 次改用**正确**密码登录 | ① 前 5 次均 401/`40110`；② 第 6 次 HTTP 429、`code=42900`、message“尝试过于频繁，请 15 分钟后再试”，不下发 Cookie；`login_attempts` 有 5 行记录 |
| **TC-AUTH-11** | 认证 | 高 | `POST /api/v1/auth/login`；S-33 | 已触发 AUTH-10 的锁定 | ① 锁定期内用正确密码登录；② 锁定期内用错误密码登录；③ 查响应体 | ① ② 均 429/`42900`；③ 两者 message 完全一致，不暴露账号是否存在、不返回密码校验结果 |
| **TC-AUTH-12** | 认证 | 中 | `POST /api/v1/auth/login`；S-33 | 已有 5 条失败记录 | ① 将 `login_attempts.failed_at` 前移 16 分钟（窗口 15 分钟）；② 用正确密码登录；③ 查记录 | ① 登录成功 200/`code=0` 并下发 Cookie；② 该用户名失败记录被清空 |
| **TC-AUTH-13** | 认证 | 高 | `POST /api/v1/auth/login`；S-33/S-04 | 使用**不存在**的用户名 | ① 用不存在用户名失败 5 次；② 第 6 次再失败 | ① 前 5 次均 401/`40110`；② 第 6 次 429/`42900`，与真实账号锁定响应一致，无法据此枚举账号 |
| **TC-AUTH-14** | 认证 | 中 | `PUT /api/v1/auth/password`；S-01/S-02/S-10 | `user_a` 已登录，当前密码 `tea2026` | ① 提交 `{"old_password":"WrongPwd","new_password":"tea2027"}`；② 查 `users.password_hash` 与 `session_version`；③ 用原 Cookie 调 `/auth/me` | ① HTTP 401、`code=40110`，message 与登录失败一致；② 密码哈希仍匹配 `tea2026`，`session_version` 不变；③ 200/`code=0`，原会话未被误吊销 |
| **TC-AUTH-15** | 认证 | 中 | `PUT /api/v1/auth/password`；S-19/S-24 | `user_a` 已登录，当前密码 `tea2026` | ① 新密码 5 字符；② 新密码 65 字符；③ 新旧密码相同；④ 请求体附加 `username` 字段 | ① ② ③ ④ 均 HTTP 400、`code=40000`；`password_hash` 与 `session_version` 均不变；无 500 |
| **TC-AUTH-16** | 认证 | 高 | `PUT /api/v1/auth/password`、`GET /api/v1/auth/me`、`POST /api/v1/auth/login`；S-06/S-08/S-10 | `user_a` 已登录并记录当前 `tea_session` | ① 提交 `{"old_password":"tea2026","new_password":"tea2027"}`；② 用步骤①前的旧 Cookie 调 `/auth/me`；③ 用新密码登录并调 `/auth/me`；④ 用旧密码登录；⑤ 查响应 `Set-Cookie` 与 `users.session_version` | ① 200/`code=0`、`data=null`，响应清除 `tea_session`（Max-Age=0、Path=/、HttpOnly、SameSite=Lax）；② 401/`40100`（`sv` 不匹配，旧会话立即失效）；③ 新密码 200/`code=0`，新 Cookie 调 `/auth/me` 返回 200；④ 401/`40110`；⑤ `session_version` 较改密前 +1 |

### 5.2 茶品录入与上下架（7 条）

| 编号 | 模块 | 优先级 | 对应接口/安全项 | 前置条件 | 操作步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| **TC-TEA-01** | 管理员/茶品 | 高 | `POST /api/v1/admin/teas`；S-19/S-28/S-11 | `admin` 已登录；`碧螺春` 未录入 | ① 提交 API_CONTRACT §4.6.3 定义的完整合法 JSON；② 查 `teas`、`tea_tips`、`operation_logs` | ① 200/`code=0`，返回完整 `TeaDetail`，`is_active=true`、`favorite_count=0`；② `teas` 新增 1 行，`tea_tips` 按提交的 `tips_*` 建行；③ `operation_logs` 新增 1 行：`action=create_tea`、`user_id=admin.id`、`target_id=新 id`、`detail` 含名称 |
| **TC-TEA-02** | 管理员/茶品 | 中 | `POST /api/v1/admin/teas`；S-19/S-20 | `admin` 已登录 | ① 缺 `name`；② `category=black`；③ `season=夏季`；④ `fermentation=后发酵`（合法）作为对照；⑤ 额外提交 `is_active=false`、`favorite_count=99` | ① ② ③ 返回 400/`40000`，message 无 Pydantic 原始结构；④ 200/`code=0`；⑤ `is_active` 仍为 true、`favorite_count` 仍为 0，额外字段被拒绝（`40000`）或被显式忽略，绝不写入 |
| **TC-TEA-03** | 管理员/茶品 | 中 | `POST /api/v1/admin/teas`；S-19 | `admin` 已登录 | ① `water_temp=69.9`；② `70.0`；③ `100.0`；④ `100.1`；⑤ `tea_amount=0`；⑥ `999.9`；⑦ `1000`；⑧ `brew_time=-1`；⑨ `water_temp=85.55` | ①④⑤⑦⑧ 返回 400/`40000`；②③⑥ 返回 200/`code=0`；⑨ 拒绝多位小数或按 1 位小数校验 → `40000`；DB 数值无四舍五入错误 |
| **TC-TEA-04** | 管理员/茶品 | 中 | `POST /api/v1/admin/teas`；S-19/S-24 | `admin` 已登录 | ① `name` 101 字符；② `origin` 201 字符；③ `price_range` 33 字符；④ `representative_variety` 101 字符；⑤ `main_image_url` 501 字符 | ①–⑤ 均 400/`40000`；无 DB 行写入；无“Data too long”500；响应不暴露列名/表名 |
| **TC-TEA-05** | 管理员/茶品 | 高 | `PUT /api/v1/admin/teas/1`；S-19/S-20/S-28 | `tea 1` 已存在；`admin` 已登录 | ① 提交完整茶品字段，`season=null`、省略 `representative_variety`；② 请求体加入 `id=999`、`is_active=false`、`favorite_count=123`；③ 查 `teas` 与 `operation_logs` | ① 200/`code=0`，`season` 与 `representative_variety` 均为 `null`（PUT 全量替换）；② `id`、`is_active`、`favorite_count` 均不变；③ `updated_at` 更新，`operation_logs` 新增 `update_tea` |
| **TC-TEA-06** | 管理员/茶品 | 高 | `PATCH /admin/teas/7/toggle`、`GET /teas`、`GET /teas?keyword=测试`、`GET /teas/hot`、`GET /teas/random`、`GET /teas/7`、`POST /favorites/7`；S-18 | `tea 7` 在架；A 已收藏 `tea 7` 且 TA 含 `tea 7` | ① `admin` 调 toggle 下架；② 依次调列表、关键词搜索、热门、随机、详情；③ A 调收藏 `tea 7`；④ 查 `teas`、`favorite_items`、`favorite_count` | ① 200/`code=0`、`is_active=false`；② 列表/搜索/热门/随机均不含 `id=7`；详情 404/`code=40401`；③ 收藏 404/`code=40401`；④ `teas` 行保留，`favorite_items` 行保留，`favorite_count` 不变，图片不删 |
| **TC-TEA-07** | 管理员/茶品 | 中 | `PATCH /admin/teas/7/toggle`、`GET /lists`、`GET /shares/TA`、`POST /shares/TB/copy`；S-18 | 承接 TC-TEA-06 或重新下架 | ① A 调 `GET /lists`；② 游客调 `GET /shares/TA`；③ B 调一键收藏 TB（TB 含 `tea 7`）；④ `admin` 再次 toggle 上架；⑤ 复查列表/详情 | ① `tea 7` 条目保留且 `is_available=false`；② 分享条目保留且 `is_available=false`；③ `tea 7` 计入 `skipped`，不新增收藏；④ 200、`is_active=true`；⑤ 列表/详情恢复可见，清单/分享 `is_available=true` |

### 5.2.1 冲泡教程（6 条，ADR-0005）

| 编号 | 模块 | 优先级 | 对应接口/安全项 | 前置条件 | 操作步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| **TC-BREW-01** | 管理员/教程 | 高 | `PUT /admin/teas/{id}/brewing-guide`、`GET /teas/{id}`；S-27/S-28 | `admin` 已登录；存在在架茶 T（无教程） | ① PUT 提交 `intro` + 6 步 + `caution`；② 游客 GET 茶详情；③ 管理员 GET `/admin/teas/{id}`；④ 查 `operation_logs` | ① 200/`code=0`，返回 `tea_id` 与完整教程；② `brewing_guide` 字段与提交一致；③ 同样返回教程；④ 新增 `action=update_brewing_guide` 日志 |
| **TC-BREW-02** | 管理员/教程 | 高 | `PUT /admin/teas/{id}/brewing-guide` | 承接 TC-BREW-01 | ① 再次 PUT 不同文案的 3 步教程；② 查 `tea_brewing_guides` 行数；③ GET 公开详情 | ① 200/`code=0`；② 仍为 1 行（整篇覆盖，不新增）；③ 返回第二次内容，步数 3 |
| **TC-BREW-03** | 管理员/教程 | 中 | `PUT /admin/teas/{id}/brewing-guide`；S-19/S-24 | `admin` 已登录 | ① `steps` 2 条；② 9 条；③ `title` 31 字；④ `detail` 201 字；⑤ `tip` 101 字；⑥ `intro` 201 字；⑦ `caution` 501 字；⑧ 提交未知字段；⑨ 标题或说明为纯空白 | ①–⑨ 均 400/`40000`；响应不含 Pydantic 原始结构、SQL、表名；DB 不写入非法数据 |
| **TC-BREW-04** | 教程/越权 | 高 | `PUT`、`DELETE /admin/teas/{id}/brewing-guide`；S-27/S-28 | 游客未登录；普通用户 B 已登录 | ① 游客 PUT；② 游客 DELETE；③ B 用户 PUT；④ B 用户 DELETE | ①–② 401/`40100`；③–④ 403/`40300`；教程内容不变，`operation_logs` 无新增 |
| **TC-BREW-05** | 管理员/教程 | 中 | `DELETE /admin/teas/{id}/brewing-guide`、`GET /teas/{id}` | 教程存在 | ① 首次 DELETE；② 再次 DELETE；③ GET 公开详情；④ 查 `operation_logs` | ① 200、`deleted=true`；② 200、`deleted=false`（幂等）；③ `brewing_guide=null`；④ 仅首次删除写 `delete_brewing_guide` |
| **TC-BREW-06** | 草稿脚本 | 中 | `python -m app.scripts.seed_brewing_guides` | 存在无教程的茶品；已有教程的茶品 | ① `--dry-run` 统计；② 实跑；③ 再跑一次；④ 抽查七大茶类草稿 | ① 仅统计不写库；② 为缺失茶品各插入 1 条 6 步教程；③ 待生成数为 0，已有教程未被覆盖；④ 七大茶类均 6 步，`title/detail` 非空，能通过 `BrewingGuide` 校验 |

### 5.3 筛选、搜索与分页（9 条）

| 编号 | 模块 | 优先级 | 对应接口/安全项 | 前置条件 | 操作步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| **TC-LIST-01** | 茶品列表 | 高 | `GET /api/v1/teas`；S-18/S-19 | 在架茶 ≥13 条 | ① 不带参数请求；② 请求 `page=2`；③ 核对 `items` 与 `total` | ① 200/`code=0`，`page=1`、`page_size=12`、`items` 12 条；② `page=2`，`items` 剩余条数；③ 排序 `created_at DESC, id DESC`，两页无重复/遗漏，`total` 等于在架总数 |
| **TC-LIST-02** | 茶品列表 | 中 | `GET /teas?category=`；S-19/S-21 | 基线茶品 | ① `category=green`；② `category=green,oolong`；③ 核对每条 `category` | ① 仅绿茶（种子 `tea 1`）；② 返回绿茶+乌龙（`tea 1`、`tea 5`）；③ 同维度多选为 OR，`total` 与并集一致 |
| **TC-LIST-03** | 茶品列表 | 中 | `GET /teas?category=&origin=&season=`；S-21 | 基线茶品 | ① `category=green&origin=浙江&season=明前`；② `category=green&origin=福建`；③ 核对交集 | ① 仅 `tea 1`；② 返回空数组、`total=0`、HTTP 200/`code=0`（不同维度为 AND，不是并集）；③ 无报错 |
| **TC-LIST-04** | 茶品列表 | 高 | `GET /api/v1/teas`；S-19 | 基线茶品 | ① `category=black`；② `season=夏季`；③ `sort=price`；④ `category=green;also` 等格式错误 | ①–④ 均 400/`40000`；不静默忽略、不返回全部数据；响应不泄露枚举定义以外的内部信息 |
| **TC-LIST-05** | 茶品搜索 | 中 | `GET /teas?keyword=`；S-21/S-19 | 基线茶品 | ① `keyword=龙井`；② `keyword=福建`；③ `keyword=` 空串；④ `keyword=%`、`_` | ① 命中 `tea 1`（名称）；② 命中产地含福建的 `tea 2/4/5`；③ 空串忽略，等同无关键词；④ 通配符被转义，不返回全表 |
| **TC-LIST-06** | 茶品搜索 | 中 | `GET /teas?keyword=`；S-19/S-24 | 基线茶品 | ① 50 个汉字关键词；② 51 个汉字关键词；③ 1000 字符关键词 | ① 200/`code=0`（可为空结果）；②③ 400/`40000`；无 DB 截断、无 500 |
| **TC-LIST-07** | 分页 | 中 | `GET /api/v1/teas`；S-19/S-24 | 在架茶 ≥13 条 | ① `page=0`；② `page_size=0`；③ `page_size=51`；④ `page=999`；⑤ `page_size=abc` | ① `page` 夹取为 1；② `page_size` 夹取为 1；③ 夹取为 50；④ 200/`code=0`、`items=[]`、`total` 不变；⑤ 400/`40000`；响应中 `page/page_size` 为实际生效值 |
| **TC-LIST-08** | 排序 | 低 | `GET /teas?sort=favorite`；S-21 | 构造至少两组相同 `favorite_count` 的茶品 | ① 请求 `sort=favorite&page=1&page_size=12`；② 请求 `page=2`；③ 核对排序字段 | ① 排序为 `favorite_count DESC, created_at DESC, id DESC`；② 同秒/同计数按 `id DESC` 稳定；③ 两页无重复、无遗漏 |
| **TC-LIST-09** | 首页数据 | 低 | `GET /teas/categories`、`/teas/origins`、`/teas/hot`、`/teas/random`；S-18/S-19 | 下架 1 款某茶类全部茶品，另保留其他茶类 | ① 查 categories；② 查 origins；③ `hot?limit=0`、`limit=21`；④ `random?exclude_id=1` | ① 固定六项顺序，下架不计入，空茶类 `count=0` 不省略；② 仅省级名称、仅统计在架、按 `count DESC, origin ASC`；③ `limit` 夹取为 1/20，返回实际条数；④ 不返回 `exclude_id=1`，无可选时 `data=null` 且 HTTP 200 |

### 5.4 收藏与取消收藏（7 条）

| 编号 | 模块 | 优先级 | 对应接口/安全项 | 前置条件 | 操作步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| **TC-FAV-01** | 收藏 | 高 | `POST /api/v1/favorites/2`；S-25/S-08/S-18 | A 未收藏 `tea 2`；记录当前 `favorite_count` | ① A 调收藏；② 查 `favorite_items` 与 `teas.favorite_count`；③ 调状态查询 | ① 200/`code=0`，`is_favorited=true`，`favorite_count=原值+1`，`list_ids` 含默认清单；② 新增 1 行 `list_id=默认清单, user_id=A, tea_id=2`；③ 状态接口返回 `true`、同一计数与 `list_ids` |
| **TC-FAV-02** | 收藏/并发 | 高 | `POST /api/v1/favorites/3`；S-25/S-26 | A 未收藏 `tea 3`；准备 20 个独立客户端 | ① 同一客户端连续 POST 两次；② 重置后 20 线程并发 POST 同一 `tea 3`；③ 查行数与计数 | ① 两次均 200、`is_favorited=true`，仅 1 行，计数只 +1；② 20 次均 200/`code=0`（或幂等成功），无 409/500；③ 最终 `favorite_items` 仅 1 行（`UNIQUE(list_id, tea_id)`），`favorite_count` 只 +1 |
| **TC-FAV-03** | 收藏 | 高 | `DELETE /api/v1/favorites/1`；S-25 | A 已收藏 `tea 1`；记录计数 | ① A 调取消；② 查行、计数、清单；③ 调状态查询 | ① 200/`code=0`，`is_favorited=false`，计数 −1，`list_ids=[]`；② 行被删除，默认清单不再含 `tea 1`；③ 状态接口返回 `false` 与同一计数 |
| **TC-FAV-04** | 收藏/并发 | 中 | `DELETE /api/v1/favorites/3`；S-25/S-26 | A 已收藏 `tea 3` | ① 连续 DELETE 两次；② 10 线程并发 DELETE；③ 查计数 | ① ② 均 200/`code=0`，幂等；③ 计数只在首次 −1，后续不变，最终不为负 |
| **TC-FAV-05** | 收藏 | 高 | `POST /api/v1/favorites/99`、`POST /api/v1/favorites/7`；S-18/S-25 | `tea 99` 不存在；`tea 7` 已下架 | ① 收藏 `tea 99`；② 收藏 `tea 7`；③ 查行与计数 | ① 404/`code=40400`；② 404/`code=40401`；③ 均无新增行、计数不变 |
| **TC-FAV-06** | 收藏 | 中 | `GET /api/v1/favorites/1/status`、`/favorites/3/status`、`/favorites/7/status`；S-12/S-18 | A 收藏 `tea 1`、`tea 7`；C 未收藏 `tea 1` | ① A 查 `tea 1`；② C 查 `tea 1`；③ A 查已下架 `tea 7`；④ 查 `tea 99` | ① `true`；② `false`；③ 200/`code=0`，返回 `true` 与缓存计数（允许下架茶状态查询）；④ 404/`40400`；所有响应不含其他用户信息 |
| **TC-FAV-07** | 收藏/边界 | 低 | `DELETE /api/v1/favorites/1`；S-25 | 手工将 `teas.favorite_count` 置 0，A 仍保留 `tea 1` 收藏行 | ① A 调取消；② 查 `teas.favorite_count` | ① 200/`code=0`；② 计数保持 0，不出现负数/无符号溢出；收藏行删除 |

### 5.5 品鉴笔记（5 条）

| 编号 | 模块 | 优先级 | 对应接口/安全项 | 前置条件 | 操作步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| **TC-NOTE-01** | 笔记 | 高 | `PUT /api/v1/lists/{list_id}/notes/1`、`GET /lists/{list_id}`、`GET /shares/TA`；S-12/S-17/S-19 | A 收藏 `tea 1`；TA 有效 | ① A 写入笔记 `第一泡豆香突出`；② A 调 `GET /lists/{list_id}`；③ 游客与 B 分别调 `GET /shares/TA` | ① 200/`code=0`，返回 `tea_id`/`list_id`/`tasting_note`；② 清单条目含笔记；③ 分享响应 `items` 中**无** `tasting_note`、无所有者身份，游客 `is_owner=false` |
| **TC-NOTE-02** | 笔记 | 高 | `PUT /api/v1/lists/{list_id}/notes/2`；S-12 | A 未收藏 `tea 2` | ① A 写入 `tea 2` 笔记；② 查 `favorite_items` | ① 404/`code=40430`；② 不创建收藏行、不落笔记；返回不泄露 B 是否收藏 |
| **TC-NOTE-03** | 笔记 | 中 | `PUT /api/v1/lists/{list_id}/notes/1`；S-19 | A 收藏 `tea 1` 且有笔记 | ① 提交 `{"content":null}`；② 提交 `{"content":"   "}`；③ 查清单与收藏行 | ① ② 均 200/`code=0`，`tasting_note=null`；③ 收藏行保留，仅笔记被清空，条目不删除 |
| **TC-NOTE-04** | 笔记/边界 | 中 | `PUT /api/v1/lists/{list_id}/notes/1`；S-24/S-19 | A 收藏 `tea 1`；应用层已启用 20,000 字符上限 | ① 提交 20,000 字符；② 提交 20,001 字符；③ 提交 70,000 字节（超过 TEXT 上限）；④ 查 DB 与响应 | ① 200/`code=0`；② ③ 400/`40000`“笔记过长”；④ 不出现 500/“Data too long”；原笔记未被截断或破坏 |
| **TC-NOTE-05** | 笔记/越权 | 高 | `PUT /api/v1/lists/{list_id}/notes/1`、`GET /lists/{list_id}`、`GET /shares/TB`；S-12/S-13 | A、B 均收藏 `tea 1`，各有独立笔记 | ① B 写入 `tea 1` 笔记 `B-新笔记`；② A 调 `GET /lists/{A_list}`；③ B 调 `GET /lists/{B_list}`；④ 查 `favorite_items` 两行 | ① 200/`code=0`；② A 的笔记仍为 `A-原始笔记`，未被覆盖；③ B 显示 `B-新笔记`；④ 两行独立，`user_id` 分别正确；分享仍不返回任何笔记 |

### 5.6 分享链路（10 条）

| 编号 | 模块 | 优先级 | 对应接口/安全项 | 前置条件 | 操作步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| **TC-SHARE-01** | 分享 | 高 | `POST /api/v1/shares/generate`、`GET /lists/{list_id}`；S-15/S-16 | `user_c` 已登录且无有效令牌 | ① 第一次生成；② 第二次生成；③ 查 `share_tokens` 与清单详情 | ① 200/`code=0`，`token` 为 8 位 URL-safe、`url=/c/{token}`、`is_new=true`；② 返回同一 token、`is_new=false`；③ DB 仅 1 条 `is_active=1`；清单详情 `share` 非空 |
| **TC-SHARE-02** | 分享/并发 | 高 | `POST /api/v1/shares/generate`；S-26/S-15 | `user_c` 无令牌；准备 20 个独立客户端 | ① 20 线程并发生成；② 查该清单的 `is_active=1` 行数；③ 汇总响应 token 与 `is_new` | ① 全部 200/`code=0`，无 500；② 有效令牌恰好 1 行；③ 所有响应 token 相同，仅 1 个 `is_new=true`，其余 `false`；旧/重复行不产生 |
| **TC-SHARE-03** | 分享 | 中 | `POST /api/v1/shares/revoke/TA`；S-16/S-17 | A 有有效令牌 TA | ① 撤销 TA；② 再次撤销 TA；③ 查 `share_tokens` | ① 200/`code=0`，`is_active=false`、`revoked_at` 非空；② 409/`code=40900`；③ 行仍保留，无物理删除，未新增令牌 |
| **TC-SHARE-04** | 分享/撤销 | 高 | `GET /api/v1/shares/TR`、`POST /shares/generate`、`GET /shares/TR`；S-16/S-17 | A 的 TR 已撤销；A 已登录 | ① 游客访问 TR；② A 重新生成分享；③ 游客再次访问旧 TR；④ 游客访问新 token | ① HTTP 200、`code=0`、`revoked=true`、`items=[]`、`tea_count=0`；② 返回**新 token**、`is_new=true`；③ 旧 TR 仍 `revoked=true`、空列表，**不可复活**；④ 新 token 正常返回内容、`revoked=false` |
| **TC-SHARE-05** | 分享/游客 | 高 | `GET /api/v1/shares/TB`；S-17/S-26 | B 的 TB 有效，含 `tea 1/2/3/7`；B 有笔记 | ① 游客无 Cookie 访问 TB；② 检查响应字段；③ 不再登录访问一次 | ① 200/`code=0`，标题为 B 的清单标题，`tea_count=4`、`revoked=false`、`is_owner=false`；② `items` 仅公开字段（`tea_id/name/category/origin/season/main_image_url/favorite_count/is_available`），无 `tasting_note`、无 B 的 `id/username/email`；③ `tea 7` 的 `is_available=false`，其他为 true |
| **TC-SHARE-06** | 分享/边界 | 中 | `GET /api/v1/shares/{token}`；S-15/S-17 | TB 有效且含大小写混合字符 | ① 访问不存在的 `ZZZZZZZZ`；② 将 TB 转为全大写/全小写后访问 | ① 404/`code=40410`；② 404/`code=40410`（`utf8mb4_bin` 大小写敏感，不命中原令牌）；不泄露“令牌存在但大小写不符” |
| **TC-SHARE-07** | 分享/越权 | 高 | `POST /api/v1/shares/revoke/TA`；S-13/S-12 | TA 属于 A；B 已登录 | ① B 撤销 TA；② 查 TA 状态；③ 游客访问 TA | ① 403/`code=40300`；② `is_active` 仍为 1，`revoked_at` 仍为 null；③ 分享仍可正常查看；B 的行为不产生审计/状态变更 |
| **TC-SHARE-08** | 分享/一键收藏 | 高 | `POST /api/v1/shares/TB/copy`；S-18/S-25/S-26 | B 已登录且是 TB 所有者，不能 copy；改用 C 登录；TB 含 `tea 1/2/3/7`；C 未收藏任何茶；`tea 7` 下架 | ① C 调一键收藏 TB；② 查 C 的 `favorite_items` 与计数；③ 汇总响应 | ① 200/`code=0`，`added=3`、`skipped=1`、`total=4`；② C 新增 `tea 1/2/3` 共 3 行，`tea 7` 不新增；③ `tea 1/2/3` 计数各 +1，`tea 7` 不变；重复调用后 `added=0`、全部 skipped |
| **TC-SHARE-09** | 分享/权限 | 中 | `POST /shares/{token}/copy`；S-13/S-17/S-11 | A 有 TA；TB 有效；TR 已撤销 | ① A 对自己 TA 调 copy；② 游客对 TB 调 copy；③ B 对 TR 调 copy | ① 403/`code=40300`（所有者不得一键收藏自己）；② 401/`code=40100`；③ 409/`code=40900`；④ 三种情况均无收藏新增、无计数变化 |
| **TC-SHARE-10** | 分享/并发 | 中 | `POST /api/v1/shares/TB/copy`；S-25/S-26 | `user_c` 登录且未收藏 TB 中的 3 款在架茶；20 个独立客户端 | ① 20 线程并发 copy；② 查 C 的收藏行；③ 汇总 `added` 与计数 | ① 全部 200/`code=0`，无 500；② `tea 1/2/3` 恰好各 1 行，无重复；③ `added` 之和为 3，计数各 +1；重复调用只增加跳过数 |

### 5.7 权限校验（6 条）

| 编号 | 模块 | 优先级 | 对应接口/安全项 | 前置条件 | 操作步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| **TC-PERM-01** | 权限 | 高 | `GET/POST/PUT/PATCH /api/v1/admin/**` 共 8 个端点；S-11/S-12 | `user_a` 已登录 | ① 依次调用 `GET /admin/teas`、`GET /admin/teas/1`、`POST /admin/teas`（合法体）、`PUT /admin/teas/1`、`PATCH /admin/teas/1/toggle`、`PUT /admin/teas/1/tips`、`GET /admin/stats`、`POST /admin/upload`（合法 JPEG）；② 查 `teas`、`operation_logs`、`uploads/` | ① 8 个全部 403/`code=40300`；② 无新增/修改茶品，无新增 `operation_logs`，无文件落盘；③ 不因“带合法 body”而先执行业务逻辑 |
| **TC-PERM-02** | 权限 | 高 | `/api/v1/admin/**`；S-11/S-08 | 无 Cookie | ① 调用 `GET /admin/teas`、`GET /admin/stats`、`POST /admin/upload`；② 查副作用 | ① 全部 401/`code=40100`，优先于参数校验；② 无数据/文件副作用；不返回管理端数据结构 |
| **TC-PERM-03** | 权限/越权 | 高 | `GET /lists`、`GET /lists/{other_list_id}`、`PUT /lists/{list_id}/notes/2`、`POST /shares/revoke/TB`；S-12/S-13 | A、B 各登录；A 未收藏 `tea 2`，B 已收藏；TB 属 B | ① A 调 `GET /lists`；② B 调 `GET /lists`；③ A 读 B 的清单与写 `tea 2` 笔记；④ A 撤销 TB；⑤ 查两用户数据 | ① 只返回 A 的清单；② 只返回 B 的清单（含 `tea 2`）；③ `GET /lists/{B_list}` → 404/`40420`，写笔记 → 404/`40430`，B 的笔记不变；④ 403/`code=40300`，TB 仍有效；⑤ 无跨用户读写 |
| **TC-PERM-04** | 权限/角色 | 中 | `POST /favorites/1`、`GET /admin/stats`；S-08/S-11/S-12 | `admin` 已登录 | ① admin 调用户端收藏；② SQL 将 `admin.role` 改为 `user`；③ 不重新登录，立即调 `/admin/stats`；④ 改回 `admin` 后再调；⑤ 核对已收藏状态 | ① 200/`code=0`（管理员可执行用户侧能力）；② 改库成功；③ 403/`code=40300`（角色实时读库，不受旧 Cookie 影响）；④ 200/`code=0`；⑤ 管理员会话未被强制退出，仅权限随角色变化 |
| **TC-PERM-05** | 权限/审计 | 高 | `GET /api/v1/admin/operation-logs`；S-11/S-28 | `admin` 已登录；已有写操作日志 | ① 不带参数查询；② 传 `action=create_tea&target_type=tea`；③ 传 `page=0&page_size=999`；④ 传 `start_date` / `end_date`（含边界） | ① 200/`code=0`，`data` 含 `items/total/page/page_size`，条目含 `id/admin_id/admin_username/action/target_type/target_id/detail/ip_address/created_at`，排序 `created_at DESC, id DESC`；② 全部命中 `action=create_tea` 且 `target_type=tea`，`admin_username` 为操作管理员；③ `page` 夹取为 1、`page_size` 夹取为 50；④ 仅返回区间内记录，边界日包含，`ip_address` 为 `null` |
| **TC-PERM-06** | 权限 | 高 | `GET /api/v1/admin/operation-logs`；S-11/S-08/S-19 | 普通用户已登录；另有游客客户端 | ① 普通用户调用；② 游客调用；③ 管理员传非法日期 `2026/11/11` 与 `start_date` 晚于 `end_date` | ① 403/`code=40300`；② 401/`code=40100`；③ 400/`code=40000`；三种情况均不返回任何日志数据，不产生新日志 |

### 5.8 文件上传（5 条）

| 编号 | 模块 | 优先级 | 对应接口/安全项 | 前置条件 | 操作步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| **TC-UPLOAD-01** | 上传 | 高 | `POST /api/v1/admin/upload`；S-23/S-11 | `admin` 已登录；准备真实 JPEG/PNG/WebP，各 ≤5 MB | ① 分别上传 3 种文件；② 检查 `data.url/size/content_type`；③ `GET` 返回的 URL；④ 查 `operation_logs` 与磁盘 | ① 3 次均 200/`code=0`；② `url` 为 `/uploads/YYYY/MM/<uuid>.<ext>`，扩展名由服务端决定，`size` 正确，`content_type` 对应；③ 图片可访问且 `Content-Type` 正确；④ `operation_logs` 新增 `upload_image`，原文件名不用于落盘 |
| **TC-UPLOAD-02** | 上传/边界 | 高 | `POST /api/v1/admin/upload`；S-23/S-24 | `admin` 已登录；构造 5 MB + 1 字节 JPEG | ① 上传超限文件；② 查 `uploads/` 与 `operation_logs` | ① 413/`code=41300`；② 无文件落盘、无日志；不把整个文件读入内存后再拒绝（可用内存观测辅助） |
| **TC-UPLOAD-03** | 上传/类型 | 高 | `POST /api/v1/admin/upload`；S-23/S-22 | `admin` 已登录 | ① 文本文件改名为 `.jpg`；② 上传 SVG；③ 上传 GIF；④ 上传可执行文件改名为 `.png` | ①–④ 全部 415/`code=41500`；无文件落盘；校验基于魔数而非扩展名/客户端 `Content-Type` |
| **TC-UPLOAD-04** | 上传/路径 | 中 | `POST /api/v1/admin/upload`；S-23 | `admin` 已登录；准备合法 JPEG | ① 文件名设为 `../../evil.jpg`；② 文件名设为 `..\..\evil.jpg`；③ 上传后检查磁盘与返回 URL | ① ② 均 200/`code=0`（或安全拒绝），落盘路径必须在 `uploads/YYYY/MM/<uuid>.jpg` 内；③ `uploads/` 外无新文件；返回 `url` 不含 `..`；原文件名仅作为响应字段展示，不参与路径 |
| **TC-UPLOAD-05** | 上传/异常 | 中 | `POST /api/v1/admin/upload`；S-23/S-11 | `admin`、`user_a` 已登录 | ① 上传 0 字节文件；② 不传 `file` 字段；③ `user_a` 上传合法 JPEG | ① 400/`code=40000`；② 400/`code=40000`（422 已重映射）；③ 403/`code=40300`；三种情况均无文件落盘 |

### 5.9 异常状态与防御（4 条）

| 编号 | 模块 | 优先级 | 对应接口/安全项 | 前置条件 | 操作步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| **TC-DEF-01** | 异常/参数 | 中 | `POST /auth/register`、`GET /teas`；S-19/S-20/S-30 | 无需登录 | ① 发送畸形 JSON `{`；② 注册时附加未知字段 `role=admin`；③ `page_size=abc`；④ `Content-Type: text/plain` 提交 JSON | ①–④ 均 400/`code=40000`；注册的 `role` 仍为 `user`（或未知字段被 `40000` 拒绝）；响应无 Pydantic 原始错误、无堆栈、无 SQL/表名；无 500 |
| **TC-DEF-02** | 异常/超大 | 中 | `POST /api/v1/admin/teas`；S-24/S-30 | `admin` 已登录；网关 `client_max_body_size=6m` | ① 提交 10 MB 的 `shape_desc`；② 提交 10 MB 的笔记内容；③ 查 DB 与日志 | ① ② 返回 413（`41300`）或 400（`40000`），不得 500；③ 无 DB 行、无内存溢出；日志不打印请求体 |
| **TC-DEF-03** | 异常/错误处理 | 高 | `GET /api/v1/teas`；S-30/S-03 | 测试环境可模拟数据库/Repository 抛出 `RuntimeError` | ① 注入运行时异常；② 调 `GET /teas`；③ 检查响应与服务端日志；④ 恢复后再次调用 | ① HTTP 500、`code=50000`、message 为通用“服务器内部错误”；② 响应无堆栈、无 SQL、无表名/文件路径；③ 服务端日志有完整堆栈但无密码/Cookie；④ 恢复后返回 200，服务未崩溃 |
| **TC-DEF-04** | 上线检查 | 高 | 种子管理员与密码轮换；S-31/S-02 | 演练环境执行 `init.sql`；准备轮换脚本 `app.scripts.rotate_admin_password` | ① 用 `admin/admin123` 登录；② 执行轮换脚本设置新密码 `Str0ng!Admin#2026`；③ 用旧密码登录；④ 用新密码登录；⑤ 查 `users.password_hash`、脚本输出与日志 | ① 200/`code=0`（仅开发/演练环境允许）；② 脚本执行成功；③ 401/`code=40110`；④ 200/`code=0`；⑤ `password_hash` 以 `$2b$10$` 开头；脚本/日志无明文密码；仓库生产配置中检索不到 `admin123` |

### 5.10 我的与个性化（6 条）

| 编号 | 模块 | 优先级 | 对应接口/安全项 | 前置条件 | 操作步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| **TC-ME-01** | 我的 | 中 | `GET /api/v1/me/stats`；S-11 | 无 Cookie | ① 未登录调用；② 用普通用户 Cookie 调用 | ① 401/`40100`；② 200/`code=0`，返回 `favorite_count/note_count/share_count/level` |
| **TC-ME-02** | 我的 | 高 | `GET /api/v1/me/stats`；S-15 | 用户已收藏 1 款、写 1 条笔记、生成 1 个有效分享 | ① 调用统计接口；② 核对返回值 | ① `favorite_count=1`、`note_count=1`、`share_count=1`；② `level.name=茶客`、`index=1`、`next_name=茶友`、`next_threshold=5`、`remaining=4` |
| **TC-ME-03** | 我的 | 中 | `GET /api/v1/me/stats`；S-15 | 可构造不同收藏数 | ① 收藏数 0/4/5/19/20/49/50/120 分别计算等级 | ① 依次为 茶客/茶客/茶友/茶友/茶人/茶人/茶师/茶师；② 茶师 `next_name=null`、`remaining=0`；其余 `remaining` 与阈值差值一致 |
| **TC-REC-01** | 推荐 | 中 | `GET /api/v1/teas/recommended`；S-16 | 游客无 Cookie | ① 调用 `?limit=1`；② 检查返回茶品 | ① 200/`code=0`，`data` 为 1 条列表项；② 茶品 `is_active=1`（下架茶不出现） |
| **TC-REC-02** | 推荐 | 中 | `GET /api/v1/teas/recommended`；S-16 | 登录用户无收藏 | ① 调用 `?limit=1`；② 与游客结果对比 | ① 200/`code=0` 且返回 1 条；② 退化为完全随机，不报错 |
| **TC-REC-03** | 推荐 | 高 | `GET /api/v1/teas/recommended`；S-16 | 用户已收藏 1 款绿茶，库中另有未收藏绿茶 | ① 调用 `?limit=1`；② 核对推荐结果 | ① 200/`code=0`；② 推荐茶品 `category=green` 且 `id != 已收藏茶`；③ 已下架茶不出现 |

### 5.11 多清单（6 条）

| 编号 | 模块 | 优先级 | 对应接口/安全项 | 前置条件 | 操作步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| **TC-MLIST-01** | 多清单 | 高 | `GET /api/v1/lists`、`POST /api/v1/lists`；S-11/S-15 | 新用户无任何清单 | ① 调 `GET /lists` 触发默认清单惰性创建；② 连续创建 9 个普通清单；③ 再创建第 10 个；④ 核对摘要字段 | ① 200/`code=0`，返回 1 条默认清单（`is_default=true`、`tea_count=0`）；② 每次 200/`code=0`，`is_default=false`；③ 400/`40000`，提示已达 10 个上限；④ 列表按默认清单置顶、其余 `created_at ASC`；每项含 `id/title/is_default/tea_count/created_at/updated_at/share` |
| **TC-MLIST-02** | 多清单 | 高 | `DELETE /api/v1/lists/{id}`；S-11/S-27 | A 有默认清单与普通清单 L2（含 2 款茶），L2 已生成有效分享令牌 | ① 删除 L2；② 删除默认清单；③ 查 `favorite_items`、`collection_lists`、`share_tokens` | ① 200/`code=0`；L2 条目迁移到默认清单（茶品不丢），默认清单 `tea_count` 相应增加；② 默认清单返回 400/`40000`（不可删除）；③ 迁移后 `favorite_items.list_id` 全部指向默认清单，无孤儿行 |
| **TC-MLIST-03** | 多清单 | 高 | `DELETE /api/v1/lists/{id}`；S-27 | 默认清单含 `tea 1`（笔记“默认笔记”），普通清单 L3 也含 `tea 1`（笔记“L3 笔记”） | ① 删除 L3；② 查默认清单中 `tea 1` 的条目 | ① 200/`code=0`；② 不产生重复条目（仍为 1 条），默认清单非空笔记优先保留“默认笔记”，若默认笔记为空则保留“L3 笔记”；无唯一键冲突、无 500 |
| **TC-MLIST-04** | 多清单 | 中 | `DELETE /api/v1/lists/{id}`、`GET /api/v1/shares/{token}`；S-18 | 普通清单 L4 已生成有效分享令牌 T4 | ① 删除 L4；② 游客访问 T4；③ 查 `share_tokens` | ① 200/`code=0`；② 404/`code=40410`（分享不存在或已失效）；③ T4 随清单级联删除，无悬挂令牌 |
| **TC-MLIST-05** | 多清单 | 中 | `POST /api/v1/shares/generate`、`GET /api/v1/shares/{token}`；S-15/S-18 | A 有默认清单与普通清单 L5（各含不同茶） | ① 生成默认清单分享；② 生成 L5 分享（body 传 `list_id`）；③ 游客分别查看两个 token；④ 再次为同一清单生成分享 | ① ② 200/`code=0`；③ 两个分享分别只含各自清单的条目，互不串数据；④ 复用同一有效令牌，不新建行 |
| **TC-MLIST-06** | 多清单 | 高 | `POST /api/v1/favorites`；S-27 | A 已收藏 `tea 1`；茶 `tea 1` 初始 `favorite_count` 已知 | ① 把 `tea 1` 加入第二个清单（body 传 `list_id`）；② 从默认清单移除 `tea 1`；③ 再从第二个清单移除 | ① 200/`code=0`，`favorite_count` **不变**（同一用户 × 茶品只计一次），`list_ids` 含两个清单；② `favorite_count` 仍不变（其他清单仍保留）；③ 最后一条移除后 `favorite_count` 减 1，最小为 0，绝不为负 |

### 5.12 用户贡献与审核（8 条）

| 编号 | 模块 | 优先级 | 对应接口/安全项 | 前置条件 | 操作步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| **TC-CONTRIB-01** | 贡献 | 高 | `POST /contributions`；S-34 | 用户已登录；提交名称不与现有茶品冲突 | ① 以 `type=new_tea` 提交完整茶品字段；② 查 `GET /contributions/mine`；③ 查 DB | ① 200/`code=0`，`status=pending`、`payload.name` 正确、`target_tea_id=null`；② 仅返回本人记录且倒序；③ `contributions` 新增 1 行，`type=new_tea` |
| **TC-CONTRIB-02** | 贡献 | 高 | `POST /contributions`；S-34 | `tea_name_category_map` 含“碧螺春→green” | ① 提交名称“碧螺春”、茶类 `red`；② 查提交记录 | ① 400/`code=40000`，message 含“绿茶”与“不一致”；② 不产生 pending 记录 |
| **TC-CONTRIB-03** | 贡献 | 高 | `POST /contributions`；S-34 | 已有茶品“大红袍” | ① 提交同名“大红袍”（茶类正确）；② 提交“大红袍茶”；③ 查记录 | ① 400/`code=40000`，“过于相似”；② 相似度 >90% 同样拦截；③ 均未落库 |
| **TC-CONTRIB-04** | 贡献 | 中 | `POST /contributions`；S-34 | 存在在架茶 `tea 1` 与不存在 ID | ① `type=article` 内容 2 字；② 目标茶品不存在；③ 目标茶品已下架；④ 合法内容 3–500 字 | ①–③ 400/`code=40000`（长度/茶品无效）；④ 200/`code=0`、`status=pending`、`payload` 含 `title/content`，`target_tea_name` 正确 |
| **TC-CONTRIB-05** | 贡献/越权 | 高 | `GET /contributions/mine`、`DELETE /contributions/{id}`；S-34 | A 有 pending 提交；B 已登录 | ① B 查我的提交；② B 删除 A 的提交；③ A 删除自己的 pending；④ A 删除已处理记录 | ① 不含 A 的记录；② 404/`code=40440`（不泄露存在性）；③ 200/`code=0` 且记录消失；④ 400/`code=40000`，已处理记录保留 |
| **TC-CONTRIB-06** | 贡献/审核 | 高 | `GET /admin/contributions`、`POST .../approve`；S-34 | A 提交新茶 pending；管理员已登录 | ① 管理员按 `status=pending&type=new_tea` 查队列；② 通过该提交；③ 查 `teas`；④ 再次通过 | ① 列表含该记录且带 `username`；② 200/`code=0`、`status=approved`、`reviewer_id/reviewed_at` 非空；③ 生成同名茶品且 `is_active=1`；④ 400/`code=40000`（不可重复审核） |
| **TC-CONTRIB-07** | 贡献/审核 | 中 | `POST .../reject`；S-34 | A 有 pending 提交 | ① 管理员以“信息不完整”拒绝；② A 查我的提交；③ A 删除该记录；④ 管理员再通过 | ① 200/`code=0`、`status=rejected`、`reject_reason` 正确；② 返回同理由；③ 400/`code=40000`；④ 400/`code=40000`；`operation_logs` 有 `reject_contribution` |
| **TC-CONTRIB-08** | 贡献/权限 | 高 | `POST /contributions`、`GET /admin/contributions`、`GET /teas/{id}`；S-34 | 游客、普通用户、管理员各一；存在在架茶 | ① 游客提交；② 普通用户访问审核队列；③ 普通用户提交科普并由管理员通过；④ 游客查茶详情 | ① 401/`40100`；② 403/`40300`；③ 200/`code=0`；④ `contributed_articles` 含该条（`contributor` 为提交者），未通过内容不出现 |

---

### 5.13 头像与个人中心（5 条）

| 编号 | 模块 | 优先级 | 对应接口/安全项 | 前置条件 | 操作步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| **TC-AVATAR-01** | 头像 | 高 | `POST /api/v1/me/avatar`、`PUT /api/v1/me/avatar`；S-35 | 无 Cookie | ① 未登录上传图片；② 未登录提交预置头像 | ① 401/`40100`；② 401/`40100`；均不写库、不落盘 |
| **TC-AVATAR-02** | 头像 | 高 | `POST /api/v1/me/avatar`；S-02/S-35 | 用户已登录；准备合法 PNG | ① 上传 PNG；② 查 `GET /auth/me`；③ 查磁盘与 `operation_logs` | ① 200/`code=0`，`data.avatar_url` 以 `/uploads/` 开头且 `.png` 结尾，响应不含 `password_hash`；② 返回同一 `avatar_url`；③ 文件实际落盘，新增 1 条 `avatar_update` 日志 |
| **TC-AVATAR-03** | 头像 | 高 | `POST /api/v1/me/avatar`；S-35 | 用户已登录 | ① 上传 `text/plain` 文件；② 上传伪造扩展名的文本文件（`.png` 但内容非图片） | ① 415/`41500`；② 415/`41500`（按魔数判定，不信任扩展名）；`users.avatar_url` 不变 |
| **TC-AVATAR-04** | 头像 | 中 | `POST /api/v1/me/avatar`；S-35 | 用户已登录 | ① 上传恰好 5 MB 的合法图片；② 上传 5 MB + 1 字节 | ① 200/`code=0`；② 413/`41300`，`avatar_url` 不变 |
| **TC-AVATAR-05** | 头像 | 中 | `PUT /api/v1/me/avatar`；S-35 | 用户已登录且已有上传头像 | ① 选择 `tea-03`；② 选择 `tea-99`；③ 请求体附加 `avatar_url` 字段 | ① 200/`code=0`，`avatar_url=/avatars/tea-03.svg`；② 400/`40000`（白名单）；③ 400/`40000`（`extra=forbid`）；②③ 均不改变现有头像 |

## 6. 覆盖矩阵与统计

### 6.1 用例数量

| 模块 | 用例数 | 编号区间 | 高 | 中 | 低 |
|---|---:|---|---:|---:|---:|
| 认证与会话 | 16 | TC-AUTH-01–16 | 10 | 6 | 0 |
| 茶品录入与上下架 | 7 | TC-TEA-01–07 | 3 | 4 | 0 |
| 筛选、搜索与分页 | 9 | TC-LIST-01–09 | 2 | 5 | 2 |
| 收藏与取消收藏 | 7 | TC-FAV-01–07 | 4 | 2 | 1 |
| 品鉴笔记 | 5 | TC-NOTE-01–05 | 3 | 2 | 0 |
| 分享链路 | 10 | TC-SHARE-01–10 | 6 | 4 | 0 |
| 权限校验 | 6 | TC-PERM-01–06 | 5 | 1 | 0 |
| 文件上传 | 5 | TC-UPLOAD-01–05 | 3 | 2 | 0 |
| 异常与防御 | 4 | TC-DEF-01–04 | 2 | 2 | 0 |
| 我的与个性化 | 6 | TC-ME-01–03、TC-REC-01–03 | 2 | 4 | 0 |
| 多清单 | 6 | TC-MLIST-01–06 | 4 | 2 | 0 |
| 用户贡献与审核 | 8 | TC-CONTRIB-01–08 | 6 | 2 | 0 |
| 头像与个人中心 | 5 | TC-AVATAR-01–05 | 3 | 2 | 0 |
| **合计** | **94** | — | **53** | **38** | **3** |

### 6.2 正向 / 反向 / 边界覆盖（按主要目的归类）

| 类型 | 数量 | 代表用例 |
|---|---:|---|
| 正向 | 34 | AUTH-01/04、TEA-01/05/07、LIST-01/02/05/08/09、FAV-01/03/06、NOTE-01/03、SHARE-01/05/08、PERM-04/05、UPLOAD-01/04、DEF-04、ME-02、REC-01/03、MLIST-01/05、CONTRIB-01/04/06/08、AVATAR-02 |
| 反向 | 38 | AUTH-02/05/06/07/10/11/13/14/15/16、TEA-02/06、LIST-04、FAV-05、NOTE-02/05、SHARE-03/04/06/07/09、PERM-01/02/03/06、UPLOAD-02/03/05、DEF-01/03、ME-01、REC-02、MLIST-02/04、CONTRIB-02/03、AVATAR-01/03/05 |
| 边界/并发 | 22 | AUTH-03/12、TEA-03/04、LIST-06/07、FAV-02/04/07、NOTE-04、SHARE-02/10、DEF-02、ME-03、MLIST-03/06、CONTRIB-05/07、AVATAR-04 |

### 6.3 强制覆盖项检查

| 要求 | 覆盖用例 | 是否覆盖 |
|---|---|---|
| 越权访问 | PERM-01、PERM-02、PERM-03、PERM-06、NOTE-05、SHARE-07、SHARE-09、MLIST-02 | ✅ |
| 并发重复提交 | FAV-02、FAV-04、SHARE-02、SHARE-10、MLIST-01、MLIST-06 | ✅ |
| 超长字段 | AUTH-03、TEA-04、LIST-06、NOTE-04、DEF-02 | ✅ |
| 非法枚举值 | TEA-02（category/season）、LIST-04（category/season/sort） | ✅ |
| 游客未登录访问分享 | SHARE-05（有效）、SHARE-04（撤销后） | ✅ |
| 分享撤销后访问 | SHARE-03、SHARE-04、SHARE-09 | ✅ |
| 管理员种子账号上线前改密 | DEF-04 | ✅ |
| 下架茶不可收藏、不出现在列表/搜索 | TEA-06、TEA-07、FAV-05 | ✅ |
| 密码不落响应/日志 | AUTH-01、AUTH-04、AUTH-09 | ✅ |
| 上传类型与大小 | UPLOAD-01、UPLOAD-02、UPLOAD-03 | ✅ |
| 贡献越权与重复审核 | CONTRIB-05、CONTRIB-06、CONTRIB-07、CONTRIB-08 | ✅ |
| 茶类矛盾与名称查重 | CONTRIB-02、CONTRIB-03 | ✅ |
| 头像上传类型/大小/白名单 | AVATAR-01、AVATAR-03、AVATAR-04、AVATAR-05 | ✅ |

### 6.4 与 SECURITY.md 控制编号的回溯

| 控制编号 | 对应用例 |
|---|---|
| S-01–S-05 密码与认证 | AUTH-01–AUTH-05、AUTH-09 |
| S-06–S-10 会话 | AUTH-01、AUTH-06–AUTH-09、AUTH-14–AUTH-16 |
| S-11–S-14 授权 | PERM-01–PERM-06、NOTE-05、SHARE-07、SHARE-09、UPLOAD-05 |
| S-15–S-18 分享与上下架 | SHARE-01–SHARE-10、TEA-06、TEA-07、FAV-05、LIST-09 |
| S-19–S-24 输入与上传 | AUTH-03、TEA-02–TEA-04、LIST-04、LIST-06、LIST-07、NOTE-04、UPLOAD-01–UPLOAD-05、DEF-01、DEF-02 |
| S-25–S-27 一致性/重复提交 | FAV-01–FAV-04、FAV-07、SHARE-02、SHARE-08、SHARE-10、LIST-01 |
| S-28–S-29 审计/日志 | TEA-01、TEA-05、AUTH-09、DEF-03、UPLOAD-01、PERM-05 |
| S-30–S-32 配置/上线/供应链 | DEF-01–DEF-04 |
| S-33 登录失败锁定 | AUTH-10–AUTH-13 |
| S-34 用户贡献与审核门禁 | CONTRIB-01–CONTRIB-08 |
| S-35 头像变更 | AVATAR-01–AVATAR-05 |

---

## 7. 执行顺序与回归集

### 7.1 执行顺序

1. **安全门禁批次（P0）**：PERM-01、PERM-02、PERM-06、AUTH-06、AUTH-09、UPLOAD-02、UPLOAD-03、SHARE-04、DEF-03、DEF-04。全部通过后才进入功能批次。
2. **认证主链路**：AUTH-01–AUTH-08、AUTH-14–AUTH-16。
3. **茶品与列表**：TEA-01–TEA-07、LIST-01–LIST-09。
4. **收藏/笔记/多清单**：FAV-01–FAV-07、NOTE-01–NOTE-05、MLIST-01–MLIST-06。
5. **分享链路**：SHARE-01–SHARE-10。
6. **上传与异常**：UPLOAD-01–UPLOAD-05、DEF-01–DEF-02。
7. **我的与个性化**：ME-01–ME-03、REC-01–REC-03。
8. **用户贡献与审核**：CONTRIB-01–CONTRIB-08。
9. **回归**：所有“高”优先级用例 + 本次变更涉及的模块用例。

### 7.2 每轮回归最小集

- 认证：AUTH-01、AUTH-05、AUTH-06、AUTH-10、AUTH-16。
- 权限：PERM-01、PERM-02、PERM-03。
- 数据归属：NOTE-05、SHARE-07、MLIST-02。
- 多清单：MLIST-01、MLIST-02、MLIST-06。
- 分享状态机：SHARE-03、SHARE-04、SHARE-05。
- 下架链路：TEA-06、FAV-05。
- 上传：UPLOAD-02、UPLOAD-03。
- 用户贡献：CONTRIB-02、CONTRIB-05、CONTRIB-06、CONTRIB-08。
- 上线检查：DEF-04。

---

## 8. 缺陷记录与判定

| 等级 | 定义 | 处理 |
|---|---|---|
| **S1 阻断** | 越权、密码泄露、管理员接口可被普通用户访问、撤销令牌复活、上传任意文件、数据丢失 | 立即停止发布，修复后重跑安全门禁批次 |
| **S2 严重** | 计数不一致、并发重复写入、下架茶仍可收藏/出现在列表、错误码/契约不符 | 发布前修复并回归相关模块 |
| **S3 一般** | 边界夹取不符、提示文案、排序次级键、日志格式 | 排期修复，可带风险发布 |
| **S4 建议** | 可观测性、性能优化、文档同步 | 记录待办 |

**缺陷单必填**：用例编号、接口路径、SECURITY 控制编号、环境、请求（脱敏）、响应（脱敏）、实际 DB 状态、期望结果、复现步骤、日志片段。

**禁止**：在缺陷单中粘贴明文密码、完整 Cookie、完整分享令牌、笔记正文；使用脱敏值或哈希前缀。

---

## 9. 不覆盖项与已知限制

| 项 | 说明 |
|---|---|
| API_CONTRACT §1.12 / PRD §2.3 明确不在范围内的能力 | 不设用例；契约中也不存在对应接口 |
| 第二阶段 S1–S17（S14/S15/S16 已提前实现，见 5.1/5.10） | 未实现项不设用例；仅在 SECURITY §3/§6 记录预留与风险 |
| 密码找回、邮箱/微信登录 | PRD FR-4.4 明确 MVP 不做 |
| S14 登录失败锁定 | 已提前实现，用例见 AUTH-10–AUTH-13（S-33） |
| 旧 Cookie 重放 | 已关闭：登出/改密均递增 `users.session_version`，旧 Cookie 立即 `40100`（AUTH-08、AUTH-16）；未登出期间被窃取的 Cookie 仍属残余风险 |
| 性能/吞吐/长时间稳定性 | 不在本方案内；并发用例只验证唯一性与幂等 |
| 前端 UI/兼容性/无障碍 | 不在本方案内；前端仅保留“守卫不是安全边界”的说明 |
| 渗透测试/漏洞扫描 | 不在本方案内；依赖 `pip-audit` / `npm audit` 与上线检查单 |

---

## 10. 变更记录

| 版本 | 日期 | 内容 |
|---|---|---|
| v1.0 | 2026-11-07 | 建立 60 条可执行用例，覆盖 9 个模块、正向/反向/边界、越权/并发/超长/非法枚举；逐条回溯 API 契约与 SECURITY 控制编号 |
| v1.1 | 2026-11-09 | 批次二：新增 AUTH-10–13（S14 登录锁定 / S-33）与 5.10 我的与个性化（ME-01–03、REC-01–03）；合计 70 条 |
| v1.2 | 2026-11-09 | 批次三 S9 多清单：新增 5.11 多清单（MLIST-01–06）；FAV-01/02/03、NOTE-01–05、PERM-03、SHARE-01 更新为多清单路径与断言；端点覆盖 40 个；合计 76 条（高 41 / 中 32 / 低 3） |
| v1.3 | 2026-11-09 | 批次四 S10–S13：新增 5.12 用户贡献与审核（CONTRIB-01–08）；覆盖端点 46 个；合计 84 条（高 47 / 中 34 / 低 3） |
| v1.4 | 2026-11-10 | ADR-0004 头像：新增 5.13 头像与个人中心（AVATAR-01–05）；S-02 校验范围补 `/me/avatar`；覆盖端点 48 个；合计 89 条（高 50 / 中 36 / 低 3） |
| v1.5 | 2026-11-11 | 自助修改密码：5.1 新增 AUTH-14–AUTH-16（旧密码错误、弱密码/新旧相同、改密后旧会话失效）；S-06–S-10 回溯补 AUTH-16；覆盖端点 49 个；合计 92 条（高 51 / 中 38 / 低 3） |
| v1.6 | 2026-11-11 | 管理员操作日志查询：5.7 新增 PERM-05（管理员分页/筛选/日期边界/字段完整）与 PERM-06（普通用户 403、游客 401、非法日期 400）；覆盖端点 50 个；合计 94 条（高 53 / 中 38 / 低 3） |
