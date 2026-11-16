# 茶·图鉴 —— 技术栈分析与选型文档（TECH_STACK）

| 项 | 值 |
|---|---|
| 文档版本 | **v1.0（已确认定稿）** |
| 创建日期 | 2026-11-04 |
| 修订记录 | v1.0（2026-11-05）：项目负责人确认全部决策，升级为定稿；v0.3：补充分析维度（学生工程化门槛、Element Plus 适配细节）；v0.2：问题清单按「决策/策略/配套/取舍」四类重排 |
| 分析依据 | [PRD.md](../product/PRD.md) v1.1 · [DESIGN_SYSTEM.md](../design/DESIGN_SYSTEM.md) · [PAGE_SPECS.md](../design/PAGE_SPECS.md) · 原型（`原型/`） |
| 结论性质 | **保留既定技术栈，不做更换**。以下所有决策项已确认，可直接按本文档推进脚手架搭建与开发 |

---

## 1. 技术栈总览（既定，不更换）

| 层 | 技术 | 角色 |
|---|---|---|
| 前端框架 | Vue 3（Composition API + `<script setup>`） | SPA 视图层 |
| 前端语言 | TypeScript | 类型安全 |
| 构建工具 | Vite | 开发服务器 + 生产构建 |
| 状态管理 | Pinia | 全局状态（登录态、Toast、列表筛选缓存） |
| HTTP 客户端 | Axios | API 请求、拦截器、统一错误处理 |
| UI 组件库 | Element Plus | 组件库（**使用范围需确认**，见 §4.2） |
| 后端框架 | Python · FastAPI | REST API |
| 数据库 | MySQL 5.7 | 持久化存储 |
| 版本管理 | Git | 源码管理 |

> **结论**：这套栈对本项目**整体合理**。所有组件均为当前主流、社区活跃、中文资料充足的选择；没有任何一项构成明显的错误选型或能力过剩。各组件间搭配协调（Vue 3 + Vite + Pinia 是 Vue 官方推荐组合；FastAPI + MySQL 是后端常见搭配）。
>
> 需要处理的不是"换不换栈"，而是：**1 个阻塞缺口必须补、1 个范围冲突需决策、3 项配套需确认、2 项策略需定调**。

---

## 2. 项目规模评估（选型是否过大/过小）

### 2.1 规模测算（依据 PRD v1.1）

| 维度 | 估算 | 说明 |
|---|---|---|
| 前台页面 | 6 个路由（首页/列表/详情/清单/分享公开页/404）+ 登录注册模态框 | PAGE_SPECS §1.1 |
| 管理后台 | 5 个页面（登录/仪表盘/茶品列表/新增/编辑） | PAGE_SPECS §1.2 |
| 组件数量 | 约 25-35 个（原型已实现导航/卡片/筛选/骨架屏/Toast/模态框） | 原型 `js/common.js` + `js/admin.js` 可拆分数量 |
| REST 端点 | 29 个（定稿见 [API_CONTRACT.md](../api/API_CONTRACT.md) §3） | 茶品 CRUD + 筛选聚合 + 认证 + 收藏 + 清单 + 分享令牌 + 小贴士 + 上下架 |
| 数据表 | 7 张（定稿见 [DATA_MODEL.md](DATA_MODEL.md) §2：`tasting_note` 已合并入 `favorite_items`、不建 `session`、新增 `collection_lists`） | `users` / `teas` / `tea_tips` / `collection_lists` / `favorite_items` / `share_tokens` / `operation_logs` |
| 查询复杂度 | **低** | AND 筛选、双维排序、分页、`ORDER BY RAND()` 随机发现、LIKE 关键词搜索（X9 明确不做相关度算法） |
| 并发/数据量 | **小** | 初始 30-50 款茶；MVP 用户量小，无高并发、无海量数据、无实时通信 |

### 2.2 结论

- 这是**中小型 CRUD + 内容展示**项目，选型重点**不在性能与扩展性**，而在：**学习成本、与已有原型/设计规范的衔接、开发效率**。
- 既定栈没有过度设计（每个组件都有明确用途），也没有能力缺口（MySQL 5.7 + FastAPI 远超本项目查询需求）。
- 唯一"规模敏感点"：TypeScript 的类型系统对单人/小团队学生项目偏重，需要用渐进式策略控制（§4.4）。

---

## 3. 五维度综合评估

### 3.1 评分总表

