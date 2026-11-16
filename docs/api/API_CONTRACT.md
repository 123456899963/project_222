# 茶·图鉴 —— 前后端 API 接口契约（API CONTRACT）

| 项 | 值 |
|---|---|
| 文档版本 | **v1.11** |
| 创建日期 | 2026-11-06 |
| 契约基线 | [PRD.md](../product/PRD.md) v1.1 · [DATA_MODEL.md](../architecture/DATA_MODEL.md) v1.4 · [database/init.sql](../../database/init.sql) · [MODULE_DESIGN.md](../architecture/MODULE_DESIGN.md) |
| 本契约地位 | 前后端联调与字段命名的唯一依据。脚手架中与本契约不一致的字段，以本契约（数据库列名）为准 |
| 覆盖范围 | MVP 业务接口 + 第二阶段已实施项（S1–S17） |
| 不覆盖 | 第二阶段能力；后端实现代码不在本次交付内 |
| 配套机器可读文件 | [openapi.yaml](openapi.yaml) |

---

## 1. 全局约定

### 1.1 访问前缀与路由

- 所有业务接口统一位于 **`/api/v1`**：`/api` 是统一访问前缀，`v1` 是为后续版本预留的版本段。
- 前端 Axios `baseURL` 固定为 `/api/v1`；开发期由 Vite 代理到 `http://127.0.0.1:8000`，生产期由 Nginx 同域反向代理，前后端同源。
- 业务路由分组：

| 前缀 | 业务模块 |
|---|---|
| `/api/v1/auth` | 注册、登录、退出、当前用户 |
| `/api/v1/teas` | 茶品列表、筛选、排序、分页、详情、首页数据 |
| `/api/v1/favorites` | 收藏与取消收藏 |
| `/api/v1/lists` | 我的多清单、标题、品鉴笔记 |
| `/api/v1/shares` | 分享链接生成、撤销、游客查看、一键收藏 |
| `/api/v1/admin` | 管理员茶品维护、上下架、小贴士、统计、图片上传 |
| `/api/v1/contents` | 内容板块：茶具 / 产地 / 文化 / 品牌 / 知识（含 `/content-types` 板块分类与 `/admin/contents` 后台维护） |

- 路径中的静态段必须先于动态段匹配（例如 `/teas/categories` 必须先于 `/teas/{tea_id}` 注册）。
- `/api/v1/health` 是部署探针，不返回统一业务响应体，**不属于本契约**。

### 1.2 请求与响应编码

| 项 | 约定 |
|---|---|
| 字符集 | UTF-8（无 BOM） |
| 普通请求/响应 | `Content-Type: application/json; charset=utf-8` |
| 文件上传 | `Content-Type: multipart/form-data` |
| JSON 字段命名 | `snake_case`，与数据库列名保持一致；派生字段在文档中注明 |
| 空值 | JSON `null`；不使用空字符串代替“未填写”（文本接口中空白字符串按 `null` 归一化） |
| 时间 | 见 §1.7 |
| HTTP 方法语义 | GET 查询、POST 创建/动作、PUT 全量更新、PATCH 局部状态切换、DELETE 取消/移除 |
| 成功状态码 | MVP 统一使用 **HTTP 200**；不使用 201/204，避免前端拦截器分裂 |
| 错误状态码 | 由业务码推导，见 §1.3、§1.4 |

### 1.3 统一响应结构

所有业务接口（含错误）均返回以下 JSON 结构：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | integer | 业务状态码；`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 可直接展示给用户的中文提示；错误时不包含堆栈、SQL、内部类名 |
| `data` | object / array / null | 成功时为业务数据；失败时固定为 `null` |

规则：

1. **成功判定只以 `code === 0` 为准**；HTTP 200 不代表业务成功。
2. 业务失败同时返回对应的 HTTP 状态码（`HTTP status = code // 100`），响应体仍为统一结构：

```json
{
  "code": 40401,
  "message": "该茶品暂不可用",
  "data": null
}
```

3. FastAPI 默认的 `422 Unprocessable Entity` 必须重映射为 **HTTP 400 + `code=40000`**，不得向前端泄露 Pydantic 原始错误结构。
4. 所有接口均可能返回 `code=50000`（HTTP 500）；下文各接口的错误表只列业务特定错误，不再重复 `50000`。
5. `data` 可以是对象、数组或 `null`；数组直接作为 `data`，不再额外包一层 `list` 字段。

### 1.4 业务状态码

| code | HTTP | 含义 | 典型触发 |
|---|---|---|---|
| `0` | 200 | 成功 | — |
| `40000` | 400 | 参数校验失败 | 枚举非法、必填缺失、长度/范围越界、JSON 结构错误 |
| `40100` | 401 | 未登录或登录已过期 | 无 Cookie、签名无效、超过 30 天 |
| `40110` | 401 | 用户名或密码错误 | 登录失败；不区分用户名不存在或密码错误 |
| `40300` | 403 | 无权限执行此操作 | 非管理员访问后台；非清单所有者撤销分享；所有者一键收藏自己的清单 |
| `40400` | 404 | 茶品不存在 | `tea_id` 无对应行 |
| `40401` | 404 | 该茶品暂不可用 | 茶品 `is_active=0`，公开详情/收藏被拒 |
| `40410` | 404 | 该分享已被撤销或不存在 | 分享 token 不存在 |
| `40420` | 404 | 清单不存在 | 访问/操作不属于当前用户的清单（S9） |
| `40430` | 404 | 收藏条目不存在 | 对未收藏的茶写品鉴笔记 |
| `40440` | 404 | 提交记录不存在 | 贡献提交不存在，或不属于当前用户（不泄露存在性） |
| `40900` | 409 | 该分享已被撤销 | 对已撤销 token 再次撤销或一键收藏 |
| `40910` | 409 | 用户名已存在 | 注册重名（大小写不敏感） |
| `41300` | 413 | 上传文件超过大小限制 | 文件大于 5 MB |
| `41500` | 415 | 不支持的文件类型 | 非 JPEG/PNG/WebP |
| `42900` | 429 | 尝试过于频繁 | S14 登录失败锁定：窗口内同一用户名或同一 IP 失败次数达到阈值 |
| `50000` | 500 | 服务器内部错误 | 未捕获异常；详情仅记录服务端日志 |

### 1.5 认证与会话（HttpOnly Cookie）

**本系统不使用 Token，不使用 `Authorization` 请求头。**

| 项 | 约定 |
|---|---|
| 凭证载体 | HttpOnly Cookie，名称固定为 **`tea_session`** |
| Cookie 值 | itsdangerous `URLSafeTimedSerializer` 签名的载荷 `{"uid": <users.id>, "sv": <users.session_version>}`，不含密码、角色、用户名；旧格式无 `sv` 的令牌按 0 处理 |
| 有效期 | 30 天（`Max-Age=2592000`，对应 `SESSION_EXPIRE_DAYS=30`） |
| 属性 | `HttpOnly=true`；`SameSite=Lax`；`Path=/`；生产环境 HTTPS 下 `Secure=true`，本地 HTTP 开发可关闭 |
| 域 | 不设置 `Domain`，使用同源主机级 Cookie |
| 服务端会话表 | MVP **不建** `sessions` 表；每次请求验签后按 `uid` 查 `users` |
| 传递方式 | 浏览器/前端自动携带；Axios 必须 `withCredentials: true`（已配置） |
| 登录 | `POST /auth/login` 校验成功后 `Set-Cookie: tea_session=...` |
| 注册 | `POST /auth/register` 成功后自动登录并 `Set-Cookie`（PRD FR-4.1） |
| 退出 | `POST /auth/logout` 删除 Cookie；携带有效 Cookie 时服务端递增 `users.session_version`，吊销该用户全部旧会话 |
| 失效 | 签名无效、过期、用户不存在、`sv` 与 `users.session_version` 不一致 → `40100`；前端提示“登录已过期”并弹登录面板 |
| 改密吊销 | `PUT /auth/password` 成功后 `session_version + 1`，该用户所有旧 Cookie 立即失效 |
| 角色 | `role` 每次从 `users.role` 读取；`admin` 才可访问 `/admin/*` |
| 跨域 | 前后端同源部署；开发期 CORS 允许配置内源并 `allow_credentials=true` |
| CSRF | MVP 依赖 `SameSite=Lax` + 同源部署；不额外下发 CSRF Token。若未来改为跨站 Cookie，必须补充 CSRF 防护 |
| 请求头 | 若客户端传入 `Authorization`，服务端忽略；不得以任何 Token 方案替代 Cookie |

`Set-Cookie` 示例（生产）：

```http
Set-Cookie: tea_session=<signed-value>; Path=/; Max-Age=2592000; HttpOnly; SameSite=Lax; Secure
```

### 1.6 分页

**分页仅用于茶品列表（公开列表、管理员列表）。**

| 参数 | 类型 | 默认 | 范围 | 说明 |
|---|---|---|---|---|
| `page` | integer | `1` | ≥ 1 | 页码，从 1 开始 |
| `page_size` | integer | **12** | 1–50 | 每页条数，默认 12 与 PRD FR-1.6 一致 |

- 越界值由服务端**夹取**而非报错：`page < 1 → 1`；`page_size < 1 → 1`；`page_size > 50 → 50`；响应中的 `page`、`page_size` 返回**实际生效值**。
- 分页响应统一放在 `data` 中：

```json
{
  "items": [],
  "total": 42,
  "page": 1,
  "page_size": 12
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `items` | array | 当前页数据；无结果时为 `[]` |
| `total` | integer | 满足筛选条件的总条数（不受分页影响） |
| `page` | integer | 实际生效页码 |
| `page_size` | integer | 实际生效每页条数 |

- `total_pages` 不单独返回，由前端计算：`Math.ceil(total / page_size)`；`total=0` 时为 0。
- 页码超出末页时返回 `items: []`，`total` 不变，HTTP 200、`code=0`。
- 所有分页排序必须有稳定次级键：`id DESC`，避免同秒数据跨页重复/遗漏。

### 1.7 日期时间格式

| 项 | 约定 |
|---|---|
| 传输格式 | **ISO 8601 UTC，秒级，带 `Z`**：`YYYY-MM-DDTHH:mm:ssZ`，例如 `"2026-11-06T12:00:00Z"` |
| 时区 | 数据库统一存 UTC（`DATETIME` + MySQL `time_zone='+00:00'`），API 不做本地时区换算 |
| 前端展示 | 前端按 `Asia/Shanghai` 渲染，展示逻辑不改变 API 值 |
| 精度 | 秒级（`DATETIME(0)`）；同秒排序使用 `id` 次级排序 |
| 输入 | MVP 没有客户端传入日期时间的接口；所有时间由服务端生成 |
| 字段 | `created_at`、`updated_at`、`revoked_at`、`favorited_at` 均遵循本格式 |

### 1.8 枚举与字典

| 字典 | API 值（数据库值） | 展示名 |
|---|---|---|
| `category` | `green` / `white` / `yellow` / `red` / `oolong` / `dark` / `reprocessed` | 绿茶 / 白茶 / 黄茶 / 红茶 / 乌龙茶 / 黑茶 / 再加工茶 |
| `season` | `明前` / `雨前` / `春茶` / `夏茶` / `秋茶` / `冬茶` | 同值 |
| `fermentation` | `不发酵` / `微发酵` / `半发酵` / `全发酵` / `后发酵` | 同值 |
| `role` | `user` / `admin` | 注册用户 / 管理员 |
| `sort` | `newest`（默认）/ `favorite` | 最新上架 / 收藏最多 |
| `share token` | 8 位 URL-safe 字符（`A-Z a-z 0-9 - _`），**大小写敏感** | 如 `k7X9m2Qa` |
| `contribution.type` | `new_tea` / `article` | 补充新茶 / 科普投稿 |
| `contribution.status` | `pending` / `approved` / `rejected` | 待审核 / 已通过 / 已拒绝 |

- `price_range` 在 PRD 中仅说明“5 档”，文案与边界未定稿，因此 API 保持 **字符串（≤32 字符）**，不在契约中硬编码档位；应用层校验，不建 ENUM。
- 枚举值非法一律 `40000`，不做静默丢弃。

### 1.9 文件上传与图片访问

| 项 | 约定 |
|---|---|
| 接口 | `POST /api/v1/admin/upload`，仅管理员 |
| 请求格式 | `multipart/form-data`，字段名固定为 **`file`** |
| 大小上限 | **5 MB**（5 × 1024 × 1024 字节），由 `MAX_UPLOAD_SIZE_MB` 控制 |
| 允许类型 | `image/jpeg`、`image/png`、`image/webp`；必须校验文件魔数（`python-magic`），不能只信扩展名/客户端 MIME |
| 禁止类型 | SVG、GIF、可执行文件及其他非图片类型 |
| 存储路径 | `uploads/{YYYY}/{MM}/{uuid}.{ext}`；扩展名由服务端按校验后的 MIME 决定，不采用原文件名 |
| 返回 | `data.url` 为**同源相对路径**：`/uploads/2026/11/<uuid>.jpg` |
| 访问方式 | 浏览器直接 `GET /uploads/{YYYY}/{MM}/{uuid}.{ext}`；无需登录。开发期 Vite 代理 `/uploads`，生产期 Nginx 反代/静态托管 |
| 写入字段 | 将返回的 `url` 写入茶品的 `main_image_url`；`main_image_url` 也允许历史外链 `https://...`（种子数据即外链） |
| 删除 | MVP **不提供**图片删除接口；茶品下架不删除图片 |
| 安全 | 上传文件不得按原文件名落盘；禁止路径穿越；返回头建议 `X-Content-Type-Options: nosniff` |

### 1.10 收藏计数 `teas.favorite_count` 的一致性

`favorite_count` 是**冗余统计列**，不是实时 `COUNT(favorite_items)`。接口返回的是该列的缓存值，语义如下：

1. **读取**：列表卡片、详情、热门推荐、收藏/取消响应、状态查询中的 `favorite_count` 均直接读 `teas.favorite_count`。
2. **写入**：收藏与取消必须在**同一事务**内完成条目变更与计数变更：
   - 新增收藏：`INSERT favorite_items` 成功后 `favorite_count = favorite_count + 1`；
   - 取消收藏：`DELETE favorite_items` 成功后 `favorite_count = GREATEST(favorite_count - 1, 0)`，下限保护为 0；
   - 批量一键收藏：先求“未收藏”差集，再批量插入，最后按差集数量一次性 `+N`；
   - 事务失败整体回滚，不出现“条目已写、计数未变”。
3. **防重复**：`favorite_items` 的 `UNIQUE(user_id, tea_id)` 是硬约束；重复收藏/重复取消按幂等处理，不重复加减计数。
4. **响应时点**：接口在事务提交后读取计数并返回，保证客户端拿到的值反映本次操作结果。
5. **对账兜底**：提供离线对账脚本/运维命令，按 `favorite_items` 分组重算并回写 `teas.favorite_count`；**不进入请求链路**。
6. **已知偏差**：`database/init.sql` 的种子 `favorite_count` 是演示热度值（如 2480），与 `favorite_items` 实际行数不相等；这是有意的演示数据，正式环境可通过对账归零/校准。
7. **下架茶品**：`is_active=0` 不会重置或删除计数；下架茶品的收藏保留，计数保留。

### 1.11 权限矩阵

