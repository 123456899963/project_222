# ADR-0003：内容扩展功能的数据模型与架构选型

| 项 | 值 |
|---|---|
| 状态 | **已采纳**（2026-11-09 用户确认「全部按推荐方案执行」） |
| 日期 | 2026-11-09 |
| 决策者 | AI 提案 + 用户确认 |
| 任务分级 | **C**（涉及数据模型、API 契约、业务范围扩展） |
| 关联任务卡 | 内容扩展需求（茶具茶器/产地/文化/品牌/知识/视频/首页背景/实拍图） |
| 取代 / 被取代 | 无 |

---

## 1. 背景与问题

### 1.1 当前处境

茶·图鉴 MVP 已完成 6 个模块（M1–M7），7 张表、29 个端点、106 条测试全部通过。产品范围严格限定在「六大茶类结构化图鉴 + 收藏分享闭环」。

### 1.2 触发本次决策的具体问题

用户提出以下扩展需求，全部超出 MVP 已确认边界：

1. **全新内容板块**：茶具茶器、茶叶产地、茶叶文化、茶叶品牌、茶叶知识（含茶叶标准/冲泡知识/视频欣赏三个子栏目）—— 共 5 个板块，其中 4 个在 PRD 中完全没有定义。
2. **茶品详情页视频介绍**（R6）—— PRD S5 已有规格，但 DATA_MODEL 明确标注 S4/S5 第二阶段不建表，需要决定视频字段的落地方案。
3. **首页图片滚动背景**（R7）—— 视觉层改造，需确认不破坏设计规范。
4. **六大茶类及每款茶配真实实拍图**（R8）—— PRD 主图是必填项但种子用了外链 CDN；S4 图片集（多张）需决定存储方案。

### 1.3 不决策的后果

- 若各板块独立建表：5 个板块 × 各自独立 CRUD API = 大量重复代码；跨板块搜索/排序困难；admin 后台需要 5 套表单。
- 若过早引入内容管理系统（CMS）级别的复杂方案：远超 MVP 后的扩展需求，增加维护负担。
- 若用 JSON 列塞内容：失去结构化查询能力（如"所有关于武夷山的内容""所有冲泡知识"），且 MySQL 5.7 JSON 支持有限。

---

## 2. 决策驱动因素

- **约束 1：MySQL 5.7 无有效 CHECK，枚举用 ENUM，范围校验靠 Pydantic/Service**—— 新表结构不能依赖 CHECK。
- **约束 2：五层架构不跨层，Router 不写业务、不查库**—— 新模块必须严格落在 `routers/ → services/ → repositories/ → models/ → schemas/`。
- **约束 3：统一响应体 `{code, message, data}`、成功 HTTP 200、`snake_case` JSON 字段**—— 新端点必须完全对齐。
- **约束 4：软失效（`is_active`）而非物理删除**—— 新表也需遵循。
- **约束 5：`operation_logs.action` 用 VARCHAR 而非 ENUM**—— 日志表可以接纳新动作值而不做 DDL。
- **约束 6：admin 后台允许 Element Plus，前台禁止**—— 新增内容管理页可使用 Element Plus，内容展示页必须自研。
- **约束 7：新表一律走 Alembic 迁移，禁止手工 ALTER TABLE**。
- **约束 8：PRD 第二阶段 S4（图片集）、S5（视频）的规格已经存在**—— 实现向规格对齐，不重新发明规格。

---

## 3. 备选方案

### 方案 A：统一内容表（单表 + type 字段）

**做法**：新建两张表 `content_types`（内容类型字典）+ `content_items`（统一内容条目），所有板块共用。

```
content_types (id, slug, name, description, sort_order, is_active)
  ├─ teaset     → 茶具茶器
  ├─ origin     → 茶叶产地知识
  ├─ culture    → 茶叶文化
  ├─ brand      → 茶叶品牌
  ├─ knowledge  → 茶叶知识（子栏目靠 category 字段再分）

content_items (
  id, type_id FK,
  title, slug,        -- URL 友好标识
  summary,            -- 摘要（列表页用）
  body,               -- 正文（TEXT）
  cover_image_url,    -- 封面图
  gallery_json,       -- 图片集（JSON，存 URL 数组）
  video_url,          -- 可选视频
  tea_id FK NULL,     -- 可关联特定茶品（如某产地→该地产出的茶）
  sort_order,
  is_active,
  created_at, updated_at
)
```

- **优点**：
  1. 两张表覆盖所有板块，API 端点统一（`GET /content?type=teaset`），admin 后台一套表单支持所有类型。
  2. 跨板块查询简单（"所有关于武夷山的内容"——用 `body LIKE '%武夷山%'` 或加标签字段）。
  3. 新增板块（如"茶叶冲泡视频"）只是加一条 `content_types` 记录，无需 DDL。
  4. 种子数据管理简单，所有内容在一个文件里。
  5. 符合"知识越用越丰富"的产品演进方向（PRD §1.2）。