| 维度 | 评价 | 说明 |
|---|---|---|
| 项目规模匹配度 | ★★★★★ | 全部组件用途明确，无冗余无缺口 |
| 学生学习成本 | ★★★☆☆ | Vue/Pinia/Axios/FastAPI 友好；**TypeScript + 工程化工具链是主要变量** |
| 开发效率 | ★★★★☆ | Vite 热更新 + FastAPI 自动文档 + Element Plus 后台提效；原型资产可复用 |
| 可维护性 | ★★★★☆ | 类型链路完整（Pydantic ↔ TS interface）；需靠约定守住上限 |
| 部署难度 | ★★★★☆ | 静态前端 + 单进程后端，结构简单；跨域与会话需注意但可解决 |

### 3.2 项目规模匹配度

任何一项技术都存在"能力过剩"，但这不构成问题——它们换来的是：
- **主流框架 → 资料多、社区大、AI 辅助查询命中率高**
- **Vite → 冷启动 300ms 以内，热更新瞬时**
- **MySQL 5.7 → 对本项目的筛选聚合（茶类计数、收藏数统计、随机发现）绰绰有余**
- **FastAPI → 异步能力本项目用不到，但 Pydantic 校验和自动生成 OpenAPI 文档对前后端并行开发有实际价值**

### 3.3 学生学习成本（逐项 + 工程化门槛）

> 评估假设：学生已有 JS（ES6+）基础和 Python 基础，无企业级开发经验。

#### 框架/语言逐项成本

| 技术 | 上手难度 | 成本说明 |
|---|---|---|
| Vue 3 + `<script setup>` | 低-中 | 官方中文文档质量高；组合式 API 约需 1-2 周形成肌肉记忆；Options API 写法可平滑过渡 |
| TypeScript | **中-高** | 泛型、接口定义、第三方库类型声明是主要门槛；详见 §4.4 渐进式策略 |
| Vite | 低 | 几乎零配置开箱即用；与 Vue CLI/Next.js 相比心智负担极小 |
| Pinia | 低 | API 面很小（`defineStore` / `state` / `getter` / `action`），半天可掌握 |
| Axios | 低 | 拦截器写法固定，本项目常用场景仅 3-5 种（GET/POST/拦截器/错误处理） |
| Element Plus | 低 | 组件用法文档齐全；**但主题定制有隐性成本**（§4.2） |
| FastAPI | 低-中 | Python 语法友好，装饰器路由直观；**建议先当同步写**（不用 `async def` 也能跑通） |
| SQLAlchemy 2.0（**配套建议**） | **中** | 后端最大的学习项；ORM 概念 + 关系映射 + Session 管理 |
| Alembic（**配套建议**） | 低-中 | 迁移命令固定：`alembic revision --autogenerate` → `alembic upgrade head` |
| MySQL 5.7 | 低 | 大学课程常见；Navicat/DBeaver 等 GUI 工具成熟 |

#### 工程化工具链的隐性门槛（v0.3 新增）

| 工具 | 学生常见困惑 | 建议 |
|---|---|---|
| npm | 依赖版本、`node_modules`、`package-lock.json` | 统一使用 npm（仓库已有 `package-lock.json`，不引入第二套 lockfile）；Node.js ≥ 20 |
| Python 虚拟环境 | venv vs conda vs poetry 混淆 | **强制统一用 venv + pip**，文档写入"第一节课先配好 `python -m venv .venv` 和 `pip install -r requirements.txt`" |
| Git | rebase vs merge 混淆、commit message 不规范 | 用最简单的方式：`git checkout -b feature/xxx` → `git add .` → `git commit -m "feat: xxx"` → `git push` → 合并时用 GitHub/Gitee PR |

### 3.4 开发效率

- **前端**：Vite 冷启动快、热更新瞬时；Element Plus 的 `el-table` / `el-form` / `el-upload` 直接覆盖管理员后台 A3-A5 的核心需求（表格视图 + 表单校验 + 图片上传），这是它在本项目的最大价值点。
- **后端**：FastAPI 自动生成 `/docs` 交互式 API 文档，前后端可基于契约并行——前端按 schema 先行 mock，后端按 schema 实现 Truth。
- **类型链路**：FastAPI 的 OpenAPI schema 可通过 `openapi-typescript` 自动生成前端 TS 类型，Pydantic 模型 ↔ TS interface 单一来源，减少前后端字段不一致这类学生项目最常见的联调 bug。
- **原型资产复用**：`原型/` 目录已有完整的 HTML/CSS/交互实现和约 30 条 mock 数据。前台页面本质是"Vue 组件化迁移"，`原型/js/mock/teas.js` 可直接转为前端开发期 mock（或后端种子数据），起跑成本低。