| 能力 | 游客 | 注册用户 `role=user` | 管理员 `role=admin` |
|---|---|---|---|
| 茶品列表/筛选/排序/分页/详情/首页数据 | 允许 | 允许 | 允许 |
| 注册/登录/用户名可用性查询 | 允许 | 允许 | 允许 |
| 查看公开分享清单 | 允许 | 允许 | 允许 |
| 收藏/取消收藏/收藏状态 | 拒绝 40100 | 允许 | 允许 |
| 我的清单/改标题/写品鉴笔记 | 拒绝 40100 | 允许 | 允许 |
| 生成/撤销自己的分享 | 拒绝 40100 | 允许 | 允许 |
| 一键收藏他人分享 | 拒绝 40100 | 允许 | 允许 |
| 一键收藏自己的分享 | — | 拒绝 40300 | 拒绝 40300 |
| 管理员茶品维护/上下架/小贴士/统计/上传 | 拒绝 40100/40300 | 拒绝 40300 | 允许 |

- 管理员账号同时也是普通用户，可执行用户侧全部能力。
- 角色判定源为 `users.role`，不在 Cookie 中缓存。

### 1.12 明确不在本系统范围

以下业务**不存在对应接口**，契约中不得出现：

- 失物、拾物、认领、通知、消息、站内信；
- 举报、评论；用户贡献的富文本与图片上传（X7，仅接受纯文本）；
- 清单描述、用户管理、修改他人账号、密码找回、邮箱登录、微信扫码登录；
- 茶品物理删除（`DELETE /admin/teas/{id}` 不提供，只有上下架软失效）；
- 批量导入、茶品图片删除（分享海报为纯前端生成，无接口）。

> 用户贡献与审核（S10–S13）已在 v1.5 纳入契约，见 §4.8；多清单（S9）见 §4.4/§4.5。

---

## 2. 共享数据结构

以下结构在多个接口中复用。字段类型为 JSON 类型，`DB 来源`列说明其数据库对应关系。

### 2.1 `User`

| 字段 | 类型 | 说明 | DB 来源 |
|---|---|---|---|
| `id` | integer | 用户主键 | `users.id` |
| `username` | string | 用户名，3–20 字符 | `users.username` |
| `role` | string | `user` / `admin` | `users.role` |
| `avatar_url` | string \| null | 头像地址：`/uploads/...`（上传）或 `/avatars/tea-0X.svg`（预置）；未设置为 `null` | `users.avatar_url` |
| `created_at` | datetime | 注册时间（UTC） | `users.created_at` |

> 统一使用 `id`，不使用 `user_id`。`password_hash` 永不返回。

示例：

```json
{
  "id": 12,
  "username": "teafan",
  "role": "user",
  "avatar_url": "/avatars/tea-03.svg",
  "created_at": "2026-11-06T12:00:00Z"
}
```

### 2.2 `TeaListItem`（公开列表卡片）

| 字段 | 类型 | 说明 | DB 来源 |
|---|---|---|---|
| `id` | integer | 茶品主键 | `teas.id` |
| `name` | string | 茶品名称 | `teas.name` |
| `category` | string | 七大茶类枚举 | `teas.category` |
| `origin` | string | 完整产地“省 市 产区” | `teas.origin` |
| `season` | string / null | 采摘季节 | `teas.season` |
| `main_image_url` | string / null | 主图 URL 或 `/uploads/...` | `teas.main_image_url` |
| `favorite_count` | integer | 冗余收藏计数（缓存值） | `teas.favorite_count` |

示例：

```json
{
  "id": 1,
  "name": "西湖龙井",
  "category": "green",
  "origin": "浙江 杭州 西湖狮峰",
  "season": "明前",
  "main_image_url": "https://images.unsplash.com/photo-1563822249366-3efb23b8e0c9?w=600&h=400&fit=crop",
  "favorite_count": 2480
}
```

### 2.3 `TeaDetail`

在 `TeaListItem` 基础上增加以下字段：

| 字段 | 类型 | 说明 | DB 来源 |
|---|---|---|---|
| `fermentation` | string / null | 发酵程度 | `teas.fermentation` |
| `price_range` | string / null | 价格区间文案（≤32 字符） | `teas.price_range` |
| `price_min` | integer / null | 价格下限（元/斤，S2）；null 表示未维护，不参与价格筛选 | `teas.price_min` |
| `price_max` | integer / null | 价格上限（元/斤，S2）；null 表示未维护 | `teas.price_max` |
| `representative_variety` | string / null | 代表品类 | `teas.representative_variety` |
| `shape_desc` | string | 外形描述 | `teas.shape_desc` |
| `soup_desc` | string | 汤色描述 | `teas.soup_desc` |
| `aroma_desc` | string | 香气描述 | `teas.aroma_desc` |
| `taste_desc` | string | 滋味描述 | `teas.taste_desc` |
| `water_temp` | number / null | 水温（摄氏度，70.0–100.0） | `teas.water_temp` |
| `tea_amount` | number / null | 投茶量（克） | `teas.tea_amount` |
| `brew_time` | number / null | 浸泡时间（秒） | `teas.brew_time` |
| `video_url` | string / null | 视频介绍（本站 `/uploads/videos/...`）；null 时前端隐藏视频区 | `teas.video_url` |
| `video_duration` | integer / null | 视频时长（秒，≤180） | `teas.video_duration` |
| `image_set` | string[] | 图片集 URL 列表，按 `sort_order` 升序，最多 9 条；空数组隐藏缩略图行 | `tea_media.image_url` |
| `is_active` | boolean | 是否上架；公开详情恒为 `true` | `teas.is_active` |
| `created_at` | datetime | 创建/上架时间 | `teas.created_at` |
| `updated_at` | datetime | 最近编辑时间 | `teas.updated_at` |
| `tips_history` | string / null | 历史典故 | `tea_tips.history` |
| `tips_suitable` | string / null | 适合人群 | `tea_tips.suitable` |
| `tips_misconception` | string / null | 冲泡误区 | `tea_tips.misconception` |
| `tips_official_note` | string / null | 官方品鉴笔记 | `tea_tips.official_note` |
| `brewing_guide` | object / null | 分步冲泡教程（ADR-0005）；`null` 表示未维护，前端退回三格速查卡 | `tea_brewing_guides` |
| `contributed_articles` | `TeaArticle[]` | 已通过审核的用户科普投稿（S11/S12），按提交时间倒序；空数组隐藏 | `contributions`（type=article 且 status=approved） |

说明：

- 四个 `tips_*` 字段为**扁平化派生字段**；`tea_tips` 无对应行时全部为 `null`。
- `brewing_guide` 为 1:1 扩展对象：`{ intro, steps[], caution }`，`steps` 为 3–8 条 `{ title, detail, tip }`；无教程时为 `null`。
- 任一 `tips_*` 为 `null` 时，前端整块隐藏（PRD FR-3.2 / FR-6.4）。
- 公开详情接口遇到 `is_active=0` 直接返回 `40401`，因此公开响应中 `is_active` 恒为 `true`；管理员详情可能为 `false`。

示例：

```json
{
  "id": 1,
  "name": "西湖龙井",
  "category": "green",
  "origin": "浙江 杭州 西湖狮峰",
  "season": "明前",
  "fermentation": "不发酵",
  "price_range": null,
  "representative_variety": "群体种",
  "shape_desc": "扁平光滑，色翠略黄，形似雀舌",
  "soup_desc": "嫩绿明亮，清澈见底",
  "aroma_desc": "豆香清雅，热香馥郁，冷香幽兰",
  "taste_desc": "鲜爽甘醇，回甘明显，有淡淡的板栗香",
  "water_temp": 85.0,
  "tea_amount": 3.0,
  "brew_time": 90.0,
  "main_image_url": "https://images.unsplash.com/photo-1563822249366-3efb23b8e0c9?w=600&h=400&fit=crop",
  "is_active": true,
  "favorite_count": 2480,
  "created_at": "2026-11-06T12:00:00Z",
  "updated_at": "2026-11-06T12:00:00Z",
  "tips_history": "西湖龙井始于唐代，是中国十大名茶之首，狮峰产区为核心原产地。",
  "tips_suitable": "适合脾胃强健、喜鲜爽口感的茶友；春季饮用尤佳。",
  "tips_misconception": "水温不宜过高，85℃即可，沸水会烫熟嫩芽导致苦涩。",
  "tips_official_note": "采摘标准为一芽一叶或一芽二叶初展，炒制工艺独特。",
  "brewing_guide": {
    "intro": "绿茶重在鲜爽，用玻璃杯，水温不宜过高，不闷盖、快出汤。",
    "steps": [
      {
        "title": "温杯洁具",
        "detail": "先用热水把玻璃杯烫洗一遍并倒掉，提升杯温便于闻香。",
        "tip": "不要用洗洁精，清水烫洗即可。"
      },
      {
        "title": "投茶",
        "detail": "取 3g 茶叶放入杯中，约占杯底薄薄一层。",
        "tip": "口味偏淡可从 2g 开始。"
      },
      {
        "title": "注水",
        "detail": "用 85℃ 热水沿杯壁缓慢注入至七分满，不要直冲茶叶。",
        "tip": "水烧开后开盖晾 2–3 分钟约 85℃。"
      }
    ],
    "caution": "不要用刚烧开的沸水直冲，也不要盖盖子闷泡。"
  },
  "contributed_articles": [
    {
      "id": 8,
      "title": "龙井的冲泡小记",
      "content": "建议使用玻璃杯，85℃水温，先注水三分之一再投茶……",
      "contributor": "teafan",
      "created_at": "2026-11-09T10:00:00Z"
    }
  ]
}
```

#### 2.3.1 `TeaArticle`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer | 贡献记录 ID（`contributions.id`） |
| `title` | string / null | 标题，可为空 |
| `content` | string | 纯文本正文，3–500 字 |
| `contributor` | string | 投稿用户名 |
| `created_at` | datetime | 投稿时间（UTC） |

### 2.3.2 `CategoryCount` / `OriginCount`

| 结构 | 字段 | 类型 | 说明 |
|---|---|---|---|
| `CategoryCount` | `category` | string | 七大茶类值，顺序固定 `green, white, yellow, red, oolong, dark, reprocessed` |
| | `count` | integer | 已上架数量；无收录返回 0 |
| `OriginCount` | `origin` | string | **省级名称**（从 `teas.origin` 第一个空格前的片段派生），如“浙江” |
| | `count` | integer | 该省已上架数量 |

### 2.4 `FavoriteState`

| 字段 | 类型 | 说明 |
|---|---|---|
| `tea_id` | integer | 茶品主键 |
| `is_favorited` | boolean | 当前用户是否已收藏（任一清单命中即为 `true`） |
| `favorite_count` | integer | `teas.favorite_count` 缓存值 |
| `list_ids` | integer[] | S9：该茶所在清单 ID 列表，空数组表示未收藏 |

### 2.5 `ListItem` / `ListData` / `ShareBrief`

`ListItem`（仅清单所有者可见，含私有笔记）：

| 字段 | 类型 | 说明 | DB 来源 |
|---|---|---|---|
| `tea_id` | integer | 茶品主键（条目业务键） | `favorite_items.tea_id` |
| `name` | string | 茶品名称 | `teas.name` |
| `category` | string | 茶类 | `teas.category` |
| `origin` | string | 产地 | `teas.origin` |
| `season` | string / null | 采摘季节 | `teas.season` |
| `main_image_url` | string / null | 主图 | `teas.main_image_url` |
| `favorite_count` | integer | 茶品收藏计数（缓存） | `teas.favorite_count` |
| `is_available` | boolean | 茶品是否仍在架；`false` 时前端灰显占位 | 派生自 `teas.is_active` |
| `tasting_note` | string / null | 私有品鉴笔记；`null` 表示未写 | `favorite_items.tasting_note` |
| `favorited_at` | datetime | 收藏时间 | `favorite_items.created_at` |

> `favorite_items.id` 是内部主键，不作为条目业务键暴露；条目操作用 `tea_id`。

`ShareBrief`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `token` | string | 当前生效分享短码 |
| `url` | string | 前端路由 `/c/{token}`（相对路径） |
| `created_at` | datetime | 令牌生成时间 |

`ListSummary`（§4.4.1 清单摘要）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer | `collection_lists.id` |
| `title` | string | 清单标题 |
| `is_default` | boolean | 是否默认清单（每用户仅一个） |
| `tea_count` | integer | 清单条目总数（含已下架占位） |
| `created_at` | datetime | 清单创建时间 |
| `updated_at` | datetime | 清单最近更新时间 |
| `share` | `ShareBrief` / null | 该清单当前生效分享 |

`ListData`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer | `collection_lists.id` |
| `title` | string | 清单标题 |
| `is_default` | boolean | 是否默认清单 |
| `tea_count` | integer | 清单条目总数（含已下架占位） |
| `created_at` | datetime | 清单创建时间 |
| `updated_at` | datetime | 清单最近更新时间 |
| `share` | `ShareBrief` / null | 当前生效分享；无则为 `null` |
| `items` | `ListItem[]` | 全部条目，按 `favorited_at DESC, tea_id DESC` 排序 |

### 2.6 `ShareViewItem` / `ShareViewData`

`ShareViewItem`（游客可见，**绝不含 `tasting_note`**）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `tea_id` | integer | 茶品主键 |
| `name` | string | 茶品名称 |
| `category` | string | 茶类 |
| `origin` | string | 产地 |
| `season` | string / null | 采摘季节 |
| `main_image_url` | string / null | 主图 |
| `favorite_count` | integer | 收藏计数（缓存） |
| `is_available` | boolean | 是否在架；下架条目灰显 |

`ShareViewData`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `token` | string | 分享短码 |
| `title` | string | 清单标题（动态读 `collection_lists.title`） |
| `tea_count` | integer | 有效分享为条目总数（含下架占位）；已撤销时为 `0` |
| `created_at` | datetime | 分享令牌创建时间 |
| `revoked` | boolean | `true` 表示已被撤销；此时 `items=[]` |
| `is_owner` | boolean | 当前请求者是否为清单所有者；游客恒 `false` |
| `items` | `ShareViewItem[]` | 有效分享时为条目列表；撤销时为空 |

### 2.7 `AdminTeaListItem`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer | `teas.id` |
| `name` | string | 茶品名称 |
| `category` | string | 茶类 |
| `origin` | string | 产地 |
| `season` | string / null | 采摘季节 |
| `main_image_url` | string / null | 主图 |
| `is_active` | boolean | 上架状态（后台可见下架） |
| `favorite_count` | integer | 收藏计数缓存 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 最近编辑时间 |

### 2.8 `AdminStats`

| 字段 | 类型 | 说明 |
|---|---|---|
| `total_count` | integer | 茶品总数（含下架） |
| `active_count` | integer | 上架数 |
| `inactive_count` | integer | 下架数 |
| `category_distribution` | `CategoryCount[]` | 七大茶类分布（含下架），顺序固定，缺失补 0 |

### 2.9 `UploadResult`

| 字段 | 类型 | 说明 |
|---|---|---|
| `url` | string | 同源相对路径 `/uploads/YYYY/MM/<uuid>.<ext>` |
| `original_filename` | string | 客户端原文件名，仅用于展示，不参与落盘 |
| `size` | integer | 文件字节数 |
| `content_type` | string | 服务端校验后的 MIME，如 `image/jpeg` |

---

## 3. 接口总览

