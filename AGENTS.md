# AGENTS.md —— AI 编程助手全局工作指南

> 本文件是进入项目的入口：只保留**速览、索引、红线、现状基线**。
> 详细业务与技术规则以 `docs/` 下的权威文档为准；详细流程以 [DEVELOPMENT_GUIDE.md](docs/development/DEVELOPMENT_GUIDE.md) 为准。
> 项目阶段：**MVP + 第二阶段扩展已完成**。PRD S1–S17 已全部实现并冻结；X1–X13 维持不开发；新增功能需求按 C 类先确认。

---

## 0. 60 秒速览

**茶·图鉴**：七大茶类（六大基础茶类 + 再加工茶）结构化知识库。核心闭环 **发现茶 → 查看详情 → 收藏/写笔记/分享**。

### 0.1 常用命令（统一使用 npm）

| 场景 | 命令 |
|---|---|
| 启动后端 | `cd backend; python run.py` |
| 启动前端 | `cd frontend; npm install; npm run dev` |
| 后端检查 | `cd backend; python -m ruff check app tests; python -m pytest -q` |
| 前端检查 | `cd frontend; npm run lint; npm run typecheck; npm run test:run` |
| 全量静态检查 | `python scripts/check_all.py` |

### 0.2 五条红线

1. **冻结规则不改**：业务规则、权限矩阵、API 契约、表结构、安全项、架构分层变更 → C 类，先确认。
2. **五层不跨层**：Router 不写业务、不查库；Service 不拼 SQL；Repository 不做业务判断；Schema 不 import Model。
3. **契约/数据变更必须同步文档**：未同步不得标记完成。
4. **测试必须实跑**：未运行写「未运行」，失败/跳过如实写，禁止虚报。
5. **交付必须留痕**：`harness/build-log.md` 追加条目；重要决策写 ADR。

### 0.3 任务路由表（先读这 3 份，再动手）

| 任务类型 | 最少必读 | 典型分级 |
|---|---|---|
| 后端端点 | API_CONTRACT 对应端点 + ARCHITECTURE §3/§5 + SECURITY 相关 S 项 | B（改契约则 C） |
| 认证/权限/会话 | SECURITY 认证项 + API `auth` 端点 + TEST_PLAN AUTH/PERM | C（实现向文档对齐为 B） |
| 收藏/清单/分享 | PRD 对应章节 + API `favorites/lists/shares` + SECURITY 越权项 | B |
| 管理员后台 | API `admin` 端点 + SECURITY 管理员门禁 + PAGE_SPECS 后台页 | B |
| 数据库/迁移 | DATA_MODEL 相关表 + `database/init.sql` + ARCHITECTURE §5.4 | **C** |
| 前台页面/样式 | PAGE_SPECS 对应页 + DESIGN_SYSTEM + `原型/` | A/B |
| 测试代码 | TEST_PLAN 用例 + API_CONTRACT + SECURITY | B |
| 文档修订 | 目标文档 + 本文件 §10 | A/B |

### 0.4 开工顺序

**填任务卡 → 定 A/B/C/D → 读文档 → 分析影响面 → 写方案（B/C）→ 编码 → 测试 → 自检 → 同步文档 → 回填 build-log**。
任务卡见 [harness/TASK_TEMPLATE.md](harness/TASK_TEMPLATE.md)。C 类必须先停下来等用户确认。

---

## 1. 项目背景与核心目标

**茶·图鉴** —— 面向茶爱好者的七大茶类（六大基础茶类 + 再加工茶）结构化知识库平台。

- 核心闭环：**发现茶 → 查看详情 → 收藏/写笔记/分享**
- 三角色：游客（只读）/ 注册用户（收藏、笔记、分享）/ 管理员（茶品与小贴士维护）
- MVP 边界：多收藏清单（默认清单 + 最多 9 个普通清单）；3 维筛选（茶类/产地/季节，AND 逻辑）；链接分享；不做用户贡献与审核
- 权威需求文档：[PRD.md](docs/product/PRD.md) v1.1（功能分级以此为准）

## 2. 技术栈（已定稿，不更换）