### 3.5 可维护性

主流框架 + 强类型 = 可维护性下限高。需要靠**约定**守住上限（建议写入后续开发规范）：

| 约定 | 说明 |
|---|---|
| 后端分层 | `routers / services / models / schemas` 四层，路由不写业务逻辑 |
| 统一响应体 | `{ code: number, message: string, data: any }` + 错误码表（附录，PRD 未定义需补） |
| 数据库变更 | 一律走 Alembic 迁移，禁止手工改表 |
| 代码规范 | 前端 ESLint + Prettier；后端 Ruff；提交前统一格式化 |
| 设计 token | 七大茶类颜色等设计 token 已在 DESIGN_SYSTEM.md 定义为 CSS 变量，前后台共用一份 `:root` 变量文件，避免硬编码色值 |

### 3.6 部署难度

#### 结构简单

前端 `vite build` 产出纯静态文件（dist/）；后端单进程 Uvicorn（小项目无需 Gunicorn 多 worker + Nginx 也能跑，生产建议 Nginx 反代）。

#### 推荐拓扑（低成本）

```
浏览器 ──► Nginx (80/443)
            ├── /            ─► 前端静态文件（Vite 产物 dist/）
            ├── /api/*       ─► 反向代理 ─► Uvicorn (FastAPI, 127.0.0.1:8000)
            └── /uploads/*   ─► 本地磁盘图片目录（或同走 /api 静态挂载）
                        │
                  MySQL 5.7 (本机或同网段)
```

#### 两个必须提前想清楚的点

1. **跨域与会话**：PRD FR-4.3 要求 30 天 Cookie 会话。
   - 开发期：前端 5173 / 后端 8000 跨源，需后端 CORS 配置 `allow_credentials=True` 且 Cookie 设置 `SameSite=Lax`、`Secure=false`（HTTP 环境下 `Secure` 会导致 Cookie 不发送）。
   - **更省事的做法**：Vite `server.proxy` 把 `/api` 代理到 8000，前后端全程同源，CORS 配置仅为兜底。
   - 生产期：经 Nginx 同域反代后跨域问题自然消失。

2. **图片存储**：PRD Q-03 建议 MVP 本地磁盘。FastAPI 用 `StaticFiles` 挂载 uploads 目录即可，迁移云存储（OSS/S3）时只换 URL 生成逻辑。

#### 可选增强（非必需）

Docker Compose（`web` + `api` + `mysql` 三容器）让部署可复制、答辩演示环境可一键重建。学生项目可先不上，部署阶段再补。

---

## 4. 识别的问题与建议

> 问题按性质分四类，优先级从上到下递减：
> **A 决策类**（不拍板无法开工）→ **B 策略类**（不阻塞但影响进度）→ **C 配套类**（建议采纳的补充清单）→ **D 取舍类**（已评估并接受的架构代价，记录在案）。

### 4.1 【A 决策 · 必须补】缺 Vue Router

**现象**：既定栈内没有路由方案。本项目至少 6 个前台路由 + 5 个后台路由，且 PRD 依赖 URL 参数传递筛选状态（`?category=green`、`?q=西湖龙井`，PAGE_SPECS §3.4）和"登录后回到触发页"（FR-4.1），无路由无法实现。

**建议**：补充 **Vue Router 4**（Vue 官方标配，无替代讨论必要）。学习成本极低，且路由参数（`useRoute` / `useRouter`）正好承接原型已有的 URL 参数设计。

**已确认 ✅**：补充 Vue Router 4

---

### 4.2 【A 决策 · 必须拍板】Element Plus 与现有设计规范冲突

**现象**：这是既定栈唯一真正的适配问题。
- DESIGN_SYSTEM.md 定义了强定制视觉：茶褐色主色 `#8B7355`、七大茶类专属色、"清新水墨"新中式极简风格、胶囊按钮、自绘卡片——原型已用约 32KB 手写 CSS 完整实现；
- Element Plus 自带蓝色系（`#409EFF`）视觉语言与独立组件样式，前台页面若直接套用，将与设计规范明显冲突；深度定制需覆盖大量 `--el-*` CSS 变量，且部分组件（表格、日期选择等）细节还原度低。

**三个方案（任选其一，均不更换既定栈主体）**：