| # | 模块 | 方法 | 路径 | 权限 |
|---|---|---|---|---|
| 1 | 认证 | GET | `/auth/username-availability` | 游客 |
| 2 | 认证 | POST | `/auth/register` | 游客 |
| 3 | 认证 | POST | `/auth/login` | 游客 |
| 4 | 认证 | POST | `/auth/logout` | 任意 |
| 5 | 认证 | GET | `/auth/me` | 登录用户 |
| 6 | 认证 | PUT | `/auth/password` | 登录用户 |
| 7 | 我的 | GET | `/me/stats` | 登录用户 |
| 8 | 我的 | POST | `/me/avatar` | 登录用户 |
| 9 | 我的 | PUT | `/me/avatar` | 登录用户 |
| 10 | 茶品 | GET | `/teas` | 游客 |
| 11 | 茶品 | GET | `/teas/categories` | 游客 |
| 12 | 茶品 | GET | `/teas/origins` | 游客 |
| 13 | 茶品 | GET | `/teas/hot` | 游客 |
| 14 | 茶品 | GET | `/teas/random` | 游客 |
| 15 | 茶品 | GET | `/teas/recommended` | 游客（可选 Cookie） |
| 16 | 茶品 | GET | `/teas/{tea_id}` | 游客 |
| 17 | 茶品 | GET | `/teas/{tea_id}/images` | 游客 |
| 18 | 茶品 | GET | `/teas/{tea_id}/related` | 游客 |
| 19 | 小贴士 | GET | `/tips/latest` | 游客 |
| 20 | 收藏 | POST | `/favorites/{tea_id}` | 登录用户 |
| 21 | 收藏 | DELETE | `/favorites/{tea_id}` | 登录用户 |
| 22 | 收藏 | GET | `/favorites/{tea_id}/status` | 登录用户 |
| 23 | 清单 | GET | `/lists` | 登录用户 |
| 24 | 清单 | POST | `/lists` | 登录用户 |
| 25 | 清单 | GET | `/lists/{list_id}` | 登录用户（所有者） |
| 26 | 清单 | PUT | `/lists/{list_id}` | 登录用户（所有者） |
| 27 | 清单 | DELETE | `/lists/{list_id}` | 登录用户（所有者） |
| 28 | 清单 | PUT | `/lists/{list_id}/notes/{tea_id}` | 登录用户（所有者） |
| 29 | 分享 | POST | `/shares/generate` | 登录用户 |
| 30 | 分享 | POST | `/shares/revoke/{token}` | 登录用户（所有者） |
| 31 | 分享 | GET | `/shares/{token}` | 游客（可选 Cookie） |
| 32 | 分享 | POST | `/shares/{token}/copy` | 登录用户（非所有者） |
| 33 | 管理员 | GET | `/admin/teas` | 管理员 |
| 34 | 管理员 | GET | `/admin/teas/{tea_id}` | 管理员 |
| 35 | 管理员 | POST | `/admin/teas` | 管理员 |
| 36 | 管理员 | PUT | `/admin/teas/{tea_id}` | 管理员 |
| 37 | 管理员 | PATCH | `/admin/teas/{tea_id}/toggle` | 管理员 |
| 38 | 管理员 | PUT | `/admin/teas/{tea_id}/tips` | 管理员 |
| 39 | 管理员 | GET | `/admin/stats` | 管理员 |
| 40 | 管理员 | POST | `/admin/upload` | 管理员 |
| 41 | 管理员 | POST | `/admin/media/video` | 管理员 |
| 42 | 管理员 | POST | `/admin/teas/{tea_id}/images` | 管理员 |
| 43 | 管理员 | DELETE | `/admin/teas/{tea_id}/images/{image_id}` | 管理员 |
| 44 | 管理员 | GET | `/admin/contributions` | 管理员 |
| 45 | 管理员 | POST | `/admin/contributions/{contribution_id}/approve` | 管理员 |
| 46 | 管理员 | POST | `/admin/contributions/{contribution_id}/reject` | 管理员 |
| 47 | 贡献 | POST | `/contributions` | 登录用户 |
| 48 | 贡献 | GET | `/contributions/mine` | 登录用户 |
| 49 | 贡献 | DELETE | `/contributions/{contribution_id}` | 登录用户（本人） |
| 50 | 内容 | GET | `/content-types` | 游客 |
| 51 | 内容 | GET | `/contents` | 游客 |
| 52 | 内容 | GET | `/contents/{item_id}` | 游客 |
| 53 | 内容管理 | GET | `/admin/contents` | 管理员 |
| 54 | 内容管理 | POST | `/admin/contents` | 管理员 |
| 55 | 内容管理 | GET | `/admin/contents/{item_id}` | 管理员 |
| 56 | 内容管理 | PUT | `/admin/contents/{item_id}` | 管理员 |
| 57 | 内容管理 | DELETE | `/admin/contents/{item_id}` | 管理员 |
| 58 | 管理员 | GET | `/admin/operation-logs` | 管理员 |
| 59 | 管理员 | PUT | `/admin/teas/{tea_id}/brewing-guide` | 管理员 |
| 60 | 管理员 | DELETE | `/admin/teas/{tea_id}/brewing-guide` | 管理员 |

> 清单条目移除不单独提供 `DELETE /lists/{tea_id}`，统一复用 `DELETE /favorites/{tea_id}`（可带 `?list_id`），避免同一语义两个入口。

---

## 4. 接口详情

### 4.1 认证模块

#### 4.1.1 用户名可用性查询

- **方法与路径**：`GET /auth/username-availability`
- **权限**：游客
- **用途**：PRD FR-4.1 用户名实时唯一校验，供注册面板防抖调用。
- **查询参数**：

| 参数 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `username` | string | 是 | 3–20 字符，`^[A-Za-z0-9\u4e00-\u9fa5]{3,20}$`，服务端 trim |

- **请求体**：无
- **成功响应**：HTTP 200，`code=0`

```json
{
  "code": 0,
  "message": "ok",
  "data": { "username": "teafan", "available": true }
}
```

| data 字段 | 类型 | 说明 |
|---|---|---|
| `username` | string | 归一化（trim）后的用户名 |
| `available` | boolean | 是否可注册；已占用为 `false`（不是错误） |

- **错误**：`40000` 格式/长度非法。
- **规则**：用户名唯一性大小写不敏感（`utf8mb4_unicode_ci`），`TeaFan` 与 `teafan` 视为同名；本接口不创建用户、不下发 Cookie。

#### 4.1.2 注册

- **方法与路径**：`POST /auth/register`
- **权限**：游客
- **请求体**：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `username` | string | 是 | 3–20 字符，中文/英文/数字，trim 后校验 |
| `password` | string | 是 | 6–64 字符；不 trim；bcrypt 哈希存储，永不回显 |

- **请求示例**：

```json
{ "username": "teafan", "password": "tea2026" }
```

- **成功响应**：HTTP 200，`code=0`，`data` 为 `User`，同时 `Set-Cookie: tea_session=...`（30 天）

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 12,
    "username": "teafan",
    "role": "user",
    "created_at": "2026-11-06T12:00:00Z"
  }
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | 用户名/密码长度或字符集非法 |
| 409 | 40910 | 用户名已存在（大小写不敏感） |

- **规则**：注册成功即自动登录（PRD FR-4.1），返回 `Set-Cookie`；默认清单不在注册时创建，而是在首次 `GET /lists` 时惰性创建；密码使用 bcrypt（cost=10）。

#### 4.1.3 登录

- **方法与路径**：`POST /auth/login`
- **权限**：游客（管理员也使用同一入口）
- **请求体**：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `username` | string | 是 | 1–32 字符，trim |
| `password` | string | 是 | 1–64 字符，不 trim |

- **成功响应**：HTTP 200，`code=0`，`data` 为 `User`，`Set-Cookie: tea_session=...`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "created_at": "2026-11-06T12:00:00Z"
  }
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | 字段缺失/超长 |
| 401 | 40110 | 用户名不存在或密码错误（统一提示，不区分） |
| 429 | 42900 | 15 分钟窗口内同一用户名或同一 IP 失败 ≥ 5 次（S14 锁定） |

- **规则**：
  - S14 锁定：先判定锁定再校验账号，锁定期间正确密码同样返回 `42900`，不泄露账号是否存在；窗口滚动过期后自动解锁。
  - 每次登录顺带清理 24 小时前的失败记录；成功登录清空该用户名的失败记录（IP 维度保留到自然过期）。
  - 成功登录覆盖旧 Cookie；`role` 由数据库读取。

#### 4.1.4 退出登录

- **方法与路径**：`POST /auth/logout`
- **权限**：任意（未登录调用也返回成功，幂等）
- **请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data=null`，并 `Set-Cookie: tea_session=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax`

```json
{ "code": 0, "message": "ok", "data": null }
```

- **错误**：无业务错误；`50000` 除外。
- **规则**：
  - 携带有效 `tea_session` 时，服务端将 `users.session_version + 1` 并提交事务，该用户全部旧 Cookie 立即失效（后续请求 `40100`）。
  - 未登录或 Cookie 无效时不做数据库操作，仅清除客户端 Cookie，接口保持幂等。
  - 因无 `sessions` 表，吊销粒度为用户级：登出会使该用户所有设备会话失效。

#### 4.1.5 当前用户信息

- **方法与路径**：`GET /auth/me`
- **权限**：登录用户（Cookie 自动携带）
- **查询参数/请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为 `User`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "created_at": "2026-11-06T12:00:00Z"
  }
}
```

- **错误**：`40100`（无 Cookie、签名无效、过期、用户已被删除、会话版本不匹配）。
- **规则**：`role` 实时读 `users.role`；前端据此显示管理入口。

#### 4.1.6 修改密码

- **方法与路径**：`PUT /auth/password`
- **权限**：登录用户（Cookie 自动携带）
- **请求体**（`extra=forbid`）：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `old_password` | string | 是 | 1–64 字符；bcrypt 校验，永不回显 |
| `new_password` | string | 是 | 6–64 字符，规则与注册完全一致；不得与 `old_password` 相同 |

- **请求示例**：

```json
{ "old_password": "tea2026", "new_password": "tea2027" }
```

- **成功响应**：HTTP 200，`code=0`，`data=null`；同时 `Set-Cookie: tea_session=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax`

```json
{ "code": 0, "message": "ok", "data": null }
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | `new_password` 长度非法、字段缺失、包含额外字段、新旧密码相同 |
| 401 | 40100 | 未登录、Cookie 无效/过期、会话版本已失效 |
| 401 | 40110 | `old_password` 错误（复用登录凭证错误码，不区分具体原因） |

- **规则**：
  - 成功后 `password_hash` 更新、`users.session_version + 1`，同一事务提交；该用户所有旧 Cookie（`sv` 不匹配）立即失效，需重新登录。
  - 响应清除当前 `tea_session` Cookie（HttpOnly / SameSite=Lax / Path=/ 与登录一致）。
  - 旧密码校验失败时不修改密码、不递增 `session_version`。

---

### 4.2 茶品模块

#### 4.2.1 茶品列表（筛选 + 排序 + 分页）

- **方法与路径**：`GET /teas`
- **权限**：游客
- **查询参数**：

| 参数 | 类型 | 必填 | 默认 | 约束与语义 |
|---|---|---|---|---|
| `category` | string | 否 | — | 逗号分隔枚举，如 `green,oolong`；同维度多选为 OR |
| `origin` | string | 否 | — | 逗号分隔**省级名称**，如 `浙江,福建`；按 `origin` 前缀匹配（`浙江%`）；同维度 OR |
| `season` | string | 否 | — | 逗号分隔枚举，如 `明前,春茶`；同维度 OR |
| `fermentation` | string | 否 | — | 逗号分隔枚举（S2）：`不发酵/微发酵/半发酵/全发酵/后发酵`；同维度 OR |
| `price_min` | integer | 否 | — | 价格下限（元/斤，S2），≥0；与 `price_max` 按区间**交集**匹配（`price_max >= price_min 且 price_min <= price_max`） |
| `price_max` | integer | 否 | — | 价格上限（元/斤，S2），≥0；与 `price_min` 同时提供时 `price_min ≤ price_max` |
| `filter_mode` | string | 否 | `and` | `and` / `or`（S1）：跨维度组合方式；同维度内部始终 OR |
| `keyword` | string | 否 | — | 1–50 字符；对 `name`、`origin` 做 `LIKE %词%`，空串忽略 |
| `sort` | string | 否 | `newest` | `newest`（创建时间倒序）/ `favorite`（收藏数倒序） |
| `page` | integer | 否 | `1` | ≥1；越界夹取 |
| `page_size` | integer | 否 | **12** | 1–50；越界夹取；默认值对应 PRD FR-1.6 |

- **过滤逻辑**：默认不同维度之间 AND（茶类 AND 产地 AND 季节 AND 发酵 AND 价格 AND 关键词）；`filter_mode=or` 时茶类/产地/季节/发酵之间改为 OR（S1），关键词仍为独立 AND 叠加；同维度多选始终 OR（PRD FR-1.2）。未维护价格（`price_min`/`price_max` 为 null）的茶品不命中任何价格区间筛选。
- **请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为分页结构：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 1,
        "name": "西湖龙井",
        "category": "green",
        "origin": "浙江 杭州 西湖狮峰",
        "season": "明前",
        "main_image_url": "https://images.unsplash.com/photo-1563822249366-3efb23b8e0c9?w=600&h=400&fit=crop",
        "favorite_count": 2480
      }
    ],
    "total": 42,
    "page": 1,
    "page_size": 12
  }
}
```

| data 字段 | 类型 | 说明 |
|---|---|---|
| `items` | `TeaListItem[]` | 当前页；无结果 `[]` |
| `total` | integer | 过滤后总数 |
| `page` | integer | 实际页码 |
| `page_size` | integer | 实际每页条数 |

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | `category`/`season`/`fermentation`/`sort`/`filter_mode` 非法枚举，`price_min`/`price_max` 为负或倒置，或 `keyword` 超过 50 字符 |

- **规则**：
  - 只返回 `is_active=1` 的茶品；下架茶品在列表/搜索/推荐中完全隐藏（PRD FR-6.3）。
  - 排序：`newest` → `created_at DESC, id DESC`；`favorite` → `favorite_count DESC, created_at DESC, id DESC`。
  - 无结果时返回空数组，不报错（PRD 空状态由前端渲染）。
  - 产地筛选面向省级选项（PRD FR-1.1）；`teas.origin` 存储为“省 市 产区”，服务端取第一个空格前片段作为省份并做前缀匹配。

#### 4.2.2 七大茶类计数

- **方法与路径**：`GET /teas/categories`
- **权限**：游客
- **参数/请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为 `CategoryCount[]`，固定六项且顺序固定：

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    { "category": "green", "count": 18 },
    { "category": "white", "count": 0 },
    { "category": "yellow", "count": 2 },
    { "category": "red", "count": 5 },
    { "category": "oolong", "count": 7 },
    { "category": "dark", "count": 3 }
  ]
}
```

- **错误**：无业务错误；`50000` 除外。
- **规则**：只统计 `is_active=1`；无茶类的茶类返回 `count=0`（PRD FR-2.1“暂无收录”），不省略。

#### 4.2.3 产地选项

- **方法与路径**：`GET /teas/origins`
- **权限**：游客
- **参数/请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为 `OriginCount[]`，按 `count DESC, origin ASC`：

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    { "origin": "福建", "count": 12 },
    { "origin": "浙江", "count": 8 },
    { "origin": "云南", "count": 3 }
  ]
}
```

- **错误**：无业务错误；`50000` 除外。
- **规则**：只统计 `is_active=1`；`origin` 值为**省级名称**（`teas.origin` 第一段），不是完整产地；前端筛选用该值传 `GET /teas?origin=浙江`。

#### 4.2.4 热门推荐

- **方法与路径**：`GET /teas/hot`
- **权限**：游客
- **查询参数**：

| 参数 | 类型 | 必填 | 默认 | 约束 |
|---|---|---|---|---|
| `limit` | integer | 否 | `8` | 1–20；越界夹取；PRD FR-2.2 固定展示前 8 |