| 层 | 技术 |
|---|---|
| 前端 | Vue 3（`<script setup>`）+ TypeScript（初期 `strict: false`）+ Vite + Vue Router 4 + Pinia + Axios |
| UI | **Element Plus 仅用于管理员后台**；前台自研组件（迁移原型 CSS，`:root` 变量 + BEM） |
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy 2.0（**同步模式**）/ Alembic / PyMySQL / bcrypt / itsdangerous |
| 数据库 | MySQL **5.7.19** · InnoDB · `utf8mb4` / `utf8mb4_unicode_ci` |
| 测试 | 后端 pytest + httpx；前端 Vitest（纯函数）；可选 Playwright 冒烟 |
| 部署 | 开发期 Vite proxy `/api` → 8000 同源；生产 Nginx 反代 + Uvicorn |
| 包管理 | **npm**（`frontend/package-lock.json` 为唯一 lockfile）；Python 统一 venv + pip |

详见 [TECH_STACK.md](docs/architecture/TECH_STACK.md) v1.0（9 项决策全部已确认）。

## 3. 项目目录结构

```
d:\项目二\
├── docs/                 # 全部已确认文档（见 §10）
├── frontend/             # Vue 3 SPA（含 /admin 路由段，后台组件动态 import）
│   └── src/{api, assets, components, router, stores, styles, types, views}
├── backend/              # FastAPI
│   └── app/
│       ├── routers/  services/  repositories/  models/  schemas/   # 五层（见 §5）
│       ├── core/     # config / database / security / response / auth_deps
│       ├── alembic/  # 数据库迁移
│       └── tests/    # pytest 骨架（当前仅健康检查）
├── database/init.sql     # 建库 + 建表 + 索引 + 种子数据
├── scripts/              # 静态检查脚本（链接/常量/分层/UI/记录/密钥）
├── harness/              # 任务卡与 build-log
├── .github/              # CI 与 PR 模板
├── 原型/                 # 静态原型（前台视觉还原基准，勿改）
└── uploads/              # 图片本地存储（backend/uploads/）
```

### 3.1 现状基线（允许暂时存在，禁止新增）

规范描述的是目标状态，仓库当前仍有已知遗留。**新 AI 不得据此判断"规则可忽略"，也不得借机大规模重构。**

| 遗留 | 现状 | 处理规则 |
|---|---|---|
| Element Plus 前台使用（已修复） | 前台 `AppToast` 自研；`main.ts` 仅在 `/admin` 路由按需加载 Element Plus | 前台禁止再引入；后台保持按需加载 |
| Service 直连查询（已修复） | 查询已全部下沉到 `repositories/`；`check_layers.py` 基线为空 | 保持五层边界，禁止回流 |
| Router/Service 返回 ORM（已修复） | 端点统一经 Schema 序列化后返回 | 保持统一响应体，禁止直接返回 ORM |
| 业务端点未实现（已修复） | 60 个业务端点已按 API_CONTRACT 实现 | 新增端点必须同步契约与测试 |
| 测试未覆盖 TEST_PLAN（已修复） | TEST_PLAN 100 条用例已落地，后端全量 190 条测试通过 | 新增业务代码必须同步补测 |
| 例外登记 | 运行 `python scripts/check_layers.py` / `check_frontend.py` 查看最新列表 | 修复后同步更新脚本基线 |

## 4. 前端开发规范

- 目录职责：`api/`（Axios 实例与请求封装，`baseURL=/api/v1`，`withCredentials: true`）、`types/`（与后端 Pydantic Schema 一一对应）、`stores/`（user/tea/toast）、`views/`（页面）、`components/`（通用组件）
- 前台禁用 Element Plus，视觉以 `原型/` 为还原基准；后台组件放 `views/admin/`，动态 `import()` 按需加载
- 全局样式用 `:root` CSS 自定义属性 + BEM 类名；**`style.css` 是唯一允许定义 HEX 的 Token 文件**，组件内只引用变量
- 前端路由守卫、按钮禁用只做体验，**不构成安全边界**
- 代码规范：`npm run lint` / `npm run format:check` / `npm run typecheck`，提交前必须通过
- 单元测试：`npm run test:run`（Vitest，仅纯函数）

详见 [TECH_STACK.md](docs/architecture/TECH_STACK.md) §4.2/§4.3/§4.4、[ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) §1。

## 5. 后端开发规范（五层架构，红线禁止跨层）

| 层 | 职责 | 红线 |
|---|---|---|
| `routers/` | 路由声明、参数接收、Depends 注入 | 禁止写业务逻辑、禁止直接查库、禁止返回 ORM 对象 |
| `services/` | 业务规则、权限判断、事务边界 | 禁止拼 SQL、禁止返回 ORM 对象 |
| `repositories/` | 封装 SQLAlchemy 查询 | 禁止业务判断、禁止抛业务异常 |
| `models/` | ORM 实体，与表一一对应 | 只有 Repository 能碰；禁止业务方法 |
| `schemas/` | Pydantic DTO，与前端 `types/` 对应 | 禁止 import Model |