| 方案 | 做法 | 优点 | 代价 |
|---|---|---|---|
| **A（强烈推荐）** | 前台页面**不用** Element Plus，将原型 CSS 迁移为自研 Vue 组件；Element Plus **仅用于管理员后台**（A1-A5） | 前台 100% 还原设计规范；后台借 EP 的表格/表单/上传快速交付；工作量分离清晰 | 维护两套组件风格（后台默认蓝主题通常可接受） |
| B | 全站 Element Plus + 深度主题定制（`--el-color-primary` 等变量映射茶褐色系） | 技术栈单一 | 主题定制工作量大；"新中式极简"风格细节还原度低；原型 CSS 大部分废弃重做 |
| C | 全站不用 EP，后台也自研组件 | 视觉统一 | 后台表格/表单/上传全部手写，工作量最高，**不建议** |

> v0.3 补充：采用方案 A 后，管理员后台的 Element Plus 默认蓝色（`#409EFF`）与"清新水墨"风格的前台是隔离的——后台是工具属性页面，默认蓝完全可接受，不需要再定制成茶褐色。

**关联决策：管理员后台与前台是否同一个 SPA？**

| 选项 | 做法 | 说明 |
|---|---|---|
| **单 SPA（推荐）** | 同一应用内用 `/admin` 路由段 + 路由守卫 + 动态 `import()` 按需加载后台代码 | 部署最简（一次构建一套产物）、共享登录态与 API 层，符合本项目体量 |
| 两个独立应用 | 前台、后台各一个 Vue 工程，分开构建部署 | 故障隔离好；代价是两套脚手架、两套部署、公共代码要抽包，本项目规模下收益不大 |

**已确认 ✅**：Element Plus 使用范围 — 方案 A（仅管理后台使用 EP，前台自研组件迁移原型）
**已确认 ✅**：前后台拆分方式 — 单 SPA + `/admin` 路由段 + 路由守卫 + 动态 `import()` 按需加载后台代码

---

### 4.3 【A 决策 · 随 §4.2 一并定】CSS 方案

DESIGN_SYSTEM.md 是按 Tailwind v4 `@theme` 语法写的 token，而原型实际是手写 CSS。两个衔接选项：

| 选项 | 做法 | 说明 |
|---|---|---|
| **a（推荐，配 §4.2 方案 A）** | 把 `@theme` token 转写为 `:root` CSS 自定义属性，延续原型手写 CSS + BEM 类名 | 与原型零缝隙衔接，零新依赖，设计文档中的值原样搬运 |
| b | 引入 Tailwind CSS v4 | 与设计文档工具类命名（`bg-primary` 等）一致，但团队需再学一套工具类语法 |

**已确认 ✅**：CSS 方案 — 选项 a（把 DESIGN_SYSTEM.md 的 `@theme` token 转写为 `:root` CSS 自定义属性，延续原型手写 CSS + BEM 类名）

---

### 4.4 【B 策略】TypeScript 学习成本

**现象**：TS 是既定栈对学生的最大成本项。若全队 JS 基础一般，严格模式（`strict: true`）会在开发初期产生大量与业务无关的类型报错，拖慢进度、挫伤积极性。

**建议**（保留 TS，不换回 JS）：
1. `tsconfig` 初期宽松：`strict: false` 起步；代码稳定后按模块逐步开启严格选项。
2. 类型定义集中在 `src/types/`（与后端 Pydantic 一一对应），禁止到处散落 `any`。
3. 若团队完全零 TS 经验，可退一步：业务代码用 TS 基础类型（`string` / `number` / `interface`），不碰泛型工具类型（`Partial` / `Pick` / `Record` 等）。

**已确认 ✅**：TypeScript 策略 — 初期宽松（`strict: false`）起步，类型定义集中在 `src/types/`，业务代码用基础类型，不碰泛型工具类型

---

### 4.5 【C 配套 · 建议采纳】后端组件清单（FastAPI 本体不包含）

FastAPI 本体是轻量框架，不自带 ORM、迁移、数据库驱动、密码哈希等。以下为**建议补充**，不强制，但采纳后开发效率显著提升：