- **请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为 `TeaListItem[]`：

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    {
      "id": 5,
      "name": "大红袍",
      "category": "oolong",
      "origin": "福建 武夷山 九龙窠",
      "season": "春茶",
      "main_image_url": "https://images.unsplash.com/photo-1597481499750-3e6b22637e12?w=600&h=400&fit=crop",
      "favorite_count": 3120
    }
  ]
}
```

- **错误**：`40000`（`limit` 非整数）。
- **规则**：只取 `is_active=1`；按热度权重排序（S17）：`7 天内收藏数 × 3 + favorite_count` 降序，次级键 `favorite_count DESC, id DESC`；数据不足 8 条时返回实际条数，不补占位。

#### 4.2.5 随机发现

- **方法与路径**：`GET /teas/random`
- **权限**：游客
- **查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `exclude_id` | integer | 否 | 排除的茶品 ID，用于“换一批”避免重复 |

- **请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为 `TeaDetail` 或 `null`：

```json
{
  "code": 0,
  "message": "ok",
  "data": { "id": 3, "name": "君山银针", "category": "yellow", "...": "..." }
}
```

- **错误**：`40000`（`exclude_id` 非整数）。
- **规则**：仅从 `is_active=1` 中随机取 1 条（MVP 完全随机，无个性化）；无可选茶品时 `data=null`（HTTP 200），前端显示占位。

#### 4.2.6 茶品详情

- **方法与路径**：`GET /teas/{tea_id}`
- **权限**：游客
- **路径参数**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `tea_id` | integer | 是 | 茶品主键 |

- **请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为 `TeaDetail`（字段见 §2.3；含四个扁平 `tips_*`）

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 1,
    "name": "西湖龙井",
    "category": "green",
    "origin": "浙江 杭州 西湖狮峰",
    "season": "明前",
    "fermentation": "不发酵",
    "price_range": null,
    "representative_variety": "群体种",
    "shape_desc": "扁平光滑，色翠略黄，形似雀舌",
    "soup_desc": "嫩绿明亮，清澈见底",
    "aroma_desc": "豆香清雅，热香馥郁，冷香幽兰",
    "taste_desc": "鲜爽甘醇，回甘明显，有淡淡的板栗香",
    "water_temp": 85.0,
    "tea_amount": 3.0,
    "brew_time": 90.0,
    "main_image_url": "https://images.unsplash.com/photo-1563822249366-3efb23b8e0c9?w=600&h=400&fit=crop",
    "video_url": "/uploads/videos/2026/11/1a2b3c4d5e6f708192a3b4c5d6e7f8a9.mp4",
    "video_duration": 96,
    "image_set": [
      "/uploads/2026/11/8f3c2b1a4d5e6f708192a3b4c5d6e7f8.jpg",
      "/uploads/2026/11/2c4d6e8f0a1b3c5d7e9f1a3b5c7d9e1f.jpg"
    ],
    "is_active": true,
    "favorite_count": 2480,
    "created_at": "2026-11-06T12:00:00Z",
    "updated_at": "2026-11-06T12:00:00Z",
    "tips_history": "西湖龙井始于唐代，是中国十大名茶之首，狮峰产区为核心原产地。",
    "tips_suitable": "适合脾胃强健、喜鲜爽口感的茶友；春季饮用尤佳。",
    "tips_misconception": "水温不宜过高，85℃即可，沸水会烫熟嫩芽导致苦涩。",
    "tips_official_note": "采摘标准为一芽一叶或一芽二叶初展，炒制工艺独特。"
  }
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 404 | 40400 | `tea_id` 不存在 |
| 404 | 40401 | 茶品已下架（PRD 例外：旧链接访问） |

- **规则**：下架茶品不返回详情数据；前端展示“该茶品暂不可用”+ 同类替代引导；`tips_*` 为空的区块由前端隐藏，不返回空占位对象。
- **内容扩展字段（ADR-0003，v1.1 追加）**：
  - `video_url`：`string | null`。本站 `/uploads/videos/...` 路径；为 `null` 时前端整块隐藏视频区，不渲染空播放器。
  - `video_duration`：`integer | null`。秒，服务端解析并校验 ≤180。
  - `image_set`：`string[]`。按 `sort_order` 升序的图片 URL 列表；最多 9 条；为空数组时前端隐藏缩略图行。

#### 4.2.7 茶品图片集

- **方法与路径**：`GET /teas/{tea_id}/images`
- **权限**：游客
- **路径参数**：`tea_id`（integer，必填）
- **请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为数组，按 `sort_order` 升序、同序按 `id` 升序：

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    { "id": 1, "image_url": "/uploads/2026/11/a.jpg", "sort_order": 0 },
    { "id": 2, "image_url": "/uploads/2026/11/b.jpg", "sort_order": 1 }
  ]
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 404 | 40400 | `tea_id` 不存在 |
| 404 | 40401 | 茶品已下架 |

- **规则**：无图片集时返回空数组 `[]`，不返回 404；数据与 `TeaDetail.image_set` 同源。

#### 4.2.8 相关推荐（S6）

- **方法与路径**：`GET /teas/{tea_id}/related`
- **权限**：游客
- **查询参数**：

| 参数 | 类型 | 必填 | 默认 | 约束与语义 |
|---|---|---|---|---|
| `limit` | integer | 否 | `4` | 1–8；越界夹取 |

- **请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为 `TeaListItem[]`。
- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 404 | 40400 | `tea_id` 不存在 |
| 404 | 40401 | 茶品已下架 |

- **规则**：排除自身与下架茶品；同茶类优先 → 同产地（省级）次之 → 热门（`favorite_count`）兜底；结果去重，条数不足时返回实际数量。

#### 4.2.9 最新小贴士（S7）

- **方法与路径**：`GET /tips/latest`
- **权限**：游客
- **查询参数**：

| 参数 | 类型 | 必填 | 默认 | 约束与语义 |
|---|---|---|---|---|
| `limit` | integer | 否 | `3` | 1–6；越界夹取 |

- **请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为 `LatestTipItem[]`，按 `tea_tips.updated_at DESC、tea_id DESC` 排序：

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    {
      "tea_id": 1,
      "tea_name": "西湖龙井",
      "category": "green",
      "summary": "采摘标准为一芽一叶或一芽二叶初展，炒制工艺独特。",
      "updated_at": "2026-11-06T12:00:00Z"
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `tea_id` | integer | 茶品 ID |
| `tea_name` | string | 茶品名称 |
| `category` | string | 茶类枚举 |
| `summary` | string | 小贴士摘要：取官方备注→适合人群→历史→误区的首个非空项，超过 80 字截断加「…」 |
| `updated_at` | datetime | 小贴士最近更新时间（ISO8601 UTC 带 Z） |

- **规则**：只取 `is_active=1` 且四项小贴士至少一项非空的茶品；无有效摘要的记录跳过。

---

#### 4.2.10 个性化推荐（S16）

- **方法与路径**：`GET /teas/recommended`
- **权限**：游客（可选 Cookie；登录用户按收藏偏好推荐）
- **查询参数**：

| 参数 | 类型 | 必填 | 默认 | 约束与语义 |
|---|---|---|---|---|
| `limit` | integer | 否 | `1` | 1–8；越界夹取 |
| `exclude_id` | integer | 否 | 无 | 排除指定茶品（首页“换一款”）；不存在或已下架时忽略 |

- **请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为 `TeaListItem[]`（字段同 §4.2.1 列表项）
- **规则**：
  - 登录且已有收藏：按收藏茶类分布加权随机，优先返回**未收藏**的同茶类茶品；
  - 未登录 / 无收藏 / 偏好茶类候选耗尽：回退完全随机（返回 1 条）；
  - 两种路径都必须排除 `exclude_id`；无其他可选茶品时返回空数组；
  - 仅返回 `is_active=1` 的茶品；无可选茶品时 `data` 为空数组。

---

### 4.3 收藏模块

> S9 起支持多清单：收藏可指定目标清单，`teas.favorite_count` 按「用户 × 茶品」跨清单去重。

#### 4.3.1 收藏茶品

- **方法与路径**：`POST /favorites/{tea_id}`
- **权限**：登录用户（`user` / `admin`）
- **路径参数**：`tea_id` integer，必填
- **请求体**（可选）：`{ "list_id": 7 }`；缺省或 `null` 时归入默认清单
- **成功响应**：HTTP 200，`code=0`，`data` 为 `FavoriteState`：

```json
{
  "code": 0,
  "message": "ok",
  "data": { "tea_id": 1, "is_favorited": true, "favorite_count": 2481, "list_ids": [7] }
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | 请求体结构非法 |
| 401 | 40100 | 未登录/会话过期 |
| 404 | 40400 | 茶品不存在 |
| 404 | 40401 | 茶品已下架，不可收藏 |
| 404 | 40420 | `list_id` 不存在或不属于当前用户 |

- **规则**：
  - **幂等**：同一清单内已收藏时再次调用不新增行、不重复计数。
  - 同一茶品可加入多个清单；`favorite_count` 只在用户**首次**收藏该茶（跨清单无记录）时 +1（见 §1.10）。
  - 依赖 `UNIQUE(list_id, tea_id)` 防并发重复；撞唯一冲突按“已收藏”处理，不返回 409。

#### 4.3.2 取消收藏

- **方法与路径**：`DELETE /favorites/{tea_id}`
- **权限**：登录用户
- **路径参数**：`tea_id` integer，必填
- **查询参数**：`list_id` integer，可选；传入时仅移除该清单条目，不传时移除该茶在所有清单中的条目
- **成功响应**：HTTP 200，`code=0`，`data` 为 `FavoriteState`：

```json
{
  "code": 0,
  "message": "ok",
  "data": { "tea_id": 1, "is_favorited": false, "favorite_count": 2480, "list_ids": [] }
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 401 | 40100 | 未登录/会话过期 |
| 404 | 40400 | 茶品不存在 |
| 404 | 40420 | `list_id` 不存在或不属于当前用户 |

- **规则**：
  - **幂等**：未收藏时调用仍返回成功，计数不变。
  - **不校验 `is_active`**：已下架茶品仍需可从清单中移除。
  - 仅当该茶在用户所有清单中的最后一条被移除时，才 `favorite_count = GREATEST(favorite_count - 1, 0)`。

#### 4.3.3 查询收藏状态

- **方法与路径**：`GET /favorites/{tea_id}/status`
- **权限**：登录用户
- **路径参数**：`tea_id` integer，必填
- **成功响应**：HTTP 200，`code=0`，`data` 为 `FavoriteState`：

```json
{
  "code": 0,
  "message": "ok",
  "data": { "tea_id": 1, "is_favorited": true, "favorite_count": 2480, "list_ids": [7, 9] }
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 401 | 40100 | 未登录/会话过期 |
| 404 | 40400 | 茶品不存在 |

- **规则**：允许查询已下架茶品的收藏状态；`list_ids` 为该茶所在全部清单。

---

### 4.4 清单与品鉴笔记模块

> S9 多清单：每用户有且仅有一个默认清单（`is_default=1`），其余为非默认清单；
> 单账号最多 **10 个**清单；默认清单不可删除。访问他人清单统一返回 `40420`。

#### 4.4.1 获取我的全部清单

- **方法与路径**：`GET /lists`
- **权限**：登录用户
- **参数/请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为 `ListSummary[]`（默认清单置顶，其余按创建时间升序）：

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    { "id": 7, "title": "我的收藏", "is_default": true, "tea_count": 2,
      "created_at": "2026-11-06T12:00:00Z", "updated_at": "2026-11-06T12:00:00Z",
      "share": null }
  ]
}
```

- **错误**：`40100`。
- **规则**：首次调用自动创建默认清单（标题“我的收藏”），`UNIQUE(user_id, is_default)` 保证并发下只成功一次。

#### 4.4.2 新建清单

- **方法与路径**：`POST /lists`
- **权限**：登录用户
- **请求体**：`{ "title": "办公室茶单" }`（trim 后 2–20 字符）
- **成功响应**：HTTP 200，`code=0`，`data` 为新建的 `ListSummary`（`is_default=false`）。
- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | 标题缺失/长度越界/纯空白；或清单数已达 10 个 |
| 401 | 40100 | 未登录/会话过期 |

#### 4.4.3 获取清单详情

- **方法与路径**：`GET /lists/{list_id}`
- **权限**：登录用户（清单所有者）
- **成功响应**：HTTP 200，`code=0`，`data` 为 `ListData`（含 `items` 与 `share`）。
- **错误**：`40100`；`40420`（清单不存在或不属于当前用户）。
- **规则**：
  - `items` 不分页，按 `favorited_at DESC, tea_id DESC`。
  - `is_available=false` 表示茶已下架，条目仍保留并灰显。
  - `share` 为该清单当前生效令牌；已撤销不返回。

#### 4.4.4 更新清单标题

- **方法与路径**：`PUT /lists/{list_id}`
- **权限**：登录用户（清单所有者）
- **请求体**：`{ "title": "我的私房茶单" }`（trim 后 2–20 字符）
- **成功响应**：

```json
{ "code": 0, "message": "ok",
  "data": { "id": 7, "title": "我的私房茶单", "is_default": true, "updated_at": "2026-11-06T12:30:00Z" } }
```

- **错误**：`40000`（标题非法）；`40100`；`40420`（清单不存在/越权）。
- **规则**：默认清单与非默认清单均可改名；分享访问时标题动态读取。

#### 4.4.5 删除清单

- **方法与路径**：`DELETE /lists/{list_id}`
- **权限**：登录用户（清单所有者）
- **成功响应**：HTTP 200，`code=0`，`data=null`。
- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | 尝试删除默认清单 |
| 401 | 40100 | 未登录/会话过期 |
| 404 | 40420 | 清单不存在或不属于当前用户 |

- **规则**：
  - 仅非默认清单可删除；默认清单不可删除。
  - 清单内条目**迁移到默认清单**，不丢数据；若默认清单已存在同一茶品，则合并为一条，
    默认清单已有笔记优先，否则继承被删清单的笔记。
  - 该清单的分享令牌随清单级联删除，旧链接立即返回 `40410`。

#### 4.4.6 保存品鉴笔记

- **方法与路径**：`PUT /lists/{list_id}/notes/{tea_id}`
- **权限**：登录用户（清单所有者）
- **路径参数**：`list_id`、`tea_id` integer，必填
- **请求体**：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `content` | string / null | 是 | 可为 `null`；上限 **20,000 字符**；纯空白归一化为 `null` |

- **成功响应**：

```json
{ "code": 0, "message": "ok",
  "data": { "tea_id": 1, "list_id": 7, "tasting_note": "第一泡豆香突出，第三泡回甘明显。" } }
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | `content` 缺失/类型非法/超过 20,000 字符 |
| 401 | 40100 | 未登录/会话过期 |
| 404 | 40420 | 清单不存在或不属于当前用户 |
| 404 | 40430 | 该茶品不在当前清单中 |

- **规则**：笔记写入 `favorite_items.tasting_note`，仅本人可读写；分享接口**不返回**笔记；清空笔记不删除条目。

---

### 4.5 分享模块

#### 4.5.1 生成分享链接

- **方法与路径**：`POST /shares/generate`
- **权限**：登录用户（清单所有者）
- **请求体**（可选）：`{ "list_id": 9 }`；缺省或 `null` 时分享默认清单（不再接收 `title`，标题取 `collection_lists.title`）
- **成功响应**：HTTP 200，`code=0`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "token": "k7X9m2Qa",
    "url": "/c/k7X9m2Qa",
    "created_at": "2026-11-06T12:00:00Z",
    "is_new": true
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `token` | string | 8 位 URL-safe 短码，大小写敏感（`utf8mb4_bin`），全局唯一 |
| `url` | string | 前端分享页相对路径 `/c/{token}`；前端自行拼接站点域名 |
| `created_at` | datetime | 令牌生成时间 |
| `is_new` | boolean | `true` 新建；`false` 复用已有生效令牌（派生字段，无 DB 列） |

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | 请求体结构非法 |
| 401 | 40100 | 未登录/会话过期 |
| 404 | 40420 | `list_id` 不存在或不属于当前用户 |