- `core/` 为横向支撑（config / database / security / response / auth_deps）
- 统一响应体 `{ code, message, data }`，业务异常经 `core/response.py` 映射
- 代码规范：Ruff（`ruff check` + `ruff format --check`）
- 安全控制共 35 项（S-01–S-35），变更必须同步 [SECURITY.md](docs/architecture/SECURITY.md) 与测试用例
- 静态检查：`python scripts/check_layers.py`

详见 [ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) §3、[SECURITY.md](docs/architecture/SECURITY.md)。

## 6. 数据库规范

- 共 **14 张表**：`users` / `teas` / `tea_tips` / `tea_brewing_guides` / `collection_lists` / `favorite_items` / `share_tokens` / `operation_logs` / `tea_media` / `login_attempts` / `contributions` / `tea_name_category_map` / `content_types` / `content_items`
- **一切结构变更走 Alembic 迁移，禁止手工 ALTER TABLE**
- MySQL 5.7 无有效 CHECK：枚举用 ENUM，数值/长度范围由 Pydantic + Service 层校验
- 时间统一 `DATETIME` + UTC，API 输出 ISO8601 带 `Z`，前端按 Asia/Shanghai 渲染
- 软失效：茶下架（`is_active=0`）、分享撤销（`is_active=0` + `revoked_at`）均**不物理删除**
- `share_tokens.token` 用 `utf8mb4_bin`（大小写敏感）；`teas.favorite_count` 为冗余计数，同事务维护
- 收藏防重复靠 `UNIQUE(list_id, tea_id)`；默认清单唯一靠 `UNIQUE(user_id, is_default)`（普通清单 `is_default=NULL`）；`favorite_count` 按「用户 × 茶品」跨清单去重

详见 [DATA_MODEL.md](docs/architecture/DATA_MODEL.md) v1.0、[database/init.sql](database/init.sql)。

## 7. API 接口规范

- 统一前缀 `/api/v1`；共 **60 个业务端点**（auth 6 / me 3 / teas 9 / tips 1 / favorites 3 / lists 6 / shares 4 / admin 17 / contributions 3 / contents 3 / admin-contents 5）
- 统一响应 `{ code, message, data }`；成功判定只看 `code === 0`；成功 HTTP 状态统一 **200**；业务失败 `HTTP status = code // 100`；FastAPI 422 必须重映射为 400/`40000`
- 认证：**HttpOnly Cookie `tea_session`**（itsdangerous 签名，30 天，`SameSite=Lax`），不使用 Token / Authorization 头；角色每次从 `users.role` 实时读库
- JSON 字段 `snake_case`，与数据库列名一致；空值用 `null`
- 分页仅茶品列表：默认 `page_size=12`，上限 50，越界夹取；排序稳定次级键 `id DESC`
- 上传：`POST /admin/upload`，仅 JPEG/PNG/WebP ≤ 5MB，校验魔数，UUID 文件名

**字段命名与端点行为的唯一依据**：[API_CONTRACT.md](docs/api/API_CONTRACT.md) v1.0 + [openapi.yaml](docs/api/openapi.yaml)。代码与契约冲突时以契约为准。

## 8. UI 设计规范

- 设计方向：**「清新水墨」新中式极简 × 东方留白**
- 主色茶褐 `#8B7355`；七大茶类各有专属标签色；页面背景暖米白 `#FAF8F5`
- 所有色值/字号/间距以 CSS 变量提供，组件内引用变量，**禁止硬编码 HEX**
- 茶类标签选中态规则、白茶特例等细节见规范原文
- 页面结构、布局与交互以 [PAGE_SPECS.md](docs/design/PAGE_SPECS.md) 与 `原型/` 为准

详见 [DESIGN_SYSTEM.md](docs/design/DESIGN_SYSTEM.md)、[PAGE_SPECS.md](docs/design/PAGE_SPECS.md)。

## 9. 测试要求