| 用途 | 建议 | 理由 | 备选 |
|---|---|---|---|
| ORM | SQLAlchemy 2.0（**同步模式**） | 事实标准、资料最多；本项目无高并发，同步写法更易理解，无需先学异步 | SQLModel（FastAPI 作者出品，模型同时当 Pydantic 用，样板更少，但社区资料少） |
| 数据库迁移 | Alembic | SQLAlchemy 官方配套；命令固定 | 手写 SQL 脚本（**不推荐**，易漂移） |
| MySQL 驱动 | PyMySQL（纯 Python） | Windows 安装零障碍，`pip install pymysql` 即可 | mysqlclient（需编译环境，Windows 易踩坑） |
| 密码哈希 | `bcrypt` 库直接使用 | PRD 4.3 指定 bcrypt；避开 passlib 与 bcrypt 4.x 的已知兼容问题 | passlib（需锁旧版本） |
| 会话管理 | HttpOnly Cookie + itsdangerous 签名令牌（**不建服务端 session 表**，见 [DATA_MODEL.md](DATA_MODEL.md) §1） | 契合 FR-4.3 的 30 天 Cookie 要求，实现简单 | JWT（无状态但撤销麻烦，MVP 无必要） |
| 文件上传 | FastAPI `UploadFile`（需 `python-multipart`） | 官方标准做法 | — |
| API 测试 | pytest + httpx（FastAPI TestClient） | 见 §4.6 | — |
| 代码规范 | Ruff（lint + format 合一） | 轻量、一个工具替代 flake8/black/isort | — |

**已确认 ✅**：后端配套采纳 — SQLAlchemy 2.0（同步模式）+ Alembic + PyMySQL + bcrypt + HttpOnly Cookie + FastAPI UploadFile + pytest + Ruff

---

### 4.6 【C 配套 · 建议采纳】测试策略

既定清单没有测试方案。课程/毕设通常要求测试交付物，且本项目有天然适合单测的纯逻辑（三维度 AND 筛选、排序、分享令牌校验、权限判断）。

| 层 | 建议 | 范围控制 |
|---|---|---|
| 后端 | pytest + httpx（FastAPI TestClient） | 覆盖核心 API：认证、收藏、筛选、分享令牌；不必全量 |
| 前端 | Vitest | 仅纯函数（筛选/格式化/URL 组装），组件测试可选 |
| E2E | 可选 Playwright 冒烟（注册 → 收藏 → 分享主链路） | 1 条主旅程即可，时间紧可砍 |

**已确认 ✅**：测试范围 — 后端 pytest + httpx（核心 API 覆盖）、前端 Vitest（纯函数覆盖）、可选 Playwright 冒烟

---

### 4.7 【C 配套 · 建议采纳】Git 协作约定

- 分支：`main` 保护 + `feature/xxx` 短分支，合并即删；
- 提交信息：`类型: 摘要`（`feat` / `fix` / `docs` / `refactor`）；
- `.gitignore` 首日配好：`node_modules/`、`dist/`、`.venv/`、`__pycache__/`、`uploads/`、`.env`。

---

### 4.8 【D 取舍 · 已评估接受】SPA 对 SEO 不友好

- **代价**：Vue SPA 内容由 JS 渲染，搜索引擎收录弱；分享链接在微信等内置浏览器没有"链接预览卡片"。
- **为何可接受**：PRD 无 SEO 需求——发现路径全在站内（首页入口 / 筛选 / 搜索 / 推荐），分享页的核心诉求是"打开可看"而非"被索引"。
- **逃生舱**：若未来需要，可单独给 `/c/{shareId}` 分享页做后端直出 HTML（FastAPI 返回 Jinja2 模板页，成本可控），无需改整体架构。

---

### 4.9 【D 取舍 · 其余已评估项】

| 项 | 结论 |
|---|---|
| CSRF | Cookie 会话理论上有 CSRF 面；同域部署 + `SameSite=Lax` + 本项目无跨站表单场景，MVP 不做 CSRF token，记录即可 |
| 随机发现 `ORDER BY RAND()` | 数据量 < 1000 行无性能问题，PRD 规模内可用 |
| 图片本地磁盘存储 | MVP 可接受（PRD Q-03），迁移 OSS/S3 时只换 URL 生成逻辑 |
| Pinia 必要性 | 本项目仍有登录态 / Toast / 筛选缓存三类全局状态，保留合理 |
| Axios vs fetch | Axios 拦截器对统一错误处理有价值，保留合理 |

---

## 5. 建议的仓库组织