- **规则**：
  - 按清单生成：每个清单最多一条生效令牌，不同清单令牌互相独立。
  - 若目标清单已有 `is_active=1` 的令牌则**复用**，不产生重复令牌；否则新建。
  - 令牌无过期时间，永久有效，除非显式撤销（PRD FR-5.4）。
  - 撤销后旧令牌不可复活；再次生成必须新建令牌。
  - 生成前若默认清单不存在，先惰性创建。

#### 4.5.2 撤销分享

- **方法与路径**：`POST /shares/revoke/{token}`
- **权限**：登录用户，且必须是该令牌所属清单的所有者
- **路径参数**：`token` string，8 位短码，大小写敏感
- **请求体**：无
- **成功响应**：HTTP 200，`code=0`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "token": "k7X9m2Qa",
    "is_active": false,
    "revoked_at": "2026-11-06T12:30:00Z"
  }
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 401 | 40100 | 未登录/会话过期 |
| 403 | 40300 | 令牌属于其他用户 |
| 404 | 40410 | 令牌不存在 |
| 409 | 40900 | 令牌已撤销 |

- **规则**：撤销为软失效：`is_active=0` + `revoked_at`，行永久保留；撤销不可逆（PRD FR-5.5）；不物理删除令牌。

#### 4.5.3 查看公开分享清单

- **方法与路径**：`GET /shares/{token}`
- **权限**：游客（无需登录；若携带 Cookie 则用于计算 `is_owner`）
- **路径参数**：`token` string，8 位短码，大小写敏感
- **请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为 `ShareViewData`

有效分享：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "token": "k7X9m2Qa",
    "title": "我的收藏",
    "tea_count": 2,
    "created_at": "2026-11-06T12:00:00Z",
    "revoked": false,
    "is_owner": false,
    "items": [
      {
        "tea_id": 1,
        "name": "西湖龙井",
        "category": "green",
        "origin": "浙江 杭州 西湖狮峰",
        "season": "明前",
        "main_image_url": "https://images.unsplash.com/photo-1563822249366-3efb23b8e0c9?w=600&h=400&fit=crop",
        "favorite_count": 2480,
        "is_available": true
      }
    ]
  }
}
```

已撤销分享（HTTP 200，通过 `revoked=true` 表达，便于前端展示明确文案）：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "token": "k7X9m2Qa",
    "title": "我的收藏",
    "tea_count": 0,
    "created_at": "2026-11-06T12:00:00Z",
    "revoked": true,
    "is_owner": false,
    "items": []
  }
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 404 | 40410 | 令牌不存在 |

- **规则**：
  - 公开只读；不返回品鉴笔记、不返回所有者身份信息。
  - 下架茶品保留条目并返回 `is_available=false`，前端灰显占位（PRD FR-5 例外）。
  - 撤销后的分享返回 `revoked=true`、`items=[]`、`tea_count=0`，前端展示“该分享已被撤销”+ 引导浏览公开推荐。
  - `is_owner` 供前端隐藏“一键收藏全部”按钮；游客恒 `false`。

#### 4.5.4 一键收藏全部

- **方法与路径**：`POST /shares/{token}/copy`
- **权限**：登录用户；**不能是清单所有者本人**
- **路径参数**：`token` string，8 位短码
- **请求体**：无
- **成功响应**：HTTP 200，`code=0`

```json
{
  "code": 0,
  "message": "ok",
  "data": { "added": 3, "skipped": 1, "total": 4 }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `added` | integer | 本次新增到当前用户清单的茶品数 |
| `skipped` | integer | 跳过的条目数（已收藏 + 已下架不可收藏） |
| `total` | integer | 分享中的条目总数 |

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 401 | 40100 | 未登录/会话过期 |
| 403 | 40300 | 当前用户是清单所有者 |
| 404 | 40410 | 令牌不存在 |
| 409 | 40900 | 令牌已撤销 |

- **规则**：
  - 只收藏 `is_active=1` 的茶；下架茶计入 `skipped`，不创建收藏。
  - 先查当前用户已收藏集合，求差集后批量插入；只对差集数量递增 `favorite_count`，同事务完成（DATA_MODEL §6.3）。
  - 幂等：重复调用时 `added=0`，已存在条目全部进入 `skipped`。
  - 当前用户无默认清单时先惰性创建。

---

### 4.6 管理员模块

所有 `/admin/*` 接口要求 `users.role=admin`；未登录返回 `40100`，已登录但非管理员返回 `40300`。

#### 4.6.1 茶品列表（管理视角）

- **方法与路径**：`GET /admin/teas`
- **权限**：管理员
- **查询参数**：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `category` | string | 否 | — | 逗号分隔茶类 |
| `keyword` | string | 否 | — | 1–50 字符，匹配名称/产地 |
| `is_active` | boolean | 否 | — | 省略=全部；`true` 只看上架；`false` 只看下架 |
| `sort` | string | 否 | `newest` | `newest` / `favorite` |
| `page` | integer | 否 | `1` | 同 §1.6 |
| `page_size` | integer | 否 | `12` | 同 §1.6，最大 50 |

- **请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为分页结构，`items` 为 `AdminTeaListItem[]`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 1,
        "name": "西湖龙井",
        "category": "green",
        "origin": "浙江 杭州 西湖狮峰",
        "season": "明前",
        "main_image_url": "https://images.unsplash.com/photo-1563822249366-3efb23b8e0c9?w=600&h=400&fit=crop",
        "is_active": true,
        "favorite_count": 2480,
        "created_at": "2026-11-06T12:00:00Z",
        "updated_at": "2026-11-06T12:00:00Z"
      }
    ],
    "total": 6,
    "page": 1,
    "page_size": 12
  }
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | 枚举/布尔/分页非法 |
| 401 | 40100 | 未登录/会话过期 |
| 403 | 40300 | 非管理员 |

- **规则**：后台列表**包含下架茶品**；公开过滤条件不加 `is_active=1`；排序次级键 `id DESC`。

#### 4.6.2 茶品详情（管理视角）

- **方法与路径**：`GET /admin/teas/{tea_id}`
- **权限**：管理员
- **路径参数**：`tea_id` integer，必填
- **请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为 `TeaDetail`，`is_active` 可能为 `false`，`tips_*` 可为 `null`
- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 401 | 40100 | 未登录/会话过期 |
| 403 | 40300 | 非管理员 |
| 404 | 40400 | 茶品不存在 |

- **规则**：下架茶品仍可编辑，故本接口不返回 `40401`。

#### 4.6.3 新增茶品

- **方法与路径**：`POST /admin/teas`
- **权限**：管理员
- **请求体**（`application/json`）：

| 字段 | 类型 | 必填 | 约束 | DB 列 |
|---|---|---|---|---|
| `name` | string | 是 | trim 后 1–100 字符 | `teas.name` |
| `category` | string | 是 | 七类枚举 | `teas.category` |
| `origin` | string | 是 | 1–200 字符，“省 市 产区” | `teas.origin` |
| `season` | string / null | 否 | 六值枚举或 `null` | `teas.season` |
| `fermentation` | string / null | 否 | 五值枚举或 `null` | `teas.fermentation` |
| `price_range` | string / null | 否 | ≤32 字符，文案待定 | `teas.price_range` |
| `representative_variety` | string / null | 否 | ≤100 字符 | `teas.representative_variety` |
| `shape_desc` | string | 是 | 非空 | `teas.shape_desc` |
| `soup_desc` | string | 是 | 非空 | `teas.soup_desc` |
| `aroma_desc` | string | 是 | 非空 | `teas.aroma_desc` |
| `taste_desc` | string | 是 | 非空 | `teas.taste_desc` |
| `water_temp` | number | 是 | 70.0–100.0，1 位小数 | `teas.water_temp` |
| `tea_amount` | number | 是 | >0 且 ≤999.9，1 位小数 | `teas.tea_amount` |
| `brew_time` | number | 是 | >0 且 ≤999.9，1 位小数 | `teas.brew_time` |
| `main_image_url` | string | 是 | ≤500 字符；`http(s)://` 外链或 `/uploads/...` | `teas.main_image_url` |
| `video_url` | string / null | 否 | ≤500 字符；**必须**为本站 `/uploads/` 路径（禁止第三方外链）；空/纯空白归一化为 `null` | `teas.video_url` |
| `video_duration` | integer / null | 否 | 1–180 秒 | `teas.video_duration` |
| `tips_history` | string / null | 否 | 空/纯空白归一化为 `null` | `tea_tips.history` |
| `tips_suitable` | string / null | 否 | 同上 | `tea_tips.suitable` |
| `tips_misconception` | string / null | 否 | 同上 | `tea_tips.misconception` |
| `tips_official_note` | string / null | 否 | 同上 | `tea_tips.official_note` |

- **不接受**：`is_active`（创建后默认上架）、`favorite_count`（服务端维护）、`id`。
- **请求示例**：

```json
{
  "name": "碧螺春",
  "category": "green",
  "origin": "江苏 苏州 洞庭山",
  "season": "明前",
  "fermentation": "不发酵",
  "price_range": "100-500",
  "representative_variety": "群体种",
  "shape_desc": "条索纤细，卷曲成螺，满披白毫",
  "soup_desc": "嫩绿明亮",
  "aroma_desc": "花果香浓郁",
  "taste_desc": "鲜爽甘醇，回甘持久",
  "water_temp": 80.0,
  "tea_amount": 3.0,
  "brew_time": 60.0,
  "main_image_url": "/uploads/2026/11/8f3c2b1a.jpg",
  "tips_history": "碧螺春产于苏州太湖洞庭山，已有千年历史。",
  "tips_suitable": null,
  "tips_misconception": null,
  "tips_official_note": null
}
```

- **成功响应**：HTTP 200，`code=0`，`data` 为完整 `TeaDetail`（`is_active=true`，`favorite_count=0`）：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 7,
    "name": "碧螺春",
    "category": "green",
    "origin": "江苏 苏州 洞庭山",
    "season": "明前",
    "fermentation": "不发酵",
    "price_range": "100-500",
    "representative_variety": "群体种",
    "shape_desc": "条索纤细，卷曲成螺，满披白毫",
    "soup_desc": "嫩绿明亮",
    "aroma_desc": "花果香浓郁",
    "taste_desc": "鲜爽甘醇，回甘持久",
    "water_temp": 80.0,
    "tea_amount": 3.0,
    "brew_time": 60.0,
    "main_image_url": "/uploads/2026/11/8f3c2b1a.jpg",
    "is_active": true,
    "favorite_count": 0,
    "created_at": "2026-11-06T12:00:00Z",
    "updated_at": "2026-11-06T12:00:00Z",
    "tips_history": "碧螺春产于苏州太湖洞庭山，已有千年历史。",
    "tips_suitable": null,
    "tips_misconception": null,
    "tips_official_note": null
  }
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | 必填缺失、枚举/数值/长度非法 |
| 401 | 40100 | 未登录/会话过期 |
| 403 | 40300 | 非管理员 |

- **规则**：
  - 必填校验由前后端双重保障（PRD FR-6.1），后端为准。
  - 若提供任一 `tips_*`，创建对应 `tea_tips` 行；全为 `null` 时可不建行，读取时四个字段统一返回 `null`（等价）。
  - 写入 `operation_logs`：`action='create_tea'`、`target_type='tea'`、`target_id=新 id`、`detail` 为名称摘要。

#### 4.6.4 编辑茶品

- **方法与路径**：`PUT /admin/teas/{tea_id}`
- **权限**：管理员
- **路径参数**：`tea_id` integer，必填
- **请求体**：与 §4.6.3 的茶品主体字段一致（全部必填/选填规则相同），但 **不接受 `tips_*`**：

  - 必填：`name`、`category`、`origin`、`shape_desc`、`soup_desc`、`aroma_desc`、`taste_desc`、`water_temp`、`tea_amount`、`brew_time`、`main_image_url`。
  - 选填：`season`、`fermentation`、`price_range`、`representative_variety`、`video_url`、`video_duration`；**省略或 `null` 均写为 `NULL`**（PUT 全量替换语义）。
  - 不可改：`id`、`is_active`（用 toggle）、`favorite_count`。
- **请求示例**：

```json
{
  "name": "西湖龙井",
  "category": "green",
  "origin": "浙江 杭州 西湖狮峰",
  "season": "明前",
  "fermentation": "不发酵",
  "price_range": "500-1000",
  "representative_variety": "群体种",
  "shape_desc": "扁平光滑，色翠略黄，形似雀舌",
  "soup_desc": "嫩绿明亮，清澈见底",
  "aroma_desc": "豆香清雅，热香馥郁，冷香幽兰",
  "taste_desc": "鲜爽甘醇，回甘明显，有淡淡的板栗香",
  "water_temp": 85.0,
  "tea_amount": 3.0,
  "brew_time": 90.0,
  "main_image_url": "https://images.unsplash.com/photo-1563822249366-3efb23b8e0c9?w=600&h=400&fit=crop"
}
```

- **成功响应**：HTTP 200，`code=0`，`data` 为更新后的完整 `TeaDetail`（`tips_*` 保持原值）
- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | 字段校验失败 |
| 401 | 40100 | 未登录/会话过期 |
| 403 | 40300 | 非管理员 |
| 404 | 40400 | 茶品不存在 |

- **规则**：
  - 编辑即时生效，无审核（PRD FR-6.2）。
  - 小贴士不由本接口修改，走 §4.6.6。
  - `updated_at` 由数据库 `ON UPDATE CURRENT_TIMESTAMP` / ORM 自动更新。
  - 写入 `operation_logs`：`action='update_tea'`、`target_id=tea_id`、`detail` 为名称摘要。

#### 4.6.5 茶品上下架

- **方法与路径**：`PATCH /admin/teas/{tea_id}/toggle`
- **权限**：管理员
- **路径参数**：`tea_id` integer，必填
- **请求体**：无（每次调用翻转当前 `is_active`）
- **成功响应**：HTTP 200，`code=0`