- 测试方案：[TEST_PLAN.md](docs/testing/TEST_PLAN.md) v1.7 —— **100 条用例**（高 56 / 中 41 / 低 3），覆盖 60 端点 + 14 表约束 + 35 项安全控制
- 后端：pytest + httpx（TestClient），断言同时检查 HTTP 状态码、业务 `code`、数据库最终状态
- 前端：Vitest，仅覆盖纯函数（筛选/格式化/URL 组装）
- 高优先级用例任一失败 = 阻断发布；错误响应不得泄露堆栈/SQL/表名
- TEST_PLAN 用例已按模块落地；新增业务代码必须同步新增或补跑对应用例，未运行写「未运行」
- 完成任务后必须执行与改动相关的测试，并如实报告结果；用户豁免需在 build-log 记录原因与风险

## 10. 文档维护要求

| 文档 | 地位 |
|---|---|
| [PRD.md](docs/product/PRD.md) | 功能分级与业务规则的唯一依据 |
| [TECH_STACK.md](docs/architecture/TECH_STACK.md) | 技术选型定稿 |
| [ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) | 架构与五层职责定稿 |
| [MODULE_DESIGN.md](docs/architecture/MODULE_DESIGN.md) | 模块与端点映射 |
| [DATA_MODEL.md](docs/architecture/DATA_MODEL.md) + [init.sql](database/init.sql) | 数据库定稿 |
| [API_CONTRACT.md](docs/api/API_CONTRACT.md) + [openapi.yaml](docs/api/openapi.yaml) | 前后端联调唯一依据 |
| [SECURITY.md](docs/architecture/SECURITY.md) | 安全控制唯一依据（S-01–S-35） |
| [DESIGN_SYSTEM.md](docs/design/DESIGN_SYSTEM.md) / [PAGE_SPECS.md](docs/design/PAGE_SPECS.md) | 视觉与页面规范 |
| [TEST_PLAN.md](docs/testing/TEST_PLAN.md) | 测试用例唯一依据 |
| [DEVELOPMENT_GUIDE.md](docs/development/DEVELOPMENT_GUIDE.md) | SDD 流程、任务分级与各阶段产出 |
| [docs/api/README.md](docs/api/README.md) / [docs/architecture/README.md](docs/architecture/README.md) | 文档目录与变更同步清单 |
| [TASK_TEMPLATE.md](harness/TASK_TEMPLATE.md) | 统一任务卡 |
| [build-log.md](harness/build-log.md) | 每次开发任务的变更、测试证据与遗留问题 |
| [ADR/](docs/development/ADR/README.md) | 重要架构与技术决策的原因、备选方案与最终选择 |
| [.github/pull_request_template.md](.github/pull_request_template.md) | PR 任务卡与证据清单 |
| `scripts/` | 可执行的规范检查（见 §0.1） |
| `specs/` | **历史草稿，非权威**；与 `docs/` 冲突时以 `docs/` 为准 |

**文档冲突处理**：DESIGN_SYSTEM / PAGE_SPECS / TEST_PLAN 低于 PRD、API_CONTRACT、SECURITY；**PRD、API_CONTRACT、SECURITY 三者之间冲突时，停止实现并升级为 C 类**，不得自行编造规则或按个人偏好裁决。

### 10.1 开发知识沉淀机制（三层记录）

| 层 | 回答的问题 | 载体 | 何时写 |
|---|---|---|---|
| 权威文档 | **是什么**（规则唯一依据） | `docs/` 下各权威文档 | 行为变化时**必须**同步 |
| ADR | **为什么**（原因 + 备选方案 + 最终选择） | [docs/development/ADR/](docs/development/ADR/README.md) | 重要架构/技术决策 |
| build-log | **做了什么、测了什么、还剩什么** | [harness/build-log.md](harness/build-log.md) | **每个开发任务交付前必写一条** |

- 判定口诀：**"为什么"能在现有权威文档里找到吗？** 能找到 → build-log；找不到 → ADR
- **C 类决策先写"提议"ADR**，用户确认后再改"已采纳"，实施后由 build-log 引用
- 接口/数据库变更必须同步文档；未同步不得标记完成
- 反复出现的错误登记到 build-log「问题复发台账」，并至少落实一项检查脚本或测试
- 只记录真实结果：未运行写「未运行」，禁止写"已通过"

## 11. AI 行为要求（红线）