- **缺点**：
  1. 不同板块可能需要不同的专属字段（如"茶具"需要材质/产地，"品牌"需要成立时间/官网）—— 统一表只能用 `body` TEXT 承载，或新增灵活字段（`extra_json`），失去结构化查询。
  2. 列表查询需始终过滤 `type_id`，且每种类型的排序/分页逻辑不同（"产地"按地理位置聚类 vs "品牌"按成立时间排序）。
  3. admin 表单无法做类型专属校验（如品牌必须有 logo，茶具必须有材质说明）。
  4. 违背 MVP 的"最小化"原则——5 个板块同时上线可能超出用户预期的实施节奏。

- **风险**：
  - 如果后期发现某个板块确实需要独立结构，从统一表拆成独立表需要数据迁移。
  - `body` TEXT 中的富文本/图片引用无结构化约束，依赖前端渲染。

---

### 方案 B：各自独立建表

**做法**：每个板块一张表，每张表有自己的字段集。

```
tea_sets        (茶具: id, name, material, origin, ...)
origin_knowledge (产地: id, province, region, description, ...)
tea_culture     (文化: id, title, body, dynasty, ...)
tea_brands      (品牌: id, name, logo, founded_year, website, ...)
tea_knowledge   (知识: id, category ENUM, title, body, video_url, ...)
```

- **优点**：
  1. 每张表字段精确匹配板块需求，查询高效。
  2. admin 表单可做类型专属校验和 UI。
  3. 某个板块出问题不影响其他板块。
  4. 与当前 `teas` / `tea_tips` 的建模风格一致（每张表业务独立）。

- **缺点**：
  1. 5 个板块 × 各 2-3 个 CRUD 端点 = 10-15 个新端点 + 对应的 repository/service/schema/router 文件 = 大量样板代码。
  2. 跨板块搜索需要 UNION 多张表，维护成本高。
  3. 板块间共性逻辑（软失效、排序、封面图、富文本渲染）无法复用。
  4. admin 后台需要 5 套列表页 + 5 套表单，开发量大。
  5. 违反 PRD §2.4 产品契约（六大茶类结构化知识库）的边界扩张初衷——5 个独立板块与"图鉴"的一体化定位有距离。

- **风险**：
  - 总代码量翻倍，测试量翻倍，容易引入回归缺陷。
  - 新板块（如 S10 用户贡献新茶）又要建新表，表数量膨胀。

---

### 方案 C（推荐）：统一表 + 类型专属扩展表（hybrid）

**做法**：核心内容字段统一在 `content_items`，类型专属字段存在各自的扩展表（1:1）。

```
content_types (id, slug, name, sort_order, is_active)  -- 字典表

content_items (
  id, type_id FK,
  title, slug, summary, body,
  cover_image_url,
  is_active,
  sort_order,
  created_at, updated_at
)

-- 可选扩展表（1:1，仅需要结构化字段时才建）
tea_set_extras    (content_id UK, material, usage, ...)   -- 茶具需要结构化字段
brand_extras      (content_id UK, logo, founded_year, website)  -- 品牌需要
origin_extras     (content_id UK, province FK, ...)       -- 产地需要
-- 文化和知识板块可以不加扩展表（正文足够）
```

**S4 图片集和 S5 视频**的落地方案（与内容板块方案正交，独立决策）：

#### S5 茶品详情页视频（PRD 已有规格）

在 `teas` 表直接增列：

```sql
ALTER TABLE teas ADD COLUMN video_url VARCHAR(500) NULL COMMENT '视频介绍 mp4 URL';
ALTER TABLE teas ADD COLUMN video_duration INT UNSIGNED NULL COMMENT '视频时长（秒）';
```

理由：PRD §4.1 选填字段明确有"视频介绍"，DATA_MODEL v1.0 的 §10 扩展预留也明确标注 S4/S5 不建独立表。视频与茶品是强从属关系，与 `main_image_url` 同级，直接增列最简洁。

#### S4 茶品图片集（PRD 已有规格）

新建关联表：

```
tea_media (
  id, tea_id FK NOT NULL,
  image_url VARCHAR(500) NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME
)
```

理由：图片集是 1:N 关系（一款茶可有多张图），且排序/删除/切换需要精确控制。不建议用 JSON 列（MySQL 5.7 JSON 查询有限）。

#### R8 六大茶类代表图

在 `content_types` 中新增一个系统记录 `category_banner`，或在 `content_items` 中存六大茶类的代表图条目。也可以在首页前端按 category 枚举硬编码（MVP 六大茶类是固定枚举）。

---

## 4. 最终选择

**选择：方案 C（hybrid）+ S4 独立关联表 + S5 增列**