```json
{
  "code": 0,
  "message": "ok",
  "data": { "id": 1, "is_active": false, "updated_at": "2026-11-06T12:30:00Z" }
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 401 | 40100 | 未登录/会话过期 |
| 403 | 40300 | 非管理员 |
| 404 | 40400 | 茶品不存在 |

- **规则**：
  - 上架：恢复列表/搜索/推荐/详情可见；下架：前台全部隐藏，但用户清单保留条目并灰显（PRD FR-6.3）。
  - **不物理删除**茶品、不删除收藏、不重置 `favorite_count`、不删除图片。
  - 下架后旧详情链接返回 `40401`；分享视图返回 `is_available=false`；一键收藏跳过。
  - 写入 `operation_logs`：`action='toggle_tea'`，`detail` 含切换方向摘要。

#### 4.6.6 编辑官方小贴士

- **方法与路径**：`PUT /admin/teas/{tea_id}/tips`
- **权限**：管理员
- **路径参数**：`tea_id` integer，必填
- **请求体**（四个字段均可选、可为 `null`）：

| 字段 | 类型 | 必填 | 语义 |
|---|---|---|---|
| `tips_history` | string / null | 否 | 省略=保持原值；`null`/纯空白=清空该区块 |
| `tips_suitable` | string / null | 否 | 同上 |
| `tips_misconception` | string / null | 否 | 同上 |
| `tips_official_note` | string / null | 否 | 同上 |

- **请求示例**（只清空“冲泡误区”）：

```json
{ "tips_misconception": null }
```

- **成功响应**：HTTP 200，`code=0`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "tea_id": 1,
    "tips_history": "西湖龙井始于唐代……",
    "tips_suitable": "适合脾胃强健……",
    "tips_misconception": null,
    "tips_official_note": "采摘标准为一芽一叶……"
  }
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | 字段类型非 string/null |
| 401 | 40100 | 未登录/会话过期 |
| 403 | 40300 | 非管理员 |
| 404 | 40400 | 茶品不存在 |

- **规则**：
  - 四个区块可独立编辑/清空（PRD FR-6.4）；`tea_tips` 无行时按本次提交 upsert。
  - 清空后公开详情对应 `tips_*` 返回 `null`，前端隐藏该块。
  - 写入 `operation_logs`：`action='update_tea'`、`target_id=tea_id`、`detail` 标注 tips 更新。

#### 4.6.7 仪表盘统计

- **方法与路径**：`GET /admin/stats`
- **权限**：管理员
- **参数/请求体**：无
- **成功响应**：HTTP 200，`code=0`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "total_count": 6,
    "active_count": 6,
    "inactive_count": 0,
    "category_distribution": [
      { "category": "green", "count": 1 },
      { "category": "white", "count": 1 },
      { "category": "yellow", "count": 1 },
      { "category": "red", "count": 1 },
      { "category": "oolong", "count": 1 },
      { "category": "dark", "count": 1 }
    ]
  }
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 401 | 40100 | 未登录/会话过期 |
| 403 | 40300 | 非管理员 |

- **规则**：`category_distribution` 统计全部茶品（含下架），固定六项顺序，缺失补 0；数量与 `teas` 表一致。

#### 4.6.8 图片上传

- **方法与路径**：`POST /admin/upload`
- **权限**：管理员
- **请求格式**：`multipart/form-data`
- **表单字段**：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `file` | binary | 是 | JPEG/PNG/WebP；≤5 MB；非空 |

- **请求示例（curl）**：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/admin/upload \
  -b "tea_session=<cookie>" \
  -F "file=@/path/to/tea.jpg"
```

- **成功响应**：HTTP 200，`code=0`，`data` 为 `UploadResult`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "url": "/uploads/2026/11/8f3c2b1a4d5e6f708192a3b4c5d6e7f8.jpg",
    "original_filename": "tea.jpg",
    "size": 204800,
    "content_type": "image/jpeg"
  }
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | `file` 缺失、空文件 |
| 401 | 40100 | 未登录/会话过期 |
| 403 | 40300 | 非管理员 |
| 413 | 41300 | 文件超过 5 MB |
| 415 | 41500 | 类型不在 JPEG/PNG/WebP，或魔数校验失败 |
| 500 | 50000 | 磁盘写入失败 |

- **规则**：
  - 文件名使用 UUID，扩展名由服务端 MIME 决定；不保留原文件名落盘。
  - 图片访问见 §1.9：同源 `GET /uploads/...`，无需认证。
  - 写入 `operation_logs`：`action='upload_image'`、`target_type='tea'`、`target_id=null`、`detail` 为文件名/大小摘要。
  - 不提供茶品删除接口；图片集条目的删除见 §4.6.11（v1.1 追加）。

#### 4.6.9 视频上传

- **方法与路径**：`POST /admin/media/video`
- **权限**：管理员
- **请求格式**：`multipart/form-data`
- **表单字段**：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `file` | binary | 是 | MP4/MOV；≤50 MB；时长 ≤180 秒；非空 |

- **成功响应**：HTTP 200，`code=0`，`data` 为 `VideoUploadResult`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "url": "/uploads/videos/2026/11/1a2b3c4d5e6f708192a3b4c5d6e7f8a9.mp4",
    "original_filename": "intro.mp4",
    "size": 20971520,
    "content_type": "video/mp4",
    "duration": 96
  }
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | `file` 缺失、空文件、无法解析视频时长 |
| 400 | 40000 | 时长超过 180 秒 |
| 401 | 40100 | 未登录/会话过期 |
| 403 | 40300 | 非管理员 |
| 413 | 41300 | 文件超过 50 MB |
| 415 | 41500 | 非 MP4/MOV 容器（`ftyp` 魔数不匹配） |
| 500 | 50000 | 磁盘写入失败 |

- **规则**：
  - 容器与时长均由服务端解析，不信任客户端 `Content-Type` 与文件名。
  - 落盘目录 `uploads/videos/{YYYY}/{MM}/`，文件名 UUID，同源访问 `GET /uploads/videos/...`。
  - 写入 `operation_logs`：`action='upload_video'`。
  - 本端点请求体上限单独放宽至 52 MB（其余端点仍为 6 MB）。

#### 4.6.10 追加茶品图片

- **方法与路径**：`POST /admin/teas/{tea_id}/images`
- **权限**：管理员
- **请求体**（JSON，`extra=forbid`）：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `image_url` | string | 是 | 必须为本站 `/uploads/` 路径；≤500 字符 |
| `sort_order` | integer | 否 | ≥0；缺省时取当前最大值 + 1 |

- **成功响应**：HTTP 200，`code=0`，`data` 为 `{ "id": 1, "image_url": "...", "sort_order": 0 }`
- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | 契约校验失败；单茶图片已达 9 张 |
| 401 | 40100 | 未登录 |
| 403 | 40300 | 非管理员 |
| 404 | 40400 | 茶品不存在 |

- **规则**：单茶上限 9 张（应用层校验）；写入 `operation_logs`：`action='add_tea_media'`。

#### 4.6.11 删除茶品图片

- **方法与路径**：`DELETE /admin/teas/{tea_id}/images/{image_id}`
- **权限**：管理员
- **成功响应**：HTTP 200，`code=0`，`data` 为 `{ "deleted": 2 }`
- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 401 | 40100 | 未登录 |
| 403 | 40300 | 非管理员 |
| 404 | 40400 | 茶品不存在，或图片不存在/不属于该茶品 |

- **规则**：**物理删除**（ADR-0003 §6）；磁盘文件保留（同一 URL 可能被其他茶品复用），仅解除关联；写入 `operation_logs`：`action='delete_tea_media'`。

#### 4.6.12 操作日志查询

- **方法与路径**：`GET /admin/operation-logs`
- **权限**：管理员
- **查询参数**：

| 参数 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `page` | integer | 否 | 默认 1；< 1 时夹取为 1 |
| `page_size` | integer | 否 | 默认 20；取值 1–50，越界夹取 |
| `action` | string | 否 | 精确匹配动作，如 `create_tea` |
| `target_type` | string | 否 | 精确匹配目标类型，如 `tea` |
| `admin_id` | integer | 否 | 操作人 `users.id`（对应 `operation_logs.user_id`） |
| `start_date` | string | 否 | `YYYY-MM-DD`；按 `created_at` 过滤，含起始日 00:00:00 |
| `end_date` | string | 否 | `YYYY-MM-DD`；含结束日全天（< 次日 00:00:00） |

- **成功响应**：HTTP 200，`code=0`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 128,
        "admin_id": 1,
        "admin_username": "admin",
        "action": "create_tea",
        "target_type": "tea",
        "target_id": 42,
        "detail": "新增茶品：碧螺春",
        "ip_address": null,
        "created_at": "2026-11-11T03:20:15Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | `page`/`page_size`/`admin_id` 非整数；日期不是 `YYYY-MM-DD`；`start_date` 晚于 `end_date` |
| 401 | 40100 | 未登录/会话过期 |
| 403 | 40300 | 非管理员 |

- **规则**：
  - 排序固定 `created_at DESC, id DESC`（稳定次级键）。
  - `admin_username` 通过 LEFT JOIN `users` 获取；账号已删除时 `admin_id` / `admin_username` 均为 `null`，历史日志照常返回，不抛错。
  - `ip_address` 为**预留字段**：`operation_logs` 当前无 IP 列，恒返回 `null`；采集 IP 需新增列，属 C 类数据库变更。
  - 日期边界按 UTC 自然日计算（与 `created_at` 存储口径一致）。
  - 只读查询，不写入 `operation_logs`。

#### 4.6.13 保存冲泡教程（ADR-0005）

- **方法与路径**：`PUT /admin/teas/{tea_id}/brewing-guide`
- **权限**：管理员
- **路径参数**：`tea_id` integer，必填
- **请求体**（整篇覆盖；`tea_brewing_guides` 无行时创建）：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `intro` | string / null | 否 | trim 后 ≤200 字；空串归一化为 `null` |
| `steps` | object[] | 是 | **3–8 条**，顺序即展示顺序 |
| `steps[].title` | string | 是 | trim 后 1–30 字 |
| `steps[].detail` | string | 是 | trim 后 1–200 字 |
| `steps[].tip` | string / null | 否 | trim 后 ≤100 字；空串归一化为 `null` |
| `caution` | string / null | 否 | trim 后 ≤500 字；空串归一化为 `null` |

- **请求示例**：

```json
{
  "intro": "绿茶重在鲜爽，水温不宜过高，不闷盖、快出汤。",
  "steps": [
    { "title": "温杯洁具", "detail": "用热水烫洗玻璃杯并倒掉。", "tip": "清水即可" },
    { "title": "投茶", "detail": "取 3g 茶叶放入杯中。" },
    { "title": "注水", "detail": "85℃ 热水沿杯壁注入至七分满。" }
  ],
  "caution": "不要用沸水直冲，也不要闷盖。"
}
```

- **成功响应**：HTTP 200，`code=0`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "tea_id": 1,
    "intro": "绿茶重在鲜爽，水温不宜过高，不闷盖、快出汤。",
    "steps": [
      { "title": "温杯洁具", "detail": "用热水烫洗玻璃杯并倒掉。", "tip": "清水即可" },
      { "title": "投茶", "detail": "取 3g 茶叶放入杯中。", "tip": null },
      { "title": "注水", "detail": "85℃ 热水沿杯壁注入至七分满。", "tip": null }
    ],
    "caution": "不要用沸水直冲，也不要闷盖。"
  }
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | 步数不在 3–8；标题/说明/提示超长；出现未知字段 |
| 401 | 40100 | 未登录/会话过期 |
| 403 | 40300 | 非管理员 |
| 404 | 40400 | 茶品不存在 |

- **规则**：
  - 整篇覆盖：未提交的可选字段按 `null` 处理，不做局部合并。
  - 保存后立即影响公开详情 `GET /teas/{tea_id}` 的 `brewing_guide`。
  - 写入 `operation_logs`：`action='update_brewing_guide'`、`target_type='tea'`、`target_id=tea_id`、`detail` 含茶名。

#### 4.6.14 删除冲泡教程（ADR-0005）

- **方法与路径**：`DELETE /admin/teas/{tea_id}/brewing-guide`
- **权限**：管理员
- **路径参数**：`tea_id` integer，必填
- **请求体**：无
- **成功响应**：HTTP 200，`code=0`

```json
{ "code": 0, "message": "ok", "data": { "tea_id": 1, "deleted": true } }
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 401 | 40100 | 未登录/会话过期 |
| 403 | 40300 | 非管理员 |
| 404 | 40400 | 茶品不存在 |

- **规则**：
  - 幂等：教程不存在时返回 `deleted=false`，不抛错。
  - 删除后公开详情 `brewing_guide` 变为 `null`，前端退回三格速查卡。
  - 仅在确实删除时写入 `operation_logs`：`action='delete_brewing_guide'`。

---

### 4.7 我的模块

#### 4.7.1 用户统计与等级（S15）

- **方法与路径**：`GET /me/stats`
- **权限**：登录用户
- **请求体**：无
- **成功响应**：HTTP 200，`code=0`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "favorite_count": 12,
    "note_count": 3,
    "share_count": 1,
    "level": {
      "name": "茶友",
      "index": 2,
      "next_name": "茶人",
      "next_threshold": 20,
      "remaining": 8
    }
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `favorite_count` | integer | 收藏总数 |
| `note_count` | integer | 非空品鉴笔记数 |
| `share_count` | integer | 当前生效的分享数 |
| `level.name` | string | 等级名：茶客 / 茶友 / 茶人 / 茶师 |
| `level.index` | integer | 等级序号 1–4 |
| `level.next_name` | string \| null | 下一等级名；已达茶师为 `null` |
| `level.next_threshold` | integer \| null | 下一等级所需收藏数；已达茶师为 `null` |
| `level.remaining` | integer | 距下一等级还差多少款收藏；已达茶师为 `0` |

- **等级规则（按收藏数实时计算，不落库）**：

| 等级 | 收藏数 |
|---|---|
| 茶客 | 0–4 |
| 茶友 | 5–19 |
| 茶人 | 20–49 |
| 茶师 | ≥ 50 |

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 401 | 40100 | 未登录 |

---

#### 4.7.2 上传头像（ADR-0004）

- **方法与路径**：`POST /me/avatar`
- **权限**：登录用户
- **请求体**：`multipart/form-data`，字段 `file`（必填）
- **约束**：仅 JPEG / PNG / WebP；按魔数判定，不信任扩展名与 `Content-Type`；单文件 ≤ 5 MB（`MAX_UPLOAD_SIZE_MB`）；文件名服务端 UUID 生成，落盘 `uploads/YYYY/MM/`
- **成功响应**：HTTP 200，`code=0`，`data` 为更新后的 `User` 对象（含 `avatar_url`）
- **副作用**：写入 `operation_logs`：`action='avatar_update'`、`target_type='user'`、`target_id=当前用户 ID`
- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | 空文件 / 参数校验失败 |
| 401 | 40100 | 未登录 |
| 413 | 41300 | 文件超过 5 MB |
| 415 | 41500 | 非 JPEG/PNG/WebP |

#### 4.7.3 选择预置头像（ADR-0004）

- **方法与路径**：`PUT /me/avatar`
- **权限**：登录用户
- **请求体**（JSON，`extra=forbid`）：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `preset` | string | 是 | 白名单 `tea-01` ～ `tea-08`（前端静态资源 `/avatars/<preset>.svg`） |

- **成功响应**：HTTP 200，`code=0`，`data` 为更新后的 `User` 对象；`avatar_url` 形如 `/avatars/tea-03.svg`
- **副作用**：写入 `operation_logs`：`action='avatar_update'`
- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | `preset` 不在白名单 / 请求体含额外字段 |
| 401 | 40100 | 未登录 |

---

### 4.8 用户贡献模块（S10–S13）

> 双层校验：① 系统层校验表单完整性、名品-茶类映射、名称相似度查重；② 管理员人工审核。
> 不接受富文本与图片上传（X7）；`payload` 由服务端生成，请求体 `extra=forbid`，无法伪造状态/审核人。

#### 4.8.1 提交贡献

- **方法与路径**：`POST /contributions`
- **权限**：登录用户
- **请求体**（JSON，`extra=forbid`，按 `type` 二选一）：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `type` | string | 是 | `new_tea` / `article` |
| `tea` | object | `new_tea` 必填 | `ContributionTeaPayload`，见下表 |
| `target_tea_id` | integer | `article` 必填 | 茶品须存在且 `is_active=1` |
| `title` | string / null | 否 | ≤50 字符，仅 `article` |
| `content` | string | `article` 必填 | 去空白后 3–500 字 |

`ContributionTeaPayload`：

| 字段 | 类型 | 必填 |
|---|---|---|
| `name` | string | 是（≤100） |
| `category` | string | 是（七大茶类枚举） |
| `origin` | string | 是（≤200） |
| `season` / `fermentation` / `price_range` / `representative_variety` | string / null | 否 |
| `shape_desc` / `soup_desc` / `aroma_desc` / `taste_desc` | string | 是 |
| `water_temp` | number | 是（70.0–100.0） |
| `tea_amount` / `brew_time` | number | 是（>0，≤999.9） |
| `main_image_url` | string / null | 否（仅接受 `http(s)://` 或 `/uploads/`） |
| `tips_history` / `tips_suitable` / `tips_misconception` / `tips_official_note` | string / null | 否 |