```
d:\项目二\
├── docs/                  # 已有：product / design / architecture
├── 原型/                  # 已有：静态原型（归档保留，作为前台还原基准）
├── frontend/              # 新建：Vue 3 + TS + Vite
│   └── src/
│       ├── api/           # Axios 实例 + 各模块请求封装
│       ├── assets/        # 静态资源（图片、字体）
│       ├── components/    # 通用组件（导航、卡片、筛选、Toast、模态框）
│       ├── composables/   # 组合式函数（useAuth、useTeaFilter 等）
│       ├── router/        # Vue Router 路由表（含 /admin 段守卫）
│       ├── stores/        # Pinia stores（user、tea、toast）
│       ├── styles/        # 全局样式（:root CSS 变量 + 原型 CSS 迁移）
│       ├── types/         # 共享 TS 类型定义（与后端 Pydantic 一一对应）
│       ├── views/         # 页面组件（首页、列表、详情、清单、分享、登录模态框）
│       ├── App.vue
│       └── main.ts
├── backend/               # 新建：FastAPI
│   └── app/
│       ├── routers/       # 各模块路由（auth、teas、favorites、lists、shares、admin）
│       ├── services/      # 业务逻辑层
│       ├── models/        # SQLAlchemy ORM 模型
│       ├── schemas/       # Pydantic 请求/响应模型
│       ├── core/          # 配置、数据库连接、安全工具
│       ├── alembic/        # 数据库迁移（初始化 Alembic 后生成）
│       └── main.py        # FastAPI 入口
└── README.md
```

> **注意**：当前工作区根目录残留有此前实验的 `next.config.ts`、`package.json`、`src/app/`（Next.js App Router 结构）、`drizzle.config.ts` 等文件，与既定栈无关。初始化 Git 时应通过 `.gitignore` 排除，并建议清理或移出这些残留目录，避免误提交与检索干扰。

---

## 6. 版本基线建议

> 原则以安装时点的最新稳定版为准，下表为最低兼容基线。

| 组件 | 基线 | 备注 |
|---|---|---|
| Node.js | ≥ 20 LTS | Vite 要求 |
| Vue | 3.4+ | `<script setup>` 稳定可用 |
| Vite | 5+ | — |
| TypeScript | 5.x | 严格策略见 §4.4 |
| Pinia | 2.2+ | — |
| **Vue Router** | **4.x** | **待确认补充，见 §4.1** |
| Element Plus | 2.x | 使用范围见 §4.2 |
| Axios | 1.x | — |
| Vitest / pytest | 最新稳定 | 测试配套，见 §4.6 |
| Python | 3.11 – 3.13 | 团队统一同一版本，写入 README |
| FastAPI | 最新稳定 | — |
| **SQLAlchemy / Alembic** | **2.0.x / 1.13+** | **待确认采纳，见 §4.5** |
| MySQL | 5.7.19.0（社区版，5.7 系列通用） | 字符集统一 `utf8mb4`，排序规则 `utf8mb4_unicode_ci`（兼容 5.7/8.0，避免 8.0 特有的 `utf8mb4_0900_ai_ci`） |

---

## 7. 确认清单（v1.0 定稿 · 全部已确认）

| # | 决策项 | 类别 | 确认结果 |
|---|---|---|---|
| 1 | 补充 Vue Router 4 | A · 阻塞缺口 | ✅ 采纳 |
| 2 | Element Plus 使用范围 | A · 范围冲突 | ✅ 方案 A：仅管理后台，前台自研组件迁移原型 |
| 3 | 前后台拆分方式 | A · 架构决策 | ✅ 单 SPA + `/admin` 路由段 |
| 4 | CSS 方案 | A · 配套决策 | ✅ 选项 a：CSS 自定义属性延续原型手写 CSS |
| 5 | TypeScript 严格策略 | B · 开发策略 | ✅ 初期宽松（strict:false）、逐步收紧 |
| 6 | 后端配套采纳 | C · 工具链 | ✅ SQLAlchemy 2.0 + Alembic + PyMySQL + bcrypt + Cookie 会话 |
| 7 | 测试范围 | C · 质量保障 | ✅ pytest + Vitest，可选 Playwright 冒烟 |
| 8 | 仓库结构 + Git 约定 | C · 工程化 | ✅ `frontend/` + `backend/` 双目录 + 约定（见 §5 / §4.7） |
| 9 | 部署目标环境 | D · 后续决策 | ⏳ 部署阶段再定（本地演示 / 云服务器 / 是否 Docker Compose） |

> 取舍类（§4.8 / §4.9）默认"记录在案、接受"，已随文档一并确认。

---

## 附录：一句话总结

这套 Vue 3 + TS + Vite + Pinia + Axios + Element Plus / FastAPI / MySQL 5.7 / Git 的技术栈对本项目**整体合理，无错误选型**。开工前需确认 5 个缺口与决策（补 Vue Router、定 EP 使用范围、定 CSS 方案、定 TS 策略、定后端配套），其余细节可在开发过程中按既定约定推进。