### 4.1 为什么选 hybrid

1. **单一事实源**：所有内容条目都在 `content_items`，统一的 CRUD API、统一的 admin 列表、统一的搜索入口。
2. **按需扩展**：只有需要结构化字段的板块才建扩展表，其余板块只用核心字段即可——避免"为了统一而统一"或"为了独立而独立"。
3. **符合产品演进**：PRD §1.2 明确说"让知识库越用越丰富"，统一表 + 类型字典天然支持新增板块（加一条字典记录即可）。
4. **与现有架构风格一致**：`teas` 主表 + `tea_tips` 1:1 扩展表的模式已经在 MVP 验证过，hybrid 是这个模式的自然延伸。

### 4.2 为什么 S5 用增列而不是独立表

PRD §4.1 选填字段已定义视频介绍为单字段，DATA_MODEL v1.0 §10 扩展预留明确标注 S4/S5 不建独立表。视频与茶品是 1:1（最多一个介绍视频），与 `main_image_url` 同级，增列最简洁。

### 4.3 为什么 S4 用独立关联表而不是 JSON 列

图片集是 1:N，需要排序、需要删除、需要精确管理。JSON 列在 MySQL 5.7 上查询不便（不能直接按 `sort_order` 排序单条图片），也不利于 admin 后台的"添加/删除/排序每张图"操作。

### 4.4 方案 A 和 B 的问题

- 方案 A（完全统一）：不同板块的结构化需求被压制，依赖 JSON 扩展——当某个板块需要"按成立年份排序的品牌列表"或"按材质筛选的茶具"时，JSON 无法高效支持。
- 方案 B（完全独立）：大量样板代码 + admin 后台复杂度翻倍 + 跨板块搜索困难——与 MVP 后"轻量扩展"的节奏不匹配。

---

## 5. 影响与后果

### 5.1 正面影响

- 新增 5 个内容板块只需要：2 张核心表 + 最多 3 张扩展表 + 约 10 个新 API 端点（统一的 GET/POST/PUT/DELETE + 类型筛选）。
- S4/S5 的实现成本极低（一个增列 + 一个关联表），完全对齐 PRD 已有规格。
- admin 后台内容管理可以复用统一表单组件，只在需要扩展字段的类型上显示额外区域。
- 未来 PRD §2.3 暂不实现项中的 X2（冲泡参数分器具对比）可以自然落在 `tea_set_extras` 扩展表中。

### 5.2 负面影响 / 需要接受的代价

- hybrid 方案的"统一性"不如完全统一方案——写服务层时需要判断是否有扩展表并在 1:1 处读写。
- 新增板块如果意外需要新的结构化字段，就需要新建扩展表 + Alembic 迁移（但这个代价远小于每张表独立设计）。
- `content_items.body` 是 TEXT，需要 admin 端自行处理富文本（MVP 阶段用简单 HTML 即可，不引入富文本编辑器）。

### 5.3 必须同步的文档与代码

- [ ] PRD_扩展提案.md：已创建，待确认后同步到 PRD.md v1.2
- [ ] DATA_MODEL.md v1.1：新增 `content_types`、`content_items`、`tea_media` 表定义；`teas` 表新增 `video_url`、`video_duration` 列
- [ ] API_CONTRACT.md v1.1：新增内容模块端点（`/content/*`）；TeaDetail/AdminTeaDetail/AdminTeaCreate/AdminTeaUpdate 新增视频字段
- [ ] openapi.yaml：同步更新
- [ ] ARCHITECTURE.md：新增 `routers/content.py` / `services/content.py` / `repositories/content_repo.py` 等模块说明
- [ ] SECURITY.md：新增视频上传的安全项（类型校验、大小限制、魔数检查）
- [ ] TEST_PLAN.md：新增内容板块 + S4 + S5 的测试用例（预估 25-30 条）
- [ ] `database/init.sql`：新增扩展表建表语句 + 内容种子数据（如六大茶类代表图、产地基础知识等）
- [ ] Alembic 迁移：`0002_content_expansion.py`
- [ ] 前端 `types/index.ts`：新增 `ContentItem` / `ContentType` / `TeaMedia` 类型
- [ ] build-log.md：每完成一个扩展模块追加条目

### 5.4 现有 MVP 端点的影响

**重要声明：所有现有 29 个 MVP 端点的请求体和响应体，在本次扩展中** 只做字段追加（追加 `video_url` 到 TeaDetail），不删除、不重命名、不改变已有字段的语义和格式。

| 端点 | 变更 | 兼容性 |
|---|---|---|
| `GET /teas/{tea_id}` TeaDetail | 追加 `video_url`、`video_duration`、`image_set`（可选字段） | ✅ 向后兼容：`null` 表示无视频/无图片集 |
| `GET /admin/teas/{tea_id}` | 同 TeaDetail | ✅ |
| `POST /admin/teas` | 请求体追加可选字段 `video_url`、`video_duration`、`image_urls` | ✅ 向后兼容：省略即不设置 |
| `PUT /admin/teas/{tea_id}` | 请求体追加可选字段 | ✅ 向后兼容 |