- **校验规则**：
  - `new_tea`：`tea_name_category_map` 命中名称时，茶类必须一致，否则 `40000`（如“「碧螺春」属于绿茶，与所选茶类不一致”）；
  - `new_tea`：与现有茶品名称相似度 > 90%（含同名）时 `40000`，提示“与已有茶品「X」过于相似”；
  - `article`：目标茶品不存在或已下架均 `40000`。
- **成功响应**：HTTP 200，`code=0`，`data` 为 `ContributionItem`（见 §4.8.4），`status=pending`。
- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | 请求体结构/枚举/长度/数值越界；茶类矛盾；名称过于相似；目标茶品无效 |
| 401 | 40100 | 未登录/会话过期 |

#### 4.8.2 我的提交记录

- **方法与路径**：`GET /contributions/mine`
- **权限**：登录用户
- **成功响应**：HTTP 200，`code=0`，`data` 为 `ContributionItem[]`，按提交时间倒序；仅返回本人记录。
- **错误**：`40100`。

#### 4.8.3 删除待审核提交

- **方法与路径**：`DELETE /contributions/{contribution_id}`
- **权限**：登录用户（本人）
- **规则**：仅 `pending` 可删除；`approved` / `rejected` 保留审计，返回 `40000`。
- **成功响应**：HTTP 200，`code=0`，`data` 为 `null`。
- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | 提交已处理，不可删除 |
| 401 | 40100 | 未登录 |
| 404 | 40440 | 提交不存在或不属于当前用户（不泄露存在性） |

#### 4.8.4 `ContributionItem`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer | `contributions.id` |
| `type` | string | `new_tea` / `article` |
| `status` | string | `pending` / `approved` / `rejected` |
| `target_tea_id` | integer / null | `article` 的目标茶品 |
| `target_tea_name` | string / null | 目标茶品名称（派生） |
| `payload` | object | `new_tea` 为茶品字段；`article` 为 `{title, content}` |
| `reject_reason` | string / null | 拒绝理由（仅 `rejected`） |
| `reviewer_id` | integer / null | 审核管理员 ID |
| `reviewed_at` | datetime / null | 审核时间（UTC） |
| `created_at` | datetime | 提交时间（UTC） |
| `username` | string / null | 提交者用户名（仅管理端队列返回） |

#### 4.8.5 审核队列（管理员）

- **方法与路径**：`GET /admin/contributions`
- **权限**：管理员
- **查询参数**：

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `status` | string | `pending` | `pending` / `approved` / `rejected` |
| `type` | string | 空 | `new_tea` / `article` |
| `page` | integer | 1 | ≥1，越界夹取 |
| `page_size` | integer | 12 | 1–50，越界夹取 |

- **成功响应**：HTTP 200，`code=0`，`data` 为分页结构 `{items, total, page, page_size}`，`items` 为带 `username` 的 `ContributionItem`，时间倒序。
- **错误**：`40000`（status/type 非法）、`40100`、`40300`。

#### 4.8.6 审核通过（管理员）

- **方法与路径**：`POST /admin/contributions/{contribution_id}/approve`
- **权限**：管理员
- **规则**：
  - `new_tea`：按 `payload` 创建茶品并默认上架（`is_active=1`），附带的 `tips_*` 写入 `tea_tips`；
  - `article`：记录置为 `approved`，随后出现在 `GET /teas/{tea_id}` 的 `contributed_articles`；
  - 仅 `pending` 可操作；写入 `operation_logs`（`action='approve_contribution'`）。
- **成功响应**：HTTP 200，`code=0`，`data` 为更新后的 `ContributionItem`。
- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | 提交已处理 |
| 401 | 40100 | 未登录 |
| 403 | 40300 | 非管理员 |
| 404 | 40440 | 提交记录不存在 |

#### 4.8.7 审核拒绝（管理员）

- **方法与路径**：`POST /admin/contributions/{contribution_id}/reject`
- **权限**：管理员
- **请求体**（JSON，`extra=forbid`）：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `reason` | string | 是 | 去空白后 1–200 字 |

- **规则**：仅 `pending` 可操作；`reason` 回传用户端“我的提交”；写入 `operation_logs`（`action='reject_contribution'`）。
- **成功响应**：HTTP 200，`code=0`，`data` 为更新后的 `ContributionItem`。
- **错误**：`40000`（理由为空/超长、提交已处理）、`40100`、`40300`、`40440`。

---

### 4.9 内容板块（批次五 R1–R5）

> 5 个板块（`teaware` 茶具 / `origin` 产地 / `culture` 文化 / `brand` 品牌 / `knowledge` 知识）由 `content_types` + `content_items` 两表统一承载；板块特有字段存放在 `content_items.meta` JSON 中，按板块校验。
> 前台（§4.9.1–§4.9.3）游客只读，仅返回 `is_active=1` 的条目；后台（§4.9.4–§4.9.8）要求管理员，下架为软失效（`is_active=0`），**不物理删除**。

#### 4.9.1 板块分类列表

- **方法与路径**：`GET /content-types`
- **权限**：游客
- **请求参数**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为 `ContentTypeOut[]`，按 `sort_order ASC` 排序：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer | `content_types.id` |
| `code` | string | `teaware` / `origin` / `culture` / `brand` / `knowledge` |
| `name` | string | 板块中文名 |
| `icon` | string / null | 板块图标字符 |
| `description` | string / null | 板块说明 |
| `sort_order` | integer | 展示顺序，升序 |

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    {
      "id": 1,
      "code": "teaware",
      "name": "茶具茶器",
      "icon": "🫖",
      "description": "盖碗、茶壶、品茗杯、公道杯等茶器文化与选择指南",
      "sort_order": 1
    }
  ]
}
```

- **错误**：`50000`（服务端异常）。

#### 4.9.2 内容列表（前台）

- **方法与路径**：`GET /contents`
- **权限**：游客
- **查询参数**：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `type` | string | 否 | — | 板块 code：`teaware` / `origin` / `culture` / `brand` / `knowledge`；省略时返回全部板块 |
| `keyword` | string | 否 | — | ≤100 字符；对 `title` 与 `summary` 做 `%keyword%` 模糊匹配，`%` / `_` / `\` 按字面量转义；trim 后为空视为未传 |
| `page` | integer | 否 | `1` | ≥1，越界按 1 处理 |
| `page_size` | integer | 否 | `12` | 1–50，越界夹取 |

- **请求体**：无
- **示例**：`GET /contents?type=teaware&keyword=盖碗`（板块与关键词 AND 生效，匹配标题或摘要）
- **成功响应**：HTTP 200，`code=0`，`data` 为分页结构 `{items, total, page, page_size}`；`items` 为 `ContentItemOut[]`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer | `content_items.id` |
| `type_id` | integer | 所属板块 ID |
| `type_code` | string | 所属板块 code（派生字段） |
| `title` | string | 标题，≤200 字符 |
| `summary` | string / null | 摘要，≤500 字符 |
| `body` | string / null | 正文，≤20,000 字符 |
| `cover_image` | string / null | 封面图 URL |
| `meta` | object / null | 板块特有字段，见 §4.9.6 |
| `sort_order` | integer | 排序值 |
| `is_active` | boolean / null | 前台恒为 `null`（不向前台暴露上下架状态） |
| `created_at` | datetime | 创建时间（UTC，ISO8601 带 `Z`） |
| `updated_at` | datetime | 更新时间（UTC，ISO8601 带 `Z`） |

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 1,
        "type_id": 1,
        "type_code": "teaware",
        "title": "盖碗：茶席上最常见的泡茶器具",
        "summary": "上盖、中碗、下托三件一套，又称三才碗，明代以后流行。",
        "body": "盖碗，也称三才碗、三才杯，是一种古老的泡茶器具……",
        "cover_image": "/uploads/2026/11/teaware-cover.jpg",
        "meta": {"material": "白瓷", "volume": "130ml", "category": "盖碗"},
        "sort_order": 1,
        "is_active": null,
        "created_at": "2026-11-11T02:00:00Z",
        "updated_at": "2026-11-11T02:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 12
  }
}
```

- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | `type` 不在五值枚举内 |
| 404 | 40450 | 板块 code 合法但库中不存在 |
| 500 | 50000 | 服务端异常 |

- **规则**：排序 `sort_order ASC, created_at DESC`；仅返回 `is_active=1`；`keyword` 与 `type` 为 AND 关系，匹配 `title` 或 `summary`。

#### 4.9.3 内容详情（前台）

- **方法与路径**：`GET /contents/{item_id}`
- **权限**：游客
- **路径参数**：`item_id` integer，必填
- **请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为 `ContentItemOut`（字段见 §4.9.2），`is_active` 恒为 `null`。
- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 404 | 40460 | 条目不存在或已下架（不区分，避免泄露存在性） |
| 500 | 50000 | 服务端异常 |

#### 4.9.4 内容列表（管理视角）

- **方法与路径**：`GET /admin/contents`
- **权限**：管理员
- **查询参数**：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `type` | string | 否 | — | 板块 code，五值枚举；省略返回全部板块 |
| `is_active` | boolean | 否 | — | 省略=全部；`true` 只看上架；`false` 只看下架 |
| `page` | integer | 否 | `1` | ≥1，越界按 1 处理 |
| `page_size` | integer | 否 | `12` | 1–50，越界夹取 |

- **请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为分页结构，`items` 为 `AdminContentListItem[]`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer | `content_items.id` |
| `type_code` | string | 所属板块 code |
| `title` | string | 标题 |
| `summary` | string / null | 摘要 |
| `is_active` | boolean | 上架 / 下架 |
| `sort_order` | integer | 排序值 |
| `created_at` | datetime | 创建时间（UTC） |
| `updated_at` | datetime | 更新时间（UTC） |

- **错误**：`40000`（`type` 非法）、`40100`、`40300`、`40450`（板块不存在）。
- **规则**：后台列表**包含下架条目**，排序 `sort_order ASC, created_at DESC`。

#### 4.9.5 内容详情（管理视角）

- **方法与路径**：`GET /admin/contents/{item_id}`
- **权限**：管理员
- **路径参数**：`item_id` integer，必填
- **请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为 `ContentItemOut`（字段见 §4.9.2），`is_active` 返回 `true` / `false`。
- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 401 | 40100 | 未登录/会话过期 |
| 403 | 40300 | 非管理员 |
| 404 | 40460 | 条目不存在 |

- **规则**：编辑回填用途；下架条目仍可读取，故不返回 `40401`。

#### 4.9.6 新建内容条目

- **方法与路径**：`POST /admin/contents`
- **权限**：管理员
- **请求体**（JSON，`extra=forbid`）：

| 字段 | 类型 | 必填 | 约束 | DB 列 |
|---|---|---|---|---|
| `type_code` | string | 是 | `teaware` / `origin` / `culture` / `brand` / `knowledge` | `content_items.type_id`（经 code 映射） |
| `title` | string | 是 | trim 后非空，≤200 字符 | `content_items.title` |
| `summary` | string / null | 否 | ≤500 字符 | `content_items.summary` |
| `body` | string / null | 否 | ≤20,000 字符 | `content_items.body` |
| `cover_image` | string / null | 否 | ≤500 字符；`http(s)://` 外链或 `/uploads/` 路径 | `content_items.cover_image` |
| `meta` | object / null | 否 | 按板块校验，见下表 | `content_items.meta` |
| `sort_order` | integer | 否 | -9999–9999，默认 `0` | `content_items.sort_order` |

- **不接受**：`is_active`（创建后默认上架）、`id`、`type_id`。
- **`meta` 分板块字段规则**：

| 板块 code | 允许的 key | 规则 |
|---|---|---|
| `teaware` | `material` / `volume` / `category` | 均为字符串 |
| `origin` | `province` / `region` | 均为字符串 |
| `culture` | `era` / `tags` | `era` 字符串；`tags` 必须为字符串数组 |
| `brand` | `founded` / `brand_origin` / `website` | `founded` 整数；`brand_origin` 字符串；`website` 非空时必须以 `http://` 或 `https://` 开头 |
| `knowledge` | `subtype` / `difficulty` | `subtype` ∈ `standard` / `brewing`；`difficulty` ∈ `beginner` / `intermediate` / `advanced` |

> `meta` 必须是对象，最多 20 个字段；出现未定义的 key 一律 `40000`。各 key 均可选，省略即不写入。

- **请求示例**：

```json
{
  "type_code": "knowledge",
  "title": "绿茶冲泡水温为何不宜过高",
  "summary": "80–85℃ 更能保留鲜爽度与氨基酸。",
  "body": "绿茶多为不发酵茶，高温会加速茶多酚氧化……",
  "cover_image": "/uploads/2026/11/knowledge-brewing.jpg",
  "meta": {"subtype": "brewing", "difficulty": "beginner"},
  "sort_order": 10
}
```

- **成功响应**：HTTP 200，`code=0`，`data` 为 `ContentItemOut`，`is_active=true`。
- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | 必填缺失、长度/枚举/数值越界、`meta` 结构非法、请求体含未定义字段 |
| 401 | 40100 | 未登录/会话过期 |
| 403 | 40300 | 非管理员 |
| 404 | 40450 | 板块不存在 |

- **规则**：写入 `operation_logs`：`action='create_content'`、`target_type='content_item'`、`target_id=新 id`、`detail` 为 `[板块 code] 标题`。

#### 4.9.7 更新内容条目

- **方法与路径**：`PUT /admin/contents/{item_id}`
- **权限**：管理员
- **路径参数**：`item_id` integer，必填
- **请求体**（JSON，`extra=forbid`）：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `title` | string / null | 否 | ≤200 字符 |
| `summary` | string / null | 否 | ≤500 字符 |
| `body` | string / null | 否 | ≤20,000 字符 |
| `cover_image` | string / null | 否 | ≤500 字符；`http(s)://` 或 `/uploads/` 路径 |
| `meta` | object / null | 否 | 按条目当前所属板块校验 |
| `sort_order` | integer / null | 否 | -9999–9999 |
| `is_active` | boolean / null | 否 | `true` 上架 / `false` 下架（软失效） |

- **不接受**：`type_code`、`type_id`（条目所属板块创建后不可变更）。
- **规则**：全量替换语义，仅更新请求中出现的字段；`meta` 传入时按条目当前板块重新校验；写入 `operation_logs`：`action='update_content'`。
- **成功响应**：HTTP 200，`code=0`，`data` 为更新后的 `ContentItemOut`（含 `is_active`）。
- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 400 | 40000 | 长度/枚举/数值越界、`meta` 结构非法、请求体含未定义字段 |
| 401 | 40100 | 未登录/会话过期 |
| 403 | 40300 | 非管理员 |
| 404 | 40460 | 条目不存在 |
| 404 | 40450 | 条目所属板块数据缺失 |

#### 4.9.8 删除内容条目（软删除）

- **方法与路径**：`DELETE /admin/contents/{item_id}`
- **权限**：管理员
- **路径参数**：`item_id` integer，必填
- **请求体**：无
- **成功响应**：HTTP 200，`code=0`，`data` 为 `{ "deleted": 5 }`（值为条目 id）。
- **错误**：