1. **先理解，再动手**：修改代码前先读相关模块与文档章节，理解五层归属。
2. **不得擅自修改已确认的业务规则**：发现疑似问题时先提出并等待确认。
3. **重大修改先出方案**：架构、数据库、安全、权限变更先给方案，经确认后实施。
4. **改完必测**：执行与改动相关的测试；未通过不得声称完成。
5. **不得虚报测试结果**：未运行、失败、跳过、未覆盖都要如实说明。
6. **决策留痕**：重要取舍写入对应文档与 ADR；C 类确认记录写入任务卡/build-log。
7. **范围自律**：S1–S17 已实现，冻结现状，不擅自变更；X1–X13 维持不开发；不做无关重构、不顺手升级依赖。
8. **不泄露敏感信息**：日志、响应、提交信息不含密码明文、Cookie 值、密钥；`.env` 不进 Git。
9. **交付必留痕**：回填 build-log；接口/数据库变更同步文档。
10. **基线自律**：不得新增 §3.1 之外的违规；触达历史遗留时按表中规则修复并更新检查基线。
11. **用户豁免**：用户明确要求跳过某项测试/检查时，必须在 build-log 记录日期、原因、风险；不得默认放宽。

### 11.1 按任务风险决定是否先询问

| 可以直接执行（A 类） | 必须先确认（C 类） |
|---|---|
| 需求明确、范围小、不触碰冻结规则 | 需求描述存在歧义 |
| 无架构变化的 Bug 修复 | 修改数据库表结构 / 迁移 |
| 已明确规范的样式调整 | 修改架构分层、模块边界 |
| 已有契约的单层实现，不改端点行为 | 修改权限/认证机制、放宽安全校验 |
| 文档错别字、注释修正 | 修改 API 契约、错误码、分页/排序 |
|  | 删除数据、不可逆操作 |
|  | 引入/更换核心技术依赖 |
|  | 修改上线配置、CI 关键流程 |
|  | 修改已确认业务规则 |

**A/B 边界唯一判定**：新增或修改端点/字段/响应行为 = **B**（若契约需变更则 **C**）；只改单层内部且对外行为不变 = **A**。
B 类输出技术方案后即可编码；C 类必须等用户明确答复。

**提问方式**：信息不足时一次只提最关键的 1–3 个问题，附影响说明；其余按文档默认口径执行并在交付时注明假设。

## 12. 规范驱动开发流程（SDD）

每个任务按 [DEVELOPMENT_GUIDE.md](docs/development/DEVELOPMENT_GUIDE.md) 的十阶段执行：

**目标与来源 → 读文档 → 影响面分析 → 技术方案 → 步骤拆解 → 编码 → 测试 → 验收自检 → 同步文档 → 变更总结**

- 分级：A 直接编码 / B 方案先行 / C 确认先行 / D 范围外；**分级规则只以 DEVELOPMENT_GUIDE §2 为准**，本文件不重复定义
- **接到任务先填任务卡**：[harness/TASK_TEMPLATE.md](harness/TASK_TEMPLATE.md)，填完并定级后才可编码
- **C 类确认前先写提议 ADR**，确认记录写入任务卡与 build-log
- **交付前回填 build-log**：[harness/build-log.md](harness/build-log.md)；PR 使用 [模板](.github/pull_request_template.md)
- **接口/数据库变更强制同步**：API 变更改 `docs/api/` 两份文件 + 前端 `types/`；数据库变更改 `DATA_MODEL.md` + `init.sql` + Alembic
- 测试必须实跑并记录；高优先级用例失败即阻断交付
- 不额外创建临时 Markdown；方案需正式评审时落盘 `docs/development/plans/`

## 13. 当前已知待办

- [x] `backend/app/repositories/` 已创建，`services/auth.py`、`services/teas.py` 的查询已下沉
- [x] `core/auth_deps.py`（`get_current_user` / `get_admin_user`）已创建 —— 安全 P0
- [x] `main.py` 已注册 `register_exception_handlers`，业务异常统一映射 —— 安全 P0
- [x] `SECRET_KEY` / `DEBUG` 代码默认值已收紧（2026-11-09，缺失 `SECRET_KEY` 拒绝启动）；生产部署仍需注入随机密钥与种子管理员密码 —— 安全 P0
- [x] bcrypt 已统一为 `cost=10`（`_BCRYPT_ROUNDS`，对齐 SECURITY S-01）
- [x] `routers/admin.py` 等端点已按 API_CONTRACT 补齐
- [x] TEST_PLAN 100 条用例已落地；后端全量 190 条测试通过（2026-11-12）
- [x] §3.1 基线遗留已在 2026-11-09 审查中清理（五层 / 前台 UI 遗留均为 0）