**API 契约版本号升级**：从 v1.0 → v1.1（小版本升级，语义为"向后兼容的字段追加"）。

---

## 6. 验证方式

| 验证对象 | 方式 |
|---|---|
| Alembic 迁移 | `alembic upgrade head` 后 `alembic downgrade` 能正常回滚再升级 |
| 新增表 | `SHOW TABLES` 包含新增表；DESCRIBE 字段与 DATA_MODEL 一致 |
| TeaDetail 响应 | 有视频的茶返回完整字段；无视频的返回 `video_url=null`；前端不报错 |
| 内容板块 API | 各端点独立 pytest 用例（列表筛选/详情/软失效/搜索/权限） |
| 管理员 CRUD | 视频上传成功/超限拒绝/非管理员 403；内容创建/编辑/上下架正确 |
| 前端 | 详情页有视频时播放器可见、无视频时区块隐藏（对齐 S5 规格）；图片缩略图可切换 |
| 安全 | 视频上传校验文件类型/大小/魔数，拒绝伪造扩展名（新增 SECURITY 项） |
| 全量回归 | 现有 106 条 pytest 全部通过；前端 lint/typecheck/test/build 无新增错误 |

---

## 7. 复审条件

- 内容板块数据量超过 10,000 条 → 评估全文搜索方案（MySQL FULLTEXT / Elasticsearch）
- 某个板块（如"品牌"）需要独立的审核工作流 → 新建扩展表 + 审核状态机（参考 PRD S12）
- 用户贡献功能（S10/S11）开放 → `content_items` 新增 `created_by` 字段 + 审核状态列
- 六大茶类以外新增茶类（如"再加工茶"）→ 修改 `content_types`（新增字典条目），同时修改 `teas.category` ENUM（DDL）

---

## 8. 待用户确认的问题

以下问题阻塞本 ADR 的最终采纳，请用户答复：

| # | 问题 | 选项 | 推荐 |
|---|---|---|---|
| A1 | **全新内容板块（R1-R5）是否在本期实现？** | 方案一：全部 5 个板块都做（hybrid 方案）<br>方案二：本期只做 PRD 已有规格的 S4（图片集）+ S5（视频）+ R7（首页背景），全新板块延后一期 | ✅ **已确认（2026-11-09）：方案二** —— 本期 S4/S5/R7/R8，全新板块延后 |
| A2 | **视频最大时长/体积限制？** | PRD S5 只说 ≤3 分钟，未提 MB 上限<br>选项 A：≤3 分钟 + ≤50MB<br>选项 B：≤3 分钟 + ≤100MB<br>选项 C：不限制体积，只限制时长 | ✅ **已确认（2026-11-09）：选项 A** —— ≤3 分钟 + ≤50MB，MP4/MOV |
| A3 | **首页滚动背景：是纯装饰还是有引导功能？** | 选项 A：纯装饰性 hero 视频/图片轮播（无点击）<br>选项 B：轮播图 + 每张可点击进入对应茶/知识板块<br>选项 C：单色渐变 + 水墨装饰（最轻量） | ✅ **已确认（2026-11-09）：选项 A** —— 纯装饰轮播，不引入新跳转 |
| A4 | **实拍图片素材来源授权方式？** | 选项 A：全部用 Unsplash/Pexels 等授权图库（需在代码中留 attribution）<br>选项 B：全部自行拍摄（最真实但耗时）<br>选项 C：混合——种子数据用授权图，后续替换为实拍 | ✅ **已确认（2026-11-09）：选项 C** —— 混合策略，种子用授权图 + 留 attribution，后续替换实拍 |
| A5 | **hybrid 方案的扩展表：哪些板块需要？** | 选项 A：5 个板块全加扩展表<br>选项 B：只有茶具+品牌+产地加扩展表（文化和知识只用核心字段）<br>选项 C：一个都不加（全部用 `body` + `extra_json`） | ⏸ **本期不适用**（A1 已选方案二，全新板块延后；后续启动时按推荐选项 B 执行） |

---

## 9. 参考资料

- [PRD.md](../../product/PRD.md) v1.1 §2.2 第二阶段 / §6 S4 S5
- [DATA_MODEL.md](../../architecture/DATA_MODEL.md) v1.0 §10 扩展预留
- [API_CONTRACT.md](../../api/API_CONTRACT.md) v1.0 §4.2 TeaDetail
- [DEVELOPMENT_GUIDE.md](../DEVELOPMENT_GUIDE.md) §2 分级判定
- [ADR TEMPLATE.md](./TEMPLATE.md)