| HTTP | code | 触发 |
|---|---|---|
| 401 | 40100 | 未登录/会话过期 |
| 403 | 40300 | 非管理员 |
| 404 | 40460 | 条目不存在 |

- **规则**：仅置 `is_active=0`，**不物理删除**；下架后前台接口不再返回；写入 `operation_logs`：`action='delete_content'`。

---

## 5. 数据库字段与 API 字段对照

### 5.1 `users`

| 数据库列 | API 字段 | 出现位置 |
|---|---|---|
| `id` | `id` / 路径中的用户身份 | `User`、`/auth/me` |
| `username` | `username` | `User`、注册/登录 |
| `role` | `role` | `User`、权限判定 |
| `session_version` | 不暴露 | 会话版本校验（改密吊销旧 Cookie） |
| `created_at` | `created_at` | `User` |
| `password_hash` | 不暴露 | — |

### 5.2 `teas`

| 数据库列 | API 字段 |
|---|---|
| `id` / `name` / `category` / `origin` / `season` | 同名 |
| `fermentation` / `price_range` / `representative_variety` | 同名 |
| `shape_desc` / `soup_desc` / `aroma_desc` / `taste_desc` | 同名 |
| `water_temp` / `tea_amount` / `brew_time` | 同名（number） |
| `main_image_url` | `main_image_url` |
| `is_active` | `is_active`（仅详情/后台列表）；前台列表用 `is_available` 派生 |
| `favorite_count` | `favorite_count`（缓存值，见 §1.10） |
| `created_at` / `updated_at` | 同名 |

### 5.3 `tea_tips`

| 数据库列 | API 字段 |
|---|---|
| `history` | `tips_history` |
| `suitable` | `tips_suitable` |
| `misconception` | `tips_misconception` |
| `official_note` | `tips_official_note` |
| `tea_id` | 不单独返回，隐含在所属茶品 |
| 无对应行 | 四个 `tips_*` 均为 `null` |

### 5.4 `collection_lists`

| 数据库列 | API 字段 |
|---|---|
| `id` | `ListData.id` |
| `user_id` | 不返回（由登录身份隐含） |
| `title` | `ListData.title`、分享 `title` |
| `created_at` / `updated_at` | 同名 |
| 可见性（无列） | 由 `share_tokens.is_active` 派生为 `ListData.share` |

### 5.5 `favorite_items`

| 数据库列 | API 字段 |
|---|---|
| `id` | 内部主键，不暴露 |
| `user_id` | 不返回 |
| `tea_id` | `ListItem.tea_id`、`FavoriteState.tea_id` |
| `tasting_note` | `ListItem.tasting_note`；分享视图不返回 |
| `created_at` | `ListItem.favorited_at`（语义化重命名） |

### 5.6 `share_tokens`

| 数据库列 | API 字段 |
|---|---|
| `id` / `list_id` | 不直接暴露 |
| `token` | `token`、路径参数 |
| `is_active` | 派生为 `revoked = !is_active` / 撤销响应 `is_active` |
| `revoked_at` | `revoked_at` |
| `created_at` | `created_at` |
| 复用判断 | `is_new`（派生） |

### 5.7 `operation_logs`

只读查询接口 `GET /admin/operation-logs`（§4.6.12）；写入仍由管理员写操作触发：

| `action` | 触发接口 |
|---|---|
| `create_tea` | `POST /admin/teas` |
| `update_tea` | `PUT /admin/teas/{tea_id}`、`PUT /admin/teas/{tea_id}/tips` |
| `toggle_tea` | `PATCH /admin/teas/{tea_id}/toggle` |
| `upload_image` | `POST /admin/upload` |

字段映射（查询响应）：

| 数据库列 | API 字段 |
|---|---|
| `id` | `id` |
| `user_id` | `admin_id`（操作人） |
| `user_id` → `users.username` | `admin_username`（LEFT JOIN，账号删除后为 `null`） |
| `action` | `action` |
| `target_type` | `target_type` |
| `target_id` | `target_id` |
| `detail` | `detail` |
| （无此列） | `ip_address` 恒为 `null`（预留） |
| `created_at` | `created_at` |

`target_type` 固定 `tea`；`target_id` 为弱引用（上传时为 `null`）；`detail` 仅存摘要，不存 JSON diff；不记录 GET 操作。

### 5.8 `login_attempts`（S14 内部表）

| 数据库列 | API 字段 |
|---|---|
| `id` | 内部主键，不暴露 |
| `username` | 不暴露（登录失败时的输入值，含不存在的用户名） |
| `ip` | 不暴露（`request.client.host`） |
| `failed_at` | 不暴露；窗口计数与 24 小时清理依据 |

### 5.9 `contributions`（S10–S13）

| 数据库列 | API 字段 |
|---|---|
| `id` | `ContributionItem.id` |
| `user_id` | 不直接暴露；管理端派生 `username` |
| `type` | `ContributionItem.type` |
| `target_tea_id` | `ContributionItem.target_tea_id`；派生 `target_tea_name` |
| `payload` | `ContributionItem.payload`（JSON） |
| `status` | `ContributionItem.status` |
| `reject_reason` | `ContributionItem.reject_reason` |
| `reviewer_id` | `ContributionItem.reviewer_id` |
| `reviewed_at` | `ContributionItem.reviewed_at` |
| `created_at` | `ContributionItem.created_at` |

### 5.10 `tea_name_category_map`（S10 内部表）

| 数据库列 | API 字段 |
|---|---|
| `name` | 不对外暴露；用于提交时茶类一致性校验 |
| `category` | 不对外暴露；校验命中时生成 `40000` 提示 |

---

## 6. 一致性与实现注意事项

### 6.1 下架（软失效）在各接口的表现

| 接口 | 下架茶品行为 |
|---|---|
| `GET /teas`、`/teas/hot`、`/teas/random`、`/teas/recommended`、`/teas/categories`、`/teas/origins` | 完全过滤，不出现、不计数 |
| `GET /teas/{tea_id}/related`、`GET /tips/latest` | 完全过滤，不出现 |
| `GET /teas/{tea_id}` | `40401` 该茶品暂不可用 |
| `POST /favorites/{tea_id}` | `40401`，不可新增收藏 |
| `DELETE /favorites/{tea_id}`、`GET /favorites/{tea_id}/status` | 正常处理（允许从清单移除/查询） |
| `GET /lists`、`GET /lists/{list_id}` | 条目保留，`is_available=false`，前端灰显 |
| `GET /shares/{token}` | 条目保留，`is_available=false` |
| `POST /shares/{token}/copy` | 跳过，计入 `skipped` |
| `GET /admin/teas`、`GET /admin/teas/{tea_id}` | 正常展示，可编辑/重新上架 |

### 6.2 分享令牌生命周期

1. 首次生成：无生效令牌 → 新建 8 位短码，写入 `share_tokens`。
2. 重复生成：存在 `is_active=1` → 复用同一 token，`is_new=false`。
3. 撤销：`is_active=0` + `revoked_at=now`，行保留。
4. 再次分享：已撤销令牌不复活，必须新建 token。
5. 访问：token 不存在 → `40410`；存在但已撤销 → HTTP 200 + `revoked=true`；有效 → 只读清单。
6. 安全：token 大小写敏感（`utf8mb4_bin`），不做大小写归一；短码全局唯一。

### 6.3 审计留痕

- 仅管理员写操作记录 1 行，读操作不记录。
- `user_id` 可为空（账号删除后 `SET NULL`），审计不随账号消失。
- `target_id` 不建外键，避免删茶/下架影响历史日志。
- 管理员可通过只读接口 `GET /admin/operation-logs`（§4.6.12）按动作、目标类型、操作人与日期检索；接口不写入新日志。

### 6.4 契约与既有脚手架的差异（落地时以此为准）

| 项 | 脚手架现状 | 本契约 |
|---|---|---|
| 用户主键字段 | 注册返回 `user_id` | 统一为 `id`（与 `users.id` 一致） |
| 产地筛选 | 对完整 `teas.origin` 做等值匹配 | 省级前缀匹配；`/teas/origins` 返回省级 |
| 管理员更新小贴士 | 无独立接口 | 新增 `PUT /admin/teas/{tea_id}/tips` |
| 管理员茶品详情 | 无独立接口 | 新增 `GET /admin/teas/{tea_id}` |
| 清单条目移除 | 规划过 `DELETE /lists/{tea_id}` | 统一使用 `DELETE /favorites/{tea_id}` |
| 422 校验错误 | FastAPI 默认结构 | 统一重映射为 `400 + 40000` |

### 6.5 PRD 功能对照

| PRD | 接口 |
|---|---|
| FR-1.1–FR-1.6 筛选/排序/分页 | `GET /teas`（默认 `page_size=12`） |
| FR-2.1 七大茶类入口 | `GET /teas/categories` |
| FR-2.2 热门推荐 | `GET /teas/hot`（前 8） |
| FR-2.3 随机发现 | `GET /teas/random` |
| FR-2.4 搜索 | `GET /teas?keyword=` |
| FR-3.1/3.2 详情与小贴士 | `GET /teas/{tea_id}` |
| FR-4.1 注册 + 实时唯一校验 | `POST /auth/register`、`GET /auth/username-availability` |
| FR-4.2 登录 | `POST /auth/login` |
| FR-4.3 30 天会话 | HttpOnly Cookie `tea_session` |
| FR-5.1 收藏/取消 | `POST/DELETE /favorites/{tea_id}` |
| FR-5.2 清单页与标题 | `GET /lists`、`POST /lists`、`GET /lists/{list_id}`、`PUT /lists/{list_id}` |
| FR-5.3 品鉴笔记 | `PUT /lists/{list_id}/notes/{tea_id}` |
| FR-5.4 生成分享 | `POST /shares/generate`、`GET /shares/{token}` |
| FR-5.5 撤销分享 | `POST /shares/revoke/{token}` |
| FR-5.6 一键收藏全部 | `POST /shares/{token}/copy` |
| FR-6.1 新增茶品 | `POST /admin/teas` |
| FR-6.2 编辑茶品 | `PUT /admin/teas/{tea_id}` |
| FR-6.3 上下架 | `PATCH /admin/teas/{tea_id}/toggle` |
| FR-6.4 官方小贴士 | `PUT /admin/teas/{tea_id}/tips` |
| 管理员数据维护支撑 | `GET /admin/teas`、`GET /admin/stats`、`POST /admin/upload` |
| S1 筛选 AND/OR | `GET /teas?filter_mode=` |
| S2 发酵/价格筛选 | `GET /teas?fermentation=&price_min=&price_max=` |
| S6 详情相关推荐 | `GET /teas/{tea_id}/related` |
| S7 首页小贴士 | `GET /tips/latest` |
| S14 登录失败锁定 | `POST /auth/login`（`42900`） |
| S15 用户等级 | `GET /me/stats` |
| S16 个性化推荐 | `GET /teas/recommended` |
| S8 分享海报 | 纯前端生成，无 API 变更 |
| S9 多收藏清单 | `GET/POST /lists`、`GET/PUT/DELETE /lists/{list_id}`；收藏/分享支持可选 `list_id` |
| S10 用户贡献新茶 | `POST /contributions`（type=`new_tea`）；名品映射表 `tea_name_category_map` |
| S11 用户投稿科普 | `POST /contributions`（type=`article`）；通过后进入 `TeaDetail.contributed_articles` |
| S12 管理员审核后台 | `GET /admin/contributions`、`POST .../approve`、`POST .../reject` |
| S13 我的提交记录 | `GET /contributions/mine`、`DELETE /contributions/{id}` |

---

## 7. 变更记录

| 版本 | 日期 | 内容 |
|---|---|---|
| **v1.0** | 2026-11-06 | 首版 API 契约：统一 `/api/v1` 前缀、`{code,message,data}` 响应、PageSize 默认 12、HttpOnly Cookie 会话、ISO8601 UTC、图片上传与静态访问、收藏计数缓存语义；覆盖 29 个 MVP 业务接口 |
| **v1.1** | 2026-11-07 | 全局一致性修订：① §4.4.3 品鉴笔记 `content` 增加 20,000 字符上限（对齐 SECURITY S-19/S-24、TEST_PLAN TC-NOTE-04）；② §1.8 分享短码示例更正为 8 位 `k7X9m2Qa` |
| **v1.2** | 2026-11-09 | 内容扩展（ADR-0003）：`TeaDetail` 增 `video_url`/`video_duration`/`image_set`；新增 §4.2.7 图片集查询、§4.6.9 视频上传、§4.6.10 追加图片、§4.6.11 删除图片；错误码族不新增，复用 400/404/413/415 |
| **v1.3** | 2026-11-09 | 批次一/二（PLAN_剩余功能）：新增 §4.2.8 相关推荐、§4.2.9 最新小贴士、§4.2.10 个性化推荐、§4.7.1 用户统计与等级；登录新增 `42900` 锁定；接口总览补齐至 37 个；新增 §5.8 `login_attempts` |
| **v1.4** | 2026-11-09 | 批次三 S9 多收藏清单：清单拆分为 6 个端点；`FavoriteState` 增 `list_ids`，收藏/取消/分享支持可选 `list_id`；新增错误码 `40420`；`favorite_count` 改为跨清单去重；接口总览 37 → 40 个 |
| **v1.5** | 2026-11-09 | 批次四 S10–S13 用户贡献：新增 §4.8 六个端点；`TeaDetail` 增 `contributed_articles`；新增错误码 `40440`；新增枚举 `contribution.type/status`；新增 §5.9 `contributions`、§5.10 `tea_name_category_map`；接口总览 40 → 46 个 |
| **v1.6** | 2026-11-10 | ADR-0004 用户头像：`User` 增 `avatar_url`；新增 §4.7.2 `POST /me/avatar`、§4.7.3 `PUT /me/avatar`；错误码复用 400/401/413/415；接口总数 53 → 55 |
| **v1.7** | 2026-11-11 | 补录批次五 R1–R5 内容板块 8 个端点：新增 §4.9（`GET /content-types`、`GET /contents`、`GET /contents/{item_id}`、`GET/POST /admin/contents`、`GET/PUT/DELETE /admin/contents/{item_id}`）；新增错误码 `40450`/`40460` 的文档说明；接口总览补齐至 56 个业务端点 |
| **v1.8** | 2026-11-11 | 新增 §4.1.6 用户自助修改密码 `PUT /auth/password`：Cookie 载荷增加 `sv`（`users.session_version`），改密后旧会话立即失效；接口总览 56 → 57 个业务端点 |
| **v1.9** | 2026-11-11 | 新增 §4.6.12 管理员操作日志查询 `GET /admin/operation-logs`（分页 + 动作/目标类型/管理员/日期筛选，`created_at DESC, id DESC`，LEFT JOIN 取 `admin_username`）；§5.7/§6.3 同步日志可读；`ip_address` 为预留字段恒 `null`；接口总览 57 → 58 个业务端点 |
| **v1.10** | 2026-11-11 | §4.1.4 登出语义更新：携带有效 Cookie 时递增 `users.session_version`，旧 Cookie 立即失效；未登录/无效 Cookie 仅清 Cookie；接口总数不变 |
| **v1.11** | 2026-11-12 | 新增 ADR-0005 分步冲泡教程：`TeaDetail`/管理员详情新增 `brewing_guide`（3–8 步，含 `intro`/`caution`）；新增 §4.6.13 `PUT /admin/teas/{tea_id}/brewing-guide` 与 §4.6.14 `DELETE .../brewing-guide`；新增表 `tea_brewing_guides`；接口总览 58 → 60 个业务端点 |
