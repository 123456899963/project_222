# 开发构建日志（build-log）

| 项 | 值 |
|---|---|
| 用途 | 记录**每次开发任务**做了什么、测了什么、还剩什么 |
| 流程依据 | [DEVELOPMENT_GUIDE.md](../docs/development/DEVELOPMENT_GUIDE.md) · [AGENTS.md](../AGENTS.md) §10.1 |
| 记录顺序 | **最新条目置顶**（按日期倒序） |
| 定位 | 事实流水，不替代任何权威文档 |

## 2026-11-11｜内容列表页搜索区重设计（工具条化）

- 任务编号 / 分级：TASK-20261111-content-search-layout / **A**（纯前台布局与样式，不改接口、数据与业务规则）
- 背景：内容板块（`/contents/:code`）搜索框原为 Hero 下方居中的 480px 胶囊，与上下文割裂、缺少归属感。
- 改动：`frontend/src/views/ContentListView.vue`
  - Hero 改为两栏：左侧 icon + 大标题 + 描述，右侧 300px 紧凑搜索框（放大镜图标 + 清空按钮），搜索框与标题同排垂直居中。
  - 结果统计（「共 N 篇内容」/「找到 N 篇与「kw」相关的内容」）单独一行置于卡片网格上方。
  - 移动端（≤767px）Hero 纵向堆叠，搜索框撑满宽度。
  - 仅引用既有 CSS 变量，未新增硬编码色值。
- 测试（2026-11-11 实跑）：
  - `cd frontend; npm run lint / typecheck / format:check` 通过
  - Playwright + 本机 Edge，1440×960 实机截图：默认态（共 33 篇）与输入「西湖」态（找到 1 篇）均正常，标题与搜索同排、结果统计与网格对齐
  - `python scripts/check_frontend.py`、`check_links.py` 通过
- 附带发现与处理：回归时发现 8000 端口运行的是旧后端进程（OpenAPI 中 `/contents` 缺 `keyword` 参数，搜索不生效）；重启后端后 `keyword=西湖 → total=1`、`keyword=zzzz → total=0`，确认内容搜索功能本身正常，无需代码改动。
- 契约 / 数据 / 安全影响：无。
- 遗留：无。
- 回滚方式：还原 `ContentListView.vue` 单文件即可。

## 2026-11-11｜P2 工程加固：登出吊销 / 告警清理 / chunk 拆分 / Docker 部署 / Gitee CI / 截图

- 任务编号 / 分级：TASK-20261111-p2-hardening / **B + C**（登出吊销、部署与 CI 属 C，已按用户确认方案实施；其余为 B/A）
- 背景：MVP 与第二阶段功能完成后，处理工程化待办：会话吊销、弃用告警、首屏体积、部署配套、CI 与文档截图。
- 改动：
  1. **登出会话吊销（C，用户已确认）**
     - `repositories/user_repo.py` 新增 `revoke_sessions`；`services/auth.py` 新增 `logout`；`routers/auth.py` 登出改为读取可选会话并递增 `users.session_version`。
     - 旧 Cookie 重放返回 `40100`；因无 `sessions` 表，吊销粒度为用户级（该账号全部设备会话失效）。
     - 同步 SECURITY S-10 / G-12、API_CONTRACT §1.5、§4.1.4（v1.10）、TEST_PLAN AUTH-08、openapi、README。
  2. **弃用告警清理**
     - 新增 `core/clock.py::utcnow()`；8 个模型与 2 个测试文件替换 `datetime.utcnow()`；`core/config.py` 改用 `SettingsConfigDict`。
     - pytest 告警由数百条降至 1 条（仅第三方 `StarletteDeprecationWarning`）。
  3. **前端 chunk 拆分**
     - 路由除首页外全部懒加载；`vite.config.ts` 增加 manualChunks（vue/pinia/router、qrcode、element-plus）。
     - 主入口 chunk 约 1.1 MB → **95.81 kB**（gzip 34.36 kB）；Element Plus 后台异步包 998 kB 仍触发 >500 kB 提示。
  4. **修复游客访问缺陷（截图验证中发现）**
     - `api/request.ts` 的 `PUBLIC_PATHS` 增加 `/auth/me` 与 `/auth/logout`。此前游客启动 `hydrate()` 探测会话返回 401 时会触发全局拦截器跳转登录页，导致所有公开页面无法直接访问。
  5. **Docker Compose 部署（C，用户已确认）**
     - 新增 `deploy/Dockerfile.backend`、`deploy/Dockerfile.frontend`、`deploy/nginx.conf`、`docker-compose.yml`、`deploy/env.example`、`.dockerignore`。
     - `web(8080) → api(8000) → mysql:5.7`；MySQL 首次启动执行 `database/init.sql`；`uploads` 绑定挂载复用既有图片。
  6. **Gitee Go CI**
     - 新增 `.workflow/ci.yml`：后端 Ruff + 静态检查、前端 lint/format/typecheck/test/build；保留 `.github/workflows/ci.yml` 作为备份。
     - Gitee Go 云端无 MySQL，pytest 不在该流水线执行。
  7. **README 截图与基线数字**
     - 新增 `docs/images/` 9 张实机截图（前台 6 + 后台 3），README §11 更新；同步 13 张表、184 条测试、73 条 Vitest 等数字。
- 测试（2026-11-11 实跑）：
  - `cd backend; python -m ruff check app tests` / `ruff format --check` 通过
  - `cd backend; python -m pytest -q` → **184 passed，1 warning**（第三方 httpx/starlette 提示）
  - `cd frontend; npm run lint / format:check / typecheck / test:run / build` → 全过；**Vitest 73 passed（9 files）**
  - `python scripts/check_all.py` → 全过（284 条链接、常量 58/94/35/13、五层 0 违规、244 文件无敏感信息）
  - 截图经 Playwright 驱动本机 Edge 实机抓取并逐张目检；游客首页/列表/详情/分享页均正常渲染
  - `.workflow/ci.yml` 与 `docker-compose.yml` 通过 PyYAML 语法解析
- 契约 / 数据 / 安全影响：登出行为变更已同步契约与安全文档；无表结构变更（复用 0011 的 `session_version`）。
- 遗留 / 未验证：
  - 本机未安装 Docker，`docker compose config` 与容器构建未执行，未在真实服务器部署验证。
  - Gitee Go 流水线未在远端实际触发；其内置 Node/Python 版本较旧，前端步骤在流水线内自行安装 Node 20。
  - Element Plus 后台异步 chunk 仍 >500 kB，不影响前台首屏。
- 回滚方式：回退本批次提交；无新增数据库迁移，无需回滚结构。

## 2026-11-11｜茶品配图重做：Bing → 百度图片 + 相关性校验

- 任务编号 / 分级：TASK-20261111-tea-image-redo / **B**
- 背景：用户反馈首批 175 张配图与茶名不符（如"金骏眉"搜到金条、"老班章"搜到 IATA 证书），要求逐款重新配图
- 根因：Bing 图片对中文茶名匹配极差；且原脚本无相关性/质量校验，抓到即用
- 方案：
  1. 数据源切换为百度图片（`image.baidu.com/search/acjson`），优先取 `replaceUrl` 原图，兜底 `thumbURL`
  2. 标题相关性校验：标题必须含"茶"，且命中茶名/核心词，否则淘汰
  3. 正负关键词分层：优先"干茶/条索/茶汤/汤色/叶底/散茶/特写"类实拍；剔除茶树/茶园/鲜叶/礼盒/袋装/罐装/价格/批发/百科/资讯/文章等
  4. 图片质量校验：宽度 ≥ 480~500px、高宽比 0.45~2.6、近白像素占比 > 0.5~0.7 剔除（排除证书/文档/纯白商品图）
  5. 分层降级重试：严格档失败后逐级放宽；仍失败的冷门茶改用缩略图兜底
  6. 人工目检：生成 3 张带茶名的拼图核对全量 175 张，再对 50 款问题项做定向精修，最后对 20 款冷门茶逐个挑候选
- 结果：
  - 175 款全部替换为按茶名检索的图片，文件名不变（数据库 `main_image_url` 无需变更）
  - 目检确认多数为干茶/茶汤实拍；约 15 款冷门茶（如天柱剑毫、青城雪芽、页尖茶、皖西黄大茶等）公开图源仅有包装图或资讯配图，已取其中最优
- 测试：
  - `GET /api/v1/teas` 返回 total=211，`main_image_url` 均指向 `/uploads/2026/11/{茶名}_{hash}.jpg`
  - 重启后端服务正常启动
- 遗留：约 15 款冷门茶配图为包装/资讯类，后续可手工上传替换（后台茶品编辑支持上传）
- 回滚方式：图片按茶名固定命名，可重新执行 `scripts/tea_expand/download_images.py`

## 2026-11-11｜茶品批量扩充：新增 175 款茶 + 高清图

- 任务编号 / 分级：TASK-20261111-tea-batch-import / **B**（数据填充，无契约/表结构变更）
- 背景：用户反馈项目茶品数量少（原 36 款），希望批量扩充
- 方案：整理六大茶类知名茶品清单（公开茶学常识）→ AI 生成结构化数据（原创描述，无版权风险）→ Bing 图片搜索批量下载高清图 → 统一压缩为 JPEG（长边 1920）→ 入库回填
- 改动：
  1. 新增 `scripts/tea_expand/` 数据与脚本目录：
     - `data_green.py`（60 款）、`data_red.py`（30 款）、`data_oolong.py`（35 款）、`data_dark.py`（28 款）、`data_white.py`（14 款）、`data_yellow.py`（8 款）
     - `download_images.py`：Bing 图片搜索下载，HTML 实体解码，自动压缩转 JPEG
     - `import_teas.py`：按 teas 表结构入库，跳过已存在茶名，自动补 price_min/max
     - `fix_image_urls.py`：回填 main_image_url
  2. 图片统一存放至 `backend/uploads/2026/11/`，命名规则 `{茶名}_{md5前8位}.jpg`
  3. 每款茶字段完整：name/category/origin/season/fermentation/representative_variety/四段品鉴描述/冲泡参数/main_image_url/favorite_count（随机 100-2000）
- 数据规模：
  - 绿茶 66 款（原 6 + 新 60）
  - 红茶 36 款（原 6 + 新 30）
  - 乌龙 41 款（原 6 + 新 35）
  - 黑茶 34 款（原 6 + 新 28）
  - 白茶 20 款（原 6 + 新 14）
  - 黄茶 14 款（原 6 + 新 8）
  - **总计 211 款**
- 测试：
  - 图片下载 174/175 成功（青砖茶首次失败，换关键词后成功）
  - 入库 175 款全部成功，无重复
  - 接口验证：`/api/v1/teas` 列表分页（total=211）、分类筛选（green=66）、搜索（"龙井"=2 款）、详情（字段完整含图片 URL）均正常
- 契约 / 数据 / 安全影响：无契约变更、无表结构变更、无权限变更
- 遗留问题：无
- 回滚方式：`DELETE FROM teas WHERE id > 36`（假设原 36 款 id 为 1-36）

## 2026-11-10｜S9 补齐：详情页收藏清单选择面板

- 任务编号 / 分级：TASK-20261110-fav-list-picker / **B**（前端交互补齐，后端 API 原生支持，无契约变更）
- 背景：上一任务 P0 冒烟发现「前端无把茶加入非默认清单入口」（FavoriteButton 仅默认清单；后端 `addFavorite` 已支持 `list_id`，收藏状态响应已含 `list_ids`）
- 改动：
  1. [favorite.ts](../frontend/src/utils/favorite.ts)：新增纯函数 `nextListToggleState`（清单维度切换 + 「用户 × 茶品」去重口径计数联动）
  2. [FavoriteButton.vue](../frontend/src/components/FavoriteButton.vue)：primary variant 新增箭头按钮 + 清单选择面板（`role="menu"` / `menuitemcheckbox`，`aria-checked` 由 `list_ids` 驱动；懒加载 `GET /lists`；Esc/外点关闭；仅登录态渲染；乐观更新 + 失败回滚；登出重置面板状态；主按钮行为不变）
  3. icon variant（卡片快速收藏）行为不变
- 文档同步：[PAGE_SPECS.md](../docs/design/PAGE_SPECS.md) §5.6 新增面板交互规格
- 测试：
  - Vitest：新增 5 条 `nextListToggleState` 用例，全量 **50 passed**
  - `npm run format` / `format:check` / `lint` / `typecheck` 全部通过
  - 浏览器冒烟 **7/7 PASS**（建清单 → 面板开合 → 勾选加入计数 +1 → 取消计数 -1 → 复勾选 → /my 清单茶品数 = 1）
- 契约 / 数据 / 安全影响：无契约变更、无表结构变更，纯前端改动
- 遗留问题：冒烟数据 smoketest04（含 1 条非默认清单收藏记录）待清理，需用户授权后删除
- 回滚方式：回退本提交

## 2026-11-10｜P0 收尾：顶栏可访问性 + 三项冒烟 + 部署演练 + CI 本地等效

- 任务编号 / 分级：TASK-20261110-p0-closeout / **B**（AppHeader 交互修复无契约变更；其余为验证、格式化与文档修正）
- 内容 1：顶栏「茶文化 ▾」下拉支持触屏/键盘
  - [AppHeader.vue](../frontend/src/components/AppHeader.vue)：触发元素 span → button（`aria-haspopup` / `aria-expanded`），点击切换 `--open` 类，Escape 关闭并回焦按钮，点击外部 / 路由跳转自动关闭；hover 规则包进 `@media (hover: hover)`，触屏不再依赖 hover
  - 测试：`npm run lint` / `npm run typecheck` 通过；浏览器实测 **5/5 PASS**（hover 展开、点击开合 + aria 同步、Esc 关闭、外点关闭、跳转 /contents/knowledge）
- 内容 2：三项功能手工冒烟（浏览器实测）
  - 多收藏清单 + 分享海报：**7/8 PASS** —— 注册 / 收藏计数 / 建清单 / 8 位分享 token / 海报下载 / 撤销分享（旧链接显失效页）全部通过；**发现缺口：前端无「把茶加入非默认清单」入口**（FavoriteButton 仅默认清单，后端 `addFavorite` 已支持 listId）→ 遗留 B 类任务
  - 用户贡献 + 管理员审核：**5/5 PASS**（提交 → 待审核 → admin/admin123 通过 → 我的提交同步「已通过」）
  - 冒烟数据清理（**经用户明确授权**）：删除 smoketest02/03 及其清单/收藏/分享/贡献/日志 + 审核上架的测试茶「冒烟测试茶」；复核 `teas=36`、残留用户=0
- 内容 3：部署全链路演练（本地模拟全新环境）
  - 干净库 `tea_guide_deploy_check` ← init.sql（13 表 + 种子 + admin）
  - **发现并修正部署阻断**：文档旧流程「stamp 0001_baseline → upgrade head」在当前 init.sql 上必失败（0002 对已有列 `teas.video_url` 报 1060 Duplicate column）——init.sql 已随批次演进包含最新全量结构与种子
  - 修正后标准流程：全新环境 `init.sql 建库 → alembic stamp head`（演练通过，`current = 0010_user_avatar (head)`）；既有旧环境直接 `alembic upgrade head`
  - 生产模式 Uvicorn（无 reload、注入随机 SECRET_KEY，端口 8010）：`/api/v1/health`、`/api/v1/teas`、`/api/v1/contents?type=knowledge`（8 条）均 `code=0`；演练库与临时文件已清理
  - 文档同步：[0001_baseline.py](../backend/app/alembic/versions/0001_baseline.py) docstring、[README](../README.md) 已知问题 3 与改进方向
- 内容 4：CI 本地等效实跑（ci.yml 三 job 原命令）
  - **发现并修正格式漂移**：后端 `ruff format --check` 失败（7 文件：0008/0009 迁移 + 5 测试文件）、前端 prettier 失败（19 文件）——历史记录曾声称通过，以本次实跑为准
  - 修复后全绿：`ruff check` ✓ / `ruff format --check`（93 files）✓ / `pytest -q` **170 passed** / `npm run lint` ✓ / `format:check` ✓ / `typecheck` ✓ / `test:run` **45 passed** / `check_all.py` 全部通过
  - **CI 远程触发未完成（C 类待决策）**：远程仓库为 Gitee，`.github/workflows/ci.yml`（GitHub Actions）push 不触发；候选：① 转 Gitee Go 流水线 ② 镜像到 GitHub ③ 维持本地等效，待用户拍板
- 契约 / 数据 / 安全影响：无契约变更、无表结构变更（仅前端交互 + 格式化 + 文档）；冒烟数据清理经用户授权
- 测试证据：见上各内容块；全部实跑
- 遗留问题：
  1. 前端「加入指定清单」UI 缺口（S9 体验闭环，B 类待立项）
  2. CI 远程触发平台待决策（C 类，本条内容 4）
  3. 真实服务器（Linux + Nginx）部署验证仍待实机；Nginx `client_max_body_size 6m` 与 413 复测属部署项
  4. `backend/uploads/` 仍 untracked（既有口径）
- 回滚方式：回退本提交（AppHeader / 格式化 / 文档均为独立可回退改动）

## 2026-11-10｜新功能：登录后顶栏头像 + 个人中心 /profile + 更换头像

- 任务编号 / 分级：TASK-20261110-avatar-profile / **C**（新增 `users.avatar_url` 列 + 2 个新端点 + 契约变更）
- 决策留痕：[ADR-0004](../docs/development/ADR/ADR-0004-user-avatar-profile.md)（方案 C：上传 + 预置双通道）；用户已通过选项确认「新建个人中心页」与「上传 + 预置头像」
- 后端变更：
  - `models/user.py` 增 `avatar_url VARCHAR(255) NULL`；Alembic 迁移 [0010_user_avatar](../backend/app/alembic/versions/0010_user_avatar.py)（已 `upgrade head`）；[init.sql](../database/init.sql) 同步
  - [services/me.py](../backend/app/services/me.py)：`AVATAR_PRESETS` 白名单（`tea-01`～`tea-08`）、`update_by_upload`、`update_by_preset`
  - [routers/me.py](../backend/app/routers/me.py)：新增 `POST /api/v1/me/avatar`（multipart）、`PUT /api/v1/me/avatar`（preset）
  - [repositories/user_repo.py](../backend/app/repositories/user_repo.py)：`update_avatar`、`add_avatar_log`（`operation_logs.action='avatar_update'`）
  - [schemas/auth.py](../backend/app/schemas/auth.py)：`UserResponse` 增 `avatar_url`；新增 `AvatarPresetRequest`（`extra=forbid`）
  - [services/me.py](../backend/app/services/me.py) 修正：非法预置原误用 `ValidationError` 实例当成可调用对象（TypeError），改为 `TeaGuideError(40000, ...)`
- 前端变更：
  - [AppHeader.vue](../frontend/src/components/AppHeader.vue)：登录态改为「圆形头像（或首字母占位）+ 用户名」并链接 `/profile`
  - 新增 [ProfileView.vue](../frontend/src/views/ProfileView.vue)：头像预览、上传（前端预校验类型/5 MB）、8 个预置头像即时切换、等级与统计、我的收藏预览（默认清单前 6 条）、快捷入口
  - [router/index.ts](../frontend/src/router/index.ts)：新增 `/profile`（`requiresAuth`）
  - [api/me.ts](../frontend/src/api/me.ts)、[types/index.ts](../frontend/src/types/index.ts)：`uploadAvatar` / `setPresetAvatar` / `User.avatar_url`
  - 预置头像资产：`frontend/public/avatars/tea-01.svg`～`tea-08.svg`（水墨风自绘）
- 契约 / 数据 / 安全影响：接口 53 → 55；`User` 增 `avatar_url`；新增 SECURITY **S-35**；TEST_PLAN 新增 AVATAR-01～05（84 → 89 条）
- 文档同步：API_CONTRACT v1.6、openapi.yaml 1.6.0、DATA_MODEL v1.5、MODULE_DESIGN、SECURITY v1.3、TEST_PLAN v1.4、docs/api/README、AGENTS 数量口径、`scripts/check_constants.py` 基线
- 测试证据：
  | 项 | 结果 |
  |---|---|
  | `python -m pytest -q`（backend） | **170 passed**（新增 `tests/test_avatar.py` 6 条） |
  | `python -m ruff check app tests` | 通过（顺带修复 0009 迁移与 `schemas/content.py` 的导入排序） |
  | `npm run typecheck` / `npm run lint` | 通过 |
  | `python scripts/check_all.py` | 全部通过（链接 253 / 常量 55·89·35·13 / 五层 / 前台 UI / 记录 / 密钥） |
  | 浏览器实测（localhost:5173） | **PASS**：注册登录 → 顶栏首字母头像 → 点击进 /profile → 选 `tea-01` → `PUT /api/v1/me/avatar` 200 → 顶栏与页面头像同步更新 |
- 过程中修正：
  1. 首次浏览器实测 `PUT /api/v1/me/avatar` 返回 404：后端 reload 未生效（WatchFiles 未捕获改动），重启 `python run.py` 后复测通过
  2. 测试库 `tea_guide_test` 由 `init.sql` 建库、不走 Alembic，补列后 170 条全通过（仅测试库一次性补列，非项目迁移路径）
  3. 浏览器验证注册的临时用户 `avatarcheck01` 已清理（含 `operation_logs` / 清单 / 收藏）
- 遗留问题：
  1. 替换头像后旧文件不即时删除，与茶图共用 `uploads/` 清理技术债（ADR-0004 §7 已登记）
  2. `backend/uploads/` 仍为 untracked；头像上传文件不进 Git
  3. 个人中心仅预览默认清单前 6 条，完整多清单管理仍在 `/my`
- 回滚方式：回退本提交 + `alembic downgrade 0009_seed_content_items_more`

## 2026-11-10｜修复：顶栏「茶文化」下拉切换板块后内容不更新

- 任务编号 / 分级：TASK-20261110-fix-content-switch / B（前端行为修复，无契约变更）
- 问题现象：在「茶叶产地」页点顶栏下拉「茶叶品牌」，地址变为 `/contents/brand`，但页面标题、面包屑、列表内容仍停留在「茶叶产地」
- 根因：五个板块共用同一路由记录 `/contents/:code`（[router/index.ts](../frontend/src/router/index.ts) L44-49），Vue 复用组件实例，`onMounted` 不再触发；[ContentListView.vue](../frontend/src/views/ContentListView.vue) 仅在 `onMounted` 拉数据
- 修复：
  - `ContentListView.vue` 新增 `watch(() => route.params.code)`：重置分页为 1、同步 `headerItem`、重新拉列表（类型未加载时补拉）
  - `ContentDetailView.vue` 同样问题（`/contents/:code/:id` 切换 id 不重载），新增 `watch(() => route.params.id)` → `load()`
- 契约 / 数据 / 安全影响：无
- 测试证据：
  | 项 | 结果 |
  |---|---|
  | `npm run typecheck` | 通过 |
  | `npm run lint` | 通过 |
  | 浏览器实测（Playwright，localhost:5173） | **PASS**：/contents/origin 点「茶叶品牌」→ URL `/contents/brand`、h1「茶叶品牌」、面包屑「首页 › 茶文化 › 茶叶品牌」、产地描述消失、品牌卡片出现 |
- 遗留问题：顶栏「茶文化 ▾」仍为 hover 展开（`cursor: default`），触屏/键盘无法展开；如需点击展开需另立任务
- 回滚方式：回退本提交

## 2026-11-10｜封面落地：39 条内容配图自动下载并回填

- 任务编号 / 分级：TASK-20261110-cover-apply / A（素材落地，无代码/契约变更）
- 需求来源：用户要求「你帮我自动下载」
- 执行方式：临时脚本（`%TEMP%/tea_covers/`，不入库）三段式
  1. Commons API 关键词检索（授权白名单 CC0/PD/CC BY(-SA)，宽 ≥800px）→ 下载
  2. 关键词命中校验（required/blacklist）剔除主题不符结果 → 定向重搜
  3. `POST /admin/upload` 落盘 + `UPDATE content_items.cover_image` 回填
- 结果：**39/39 全部落地**，`content_items` 无空封面；接口与静态文件均 200（示例 143KB jpg）
- 过程中修正的错误匹配（关键词搜索易踩坑，已加校验）：
  | 条目 | 首次错配 | 修正后 |
  |---|---|---|
  | 公道杯 | 1970 年足球赛照片 | Gong fu cha 茶席照 |
  | 大益 | 蛋糕切面照 | 2015 普洱饼茶 |
  | 禅茶一味 | 加州石园 | 京都茶会点茶实拍 |
  | 玻璃茶壶 | 罗马 3 世纪玻璃器 | 港式茶居玻璃壶 |
  | 品茗杯 | 西式带把茶杯+标尺馆藏照 | 明代白釉花口杯（CC0） |
  | 茶则/潮汕/茶马/泡茶用水 | 429 限流失败 | 分类目录+重试取图 |
  | 茶马古道（人工复核） | — | 斯文·赫定 1906 雪山马帮历史照片，题材契合 |
- 契约 / 数据 / 安全影响：无契约变更；`content_items.cover_image` 批量赋值；未触碰 `teas`/`tea_media`
- 文档同步：`docs/product/素材清单.md` §5.4 状态改「已落地」并新增「6. 落地登记表」（39 行：本地 URL / 来源 / 授权 / 作者）+ 3 条偏差说明
- 测试证据：`pytest -q` **164 passed**；`check_all.py` 全部通过
- 遗留问题：
  1. **3 条属品类示意图非本地实景**（蒙顶山用浙江茶园、泡茶用水用科罗拉多山涧、茶马古道用 1906 历史影像），已在文档标注
  2. `backend/uploads/` 仍为 untracked（历史既有口径），图片不进 Git；生产部署需单独同步该目录
  3. CC BY / CC BY-SA 条目上线需保留署名，署名依据见登记表「作者」列
- 回滚方式：`UPDATE content_items SET cover_image=NULL`（图片文件留在 uploads，建议随后清理）

## 2026-11-10｜配图方案：五板块 39 条封面 CC0 实拍方案

- 任务编号 / 分级：TASK-20261110-cover-plan / A（纯文档，无代码变更）
- 需求来源：用户要求生成配图方案；经询问确认：风格 = **CC0 实拍照片**，粒度 = **每条独立封面（39 张）**
- 主要变更：`docs/product/素材清单.md` 新增 §5.4「内容板块封面配图方案」——39 条逐一给出 Wikimedia Commons 主搜索关键词 / 备选关键词 / 画面要求；原「登记规则」顺延 §5.5
- 特别决策：
  - **品牌 7 条**无门店实拍资源：统一以「品类示意 + 产地风貌」配图，不使用含商标店面照片（避免商标侵权），正式上线需门店图须向品牌方申请授权
  - 下载登记流程 6 步：Commons 搜图（筛 CC0/PD）→ 记录文件页 → `POST /admin/upload` 落盘 → 后台填 cover_image → 回表补登三列 → 遵守 §1 品类示意图约束
- 契约 / 数据 / 安全影响：无
- 测试证据：`python scripts/check_all.py` 全部通过（含链接检查）
- 遗留问题：39 张图**待下载落地**（可由用户按方案手动执行，或后续会话脚本化批量下载 + 人工复核授权）
- 回滚方式：删除素材清单 §5.4 节


## 2026-11-10｜内容补全：五板块种子数据扩充至 39 条

- 任务编号 / 分级：TASK-20261110-content-seed-more / A（纯数据补充，无契约/规则变更）
- 需求来源：用户要求「把每一个版块里的内容都补充完整」
- 主要变更：
  - 新增 `backend/app/alembic/versions/0009_seed_content_items_more.py`：五板块新增 30 条原创条目（茶具+6/产地+6/文化+6/品牌+6/知识+6），幂等按 title 去重
  - `database/init.sql` 同步追加同样 30 条（子查询 type_id，与迁移内容一致）
  - 板块覆盖：茶具 8 条（盖碗/紫砂壶/公道杯/品茗杯/建盏/茶则茶匙/玻璃茶壶/朱泥壶）；产地 8 条（西湖/武夷山/西双版纳/安溪/祁门/福鼎/蒙顶山/凤凰山）；文化 8 条（陆羽茶经/宋代点茶/唐代煎茶/明代瀹饮/潮汕工夫茶/茶马古道/禅茶一味/茶与诗词）；品牌 7 条（吴裕泰/张一元/大益/八马/正山堂/品品香/凤牌）；知识 8 条（分类原理/水温投茶/品鉴三步/存茶四原则/醒茶洗茶/春夏秋茶/泡茶用水/五大误区）
- 契约 / 数据 / 安全影响：无契约变更；数据为纯新增种子（content_items 共 39 条）；meta 均符合各板块 JSON Schema 校验
- 测试证据：

  | 命令 | 结果 |
  |---|---|
  | `alembic upgrade head`（开发库） | 0008/0009 应用成功，content_items 总数 39 |
  | `python -m pytest -q` | **164 passed** |
  | `python scripts/check_all.py` | 全部通过 |
  | API 冒烟 `GET /api/v1/contents?type=teaware` / `?type=brand` | total 8 / 7，实时命中 |
- 遗留问题：封面图 cover_image 均为 NULL（待素材到位后后台补录）；品牌 website 仅收录可确认官网（吴裕泰/大益/八马），其余留空
- 回滚方式：`alembic downgrade 0008_seed_content_items`

---

## 1. 写入规则

1. **每个开发任务交付前追加一条**，无论大小（A/B/C 类都要），A 类可精简为 4 行。
2. **只写真实执行结果**：命令、通过/失败/跳过数量必须与实际一致；未运行的测试写「未运行」，**禁止写"已通过"**。
3. 接口、数据库、安全变更必须在条目中显式写出**已同步的文档与迁移文件**；没有同步不得标记验收通过。
4. 重要技术决策同时产出 [ADR](../docs/development/ADR/README.md)，build-log 只留一行引用，不重复论证过程；C 类决策的 ADR 必须在编码前完成"提议"版本。
5. 不记录密码、Cookie 值、密钥、完整堆栈、`.env` 内容。
6. 遗留问题必须可执行（写清"谁在什么条件下补什么"），不写"后续优化"这类空话。

## 2. 条目模板（复制使用）

```markdown
## YYYY-MM-DD｜<任务名>

- 任务编号 / 分级：TASK-YYYYMMDD-xx / A / B / C（C 类注明"用户确认于 <日期/方式>"）
- 需求来源：<PRD §x / API 端点 / S-xx / 用例 ID / PAGE_SPECS>
- 主要变更：
  - `<文件>`：<要点>
  - `<文件>`：<要点>
- 契约 / 数据 / 安全影响：无 / <端点、字段、表、S 项变更 + 已同步文档与迁移文件>
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `cd backend; pytest -q -k "AUTH-01"` | AUTH-01 | 1 passed | —— |
  | `npm run test:run -- src/utils/filter.spec.ts` | 前端筛选 | 未运行 | 本节无前端改动 |

- 验收结论：通过 / 有条件通过（写明遗留）/ 不通过
- 基线例外：<本次触及的 AGENTS §3.1 遗留 / 无>
- 遗留问题：
- 回滚方式：
- 关联 ADR：<ADR-XXXX / 无>
```

## 3. 问题复发台账

同一类错误**出现第二次**时，必须登记到下表，并落实至少一项防护：
补自动化测试（标注 TEST_PLAN 用例 ID）、补校验规则、补规范条款或补检查脚本。
连续出现三次仍无防护，视为流程缺陷，需按 C 类提出流程修订。

| 编号 | 现象 | 首次 / 再次出现 | 根因 | 已落实的防护 | 状态 |
|---|---|---|---|---|---|
| R-01 | 篡改 Cookie 末位仅把 `A` 换 `B`，服务端仍接受，测试误判为通过/失败 | 2026-11-08（首次） | base64url 签名末位含未参与解码的低位，同高位字符互换后字节相同 | AUTH-07 改为翻转 base64url 索引高位（`index ^ 32`），断言仍为 401/40100，未放宽 | 已关闭 |

---

## 4. 记录

## 2026-11-10｜批次五：R1–R5 五大内容板块

- 任务编号 / 分级：TASK-20261110-batch5 / C（2 张新表 + 7 新端点 + 2 新前端页 + 3 新后台页；用户确认于 2026-11-10；本批不提交 Git）
- 需求来源：批次五 R1–R5 延后任务；[PLAN_剩余功能.md](../docs/development/plans/PLAN_剩余功能.md) §6
- 主要变更：
  - `backend/app/alembic/versions/0007_content_platform.py`（新）：建 `content_types`（5 板块种子）+ `content_items`（FK→CASCADE；meta JSON 承载各板块特有字段）
  - `backend/app/models/content.py`（新）：`ContentType` + `ContentItem` 两个 ORM；`models/__init__.py` 追加导出
  - `backend/app/schemas/content.py`（新）：`ContentTypeOut`、`ContentItemOut`、`ContentListResponse`、`ContentCreateRequest`（extra=forbid + 板块差异化 meta 校验）、`ContentUpdateRequest`、后台列表 DTO
  - `backend/app/repositories/content_repo.py`（新）：前台查询自动过滤 `is_active=0`；后台含下架；只 flush 不 commit
  - `backend/app/services/contents.py`（新）：CRUD + meta JSON 校验 + 软失效 + operation_logs 留痕
  - `backend/app/routers/contents.py`（新，前台 3 端点）+ `routers/admin.py` 扩展（后台 4 端点）
  - `backend/app/core/response.py`：新增 `ContentTypeNotFound=40450`、`ContentItemNotFound=40460`
  - `frontend/src/types/index.ts`（追加）：ContentType/ContentItem/AdminContentListItem/...
  - `frontend/src/api/contents.ts`（新，3 前台）+ `api/admin.ts`（追加 4 后台）
  - `frontend/src/views/ContentListView.vue`、`views/ContentDetailView.vue`（新，自研，前台禁用 Element Plus）
  - `frontend/src/views/admin/AdminContents.vue`、`views/admin/AdminContentEdit.vue`（新，Element Plus）
  - `frontend/src/components/AppHeader.vue`（导航追加「茶文化 ▾」自研下拉）
  - `frontend/src/router/index.ts`（追加前台 `/contents/:code`、`/contents/:code/:id` + admin 三路由）
  - `frontend/src/views/admin/AdminLayout.vue`（侧边栏追加「内容管理」菜单）
- 契约 / 数据影响：
  - 新增 7 端点：前台 `GET /content-types`、`GET /contents?type=&page=&page_size=`、`GET /contents/{id}` + 后台 `GET/POST/PUT/DELETE /admin/contents(*)`（业务端点 46 → 53）
  - 新表 `content_types` + `content_items`（11 → 13 张表）
  - meta JSON 各板块字段约定：teaware→material/volume/category、origin→province/region、culture→era/tags、brand→founded/brand_origin/website、knowledge→subtype/difficulty
  - 新错误码：40450（板块不存在）、40460（条目不存在）
  - 已同步 `database/init.sql`（两张表 DDL + 种子）、`docs/api/openapi.yaml`（7 端点 + 9 个 schema）、`docs/api/README.md`（端点数）、`AGENTS.md`（表数+端点数）、`scripts/check_constants.py`（EXPECTED + claims）
  - 迁移 `0007_content_platform` 已在 `tea_guide` 与 `tea_guide_test` 双库执行
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `cd backend; python -m ruff check app` | Ruff | All checks passed | 批次五新增/修改文件 |
  | `cd backend; python -m ruff format --check app` | Ruff format | 通过 | 批次五新增/修改文件 + 2 批次遗留一起修复 |
  | `cd backend; python -m pytest -q` | 后端全量 | 153 passed | 回归零破坏 |
  | `cd backend; python -m pytest tests/test_content_smoke.py -q` | 批次五冒烟 | 5 passed | CONT-01~05：list_types/list_contents/invalid_type/not_found/admin_auth |
  | `cd frontend; npm run lint` | ESLint | 0 errors, 0 warnings | —— |
  | `cd frontend; npm run typecheck` | vue-tsc | 通过 | —— |
  | `cd frontend; npm run test:run` | Vitest | 45 passed | 纯函数用例，未新增 |
  | `cd frontend; npm run build` | Vite 生产构建 | 通过 | ContentDetailView + AdminContentEdit 正确拆分 |
  | `python scripts/check_all.py` | 链接/常量/分层/前端/记录/密钥 | 全部 OK | 常量 53/84/34/13 |

- 验收结论：通过 —— 代码、静态检查、后端 158 条（153 回归 + 5 冒烟）、前端 lint/typecheck/test/build 全部通过；批次五 R1–R5 功能完整落地
- 基线例外：无新违规
- 遗留问题：
  - `AdminContentEdit` 编辑模式暂未实现详情回填（后端未加 `GET /admin/contents/{id}` 端点）；新增功能完整可用，编辑需手动在 PUT 请求体传完整字段
  - 批次五种子数据仅有 5 板块分类，无示例内容条目（用户可通过后台 AdminContents 录入）
  - batch5 测试仅 5 条冒烟，需后续补全 CONT-06（meta JSON 校验非法结构 → 400）与 CRUD 全链路（Service 层覆盖）
  - 批次五改动未提交 Git（留在工作区等用户指令）
- 回滚方式：`alembic downgrade 0006_contributions` + 回退上述文件

## 2026-11-10｜批次五完善：回填端点 + 测试补齐 + 种子数据 + utcnow 技术债

- 任务编号 / 分级：TASK-20261110-batch5-fix / B（后端 1 新端点 + Schema 调整，前端 1 API + 回填逻辑，测试 +6 条，种子数据迁移 + init.sql，技术债 8 处）
- 需求来源：批次五 build-log 遗留 5 项 + utcnow DeprecationWarning
- 主要变更：
  - **后端** `routers/admin.py` 新增 `GET /admin/contents/{item_id}` —— 后台详情（含下架条目，is_active 返回给编辑回填）
  - **后端** `services/contents.py` 新增 `admin_get_content()` + `_to_admin_out()`（含 is_active）；`ContentCreateRequest.validate_meta_for_type` 从 Service 手动调用改为 `@model_validator(mode="after")` 自动执行，ValueError → ValidationError → 422 → 400
  - **后端** `schemas/content.py`：`ContentItemOut.type_code` 设默认空串（非 ORM 列）；`ContentItemOut.is_active` 改为 Optional；所有 meta 校验异常经 Pydantic 自动重映射
  - **后端** 8 处 `datetime.utcnow()` → `datetime.now(timezone.utc)` —— `services/{contributions,upload,auth}.py` + `repositories/{list_repo,share_repo,tea_repo}.py`
  - **前端** `api/admin.ts` 新增 `getAdminContent(id)`
  - **前端** `views/admin/AdminContentEdit.vue`：编辑模式回填实现 —— 加载详情 → 表单填值 → meta JSON → 各板块 ref 对象还原
  - **前端** `types/index.ts`：`ContentItem.is_active` 新增 Optional
  - **数据库** `alembic/versions/0008_seed_content_items.py`（新）：5 板块各 1–2 条示例条目，upsert（按 title 去重）
  - **数据库** `database/init.sql`：追加 content_items 9 条种子数据（子查询 type_id）
  - **测试** `tests/test_content_smoke.py` 5 → 11 条 —— CONT-06 meta 结构校验（extra字段/tags非list/枚举超范围/URL格式/非法type_code → 400）、CONT-07 CRUD 全链路（创建→详情→更新软删→前台不可见）、CONT-08 软删恢复、CONT-09 后台详情 not found、CONT-10 板块筛选、CONT-11 operation_log 写入
  - **修复** `ContentCreateRequest` 的 meta 校验从 Service 层手动调用改为 Pydantic model_validator，异常自动走 FastAPI 重映射
- 契约 / 数据 / 安全影响：
  - 契约新增 `GET /admin/contents/{id}`（后台专用，游客 401）；`ContentItemOut` 新增可选 `is_active`（前台详情不含，不破坏既有）
  - 种子数据迁移 0008 幂等（按 title 去重）；init.sql 追加同样的 9 条示例
  - 安全：`model_validator` 改造后 meta 校验异常自动返回 400（之前可能漏校验被 Service 层手动调但异常不被捕获）
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `python -m pytest -q` | 后端全量 | **164 passed**（158 → +6） | DeprecationWarning 从 868 降至 779（少 89 条 utcnow 警告） |
  | `python -m pytest tests/test_content_smoke.py -v` | 批次五扩展 | **11 passed**（5 → +6） | CONT-06~11 |
  | `npm run typecheck` | 前端 | 通过 | ContentItem.is_active 新增 Optional |
  | `python scripts/check_all.py` | 全量静态 | **全部通过** | 242 links / 常量一致 / 五层检查 / 前台 UI / records / secrets |
- 遗留问题：
  - `ContentUpdateRequest` 的 meta 校验仍是 Service 层手动调 `_validate_meta`（PUT 时 title/type_code 不可改，meta 字段可能与板块不匹配 → 暂接受 PUT 时用户必须知板块）
  - SQLAlchemy 底层 `_ColumnDefault` 还有 2 条 utcnow DeprecationWarning（orm `default=func.utc_timestamp()`，来自 Alembic 框架内部），暂无法修复
  - 种子数据仅 9 条，前台展示可能偏少（可在后台继续录入）
- 回滚方式：`alembic downgrade 0007_content_platform` + 回退上述文件

## 2026-11-09｜批次四：S10–S13 用户贡献 + 管理员审核

- 任务编号 / 分级：TASK-20261109-batch4 / C（2 张新表 + 迁移 + 契约变更；用户确认于 2026-11-09 的 PLAN_剩余功能，本批不提交 Git）
- 需求来源：PRD S10–S13；[PLAN_剩余功能.md](../docs/development/plans/PLAN_剩余功能.md) §5
- 主要变更：
  - `backend/app/models/contribution.py`（新）：`Contribution`（type/payload JSON/三态/审核人/拒绝理由）+ `TeaNameCategoryMap`
  - `backend/app/alembic/versions/0006_contributions.py`（新）：建 `tea_name_category_map`（种子 22 条名品映射）+ `contributions`（FK×3、2 个复合索引）
  - `backend/app/schemas/contribution.py`（新）：`ContributionTeaPayload`（extra=forbid）、按 type 二选一校验、article 3–500 字、拒绝理由 1–200 字
  - `backend/app/repositories/contribution_repo.py`（新）：创建/我的列表/管理队列/已通过科普聚合/映射与名称查询；只 flush 不 commit
  - `backend/app/services/contributions.py`（新）：双层校验（映射表茶类一致性 + 名称相似度 >90% 拦截）、提交/删除规则、审核通过创建上架茶品+可选 tips、拒绝留理由、写 operation_logs
  - `backend/app/routers/contributions.py`（新，3 端点）+ `routers/admin.py` 扩展（审核队列/通过/拒绝 3 端点）+ `core/response.py`（`ContributionNotFound=40440`）
  - `backend/app/services/teas.py` + `schemas/tea.py`：`TeaDetail` 新增 `contributed_articles`（仅 approved 科普，倒序）
  - `frontend/src/types/index.ts` + `api/contributions.ts`（新）+ `api/admin.ts` 扩展
  - `frontend/src/views/ContributeView.vue`（投稿页：补充新茶 / 投稿科普双 Tab）、`views/MyContributionsView.vue`（我的提交：状态/理由/删除）、`views/admin/AdminContributions.vue`（Element Plus 审核后台：队列/详情/通过/预设理由拒绝）
  - `frontend/src/router/index.ts`（`/contribute`、`/my/contributions`、`/admin/contributions`）、`views/MyListView.vue`（投稿入口）、`views/TeaDetailView.vue`（茶友科普区 + 投稿入口）、`views/admin/AdminLayout.vue`（审核菜单）
- 契约 / 数据 / 安全影响：
  - 新增 6 个端点：`POST/GET(mine)/DELETE /contributions*` + `GET /admin/contributions`、`POST .../approve`、`POST .../reject`（业务端点 40 → 46）
  - 新表 `contributions`、`tea_name_category_map`（9 → 11 张表）；`TeaDetail` 增 `contributed_articles`；新错误码 `40440`
  - SECURITY 新增 S-34（贡献与审核门禁）；仅 pending 可删除/审核；审核仅管理员；payload 服务端组装防伪造
  - 已同步 `docs/api/API_CONTRACT.md` v1.5、`docs/api/openapi.yaml` 1.5.0、`docs/architecture/DATA_MODEL.md` v1.4、`database/init.sql`、`docs/testing/TEST_PLAN.md` v1.3（CONTRIB-01–08）、`docs/architecture/SECURITY.md` v1.2、`AGENTS.md`、`docs/api/README.md`、`scripts/check_constants.py`
  - 迁移 `0006_contributions` 已在 `tea_guide` 与 `tea_guide_test` 双库执行
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `cd backend; python -m ruff check app tests` | Ruff | All checks passed | —— |
  | `cd backend; python -m pytest -q` | 后端全量 | 153 passed | 含 `tests/test_contributions.py` 新增 8 条（映射校验/查重/越权/审核流转/详情聚合/权限） |
  | `cd frontend; npm run lint` | ESLint | 通过 | —— |
  | `cd frontend; npm run typecheck` | vue-tsc | 通过 | —— |
  | `cd frontend; npm run test:run` | Vitest | 45 passed | 纯函数用例，未新增 |
  | `cd frontend; npm run build` | Vite 生产构建 | 通过 | —— |
  | `python scripts/check_all.py` | 链接/常量/分层/前端/记录/密钥 | 全部 OK | 常量 46/84/34/11 |
  | 浏览器投稿/审核冒烟 | 投稿→审核→详情展示 | 未运行 | 无浏览器自动化；需人工确认 |

- 验收结论：有条件通过 —— 代码、静态检查、后端 153 条与前端 45 条测试全部通过；投稿/审核链路未手工浏览器验证
- 基线例外：无
- 遗留问题：S10–S13 需人工在浏览器执行「投稿新茶 → 管理员通过 → 前台可见」与「投稿科普 → 通过 → 详情页展示」确认（责任人：用户；条件：前后端 dev server + 管理员账号）
- 回滚方式：`alembic downgrade 0005_multi_lists` + 回退上述文件
- 关联 ADR：无（贡献审核决策见 PLAN_剩余功能 §5 与 SECURITY S-34）

## 2026-11-09｜批次三：S9 多收藏清单

- 任务编号 / 分级：TASK-20261109-batch3 / C（表结构 + 迁移 + 契约变更；用户确认于 2026-11-09：删除清单时条目迁移到默认清单、不丢数据；本批不提交 Git）
- 需求来源：PRD S9；[PLAN_剩余功能.md](../docs/development/plans/PLAN_剩余功能.md) §4
- 主要变更：
  - `backend/app/models/collection_list.py`：新增 `is_default`，`UNIQUE(user_id, is_default)`（默认行 1、普通行 NULL）+ `idx_list_user`
  - `backend/app/models/favorite.py`：`favorite_items` 新增 `list_id`；唯一键改 `UNIQUE(list_id, tea_id)`；索引 `idx_favorite_list_created`
  - `backend/app/alembic/versions/0005_multi_lists.py`（新）：历史数据回填（全置默认 → 为缺失用户补建默认清单 → 回填 `list_id` → 切换唯一键）
  - `backend/app/repositories/list_repo.py`（重写）、`favorite_repo.py`：多清单查询、跨清单去重统计、清单归属锁
  - `backend/app/services/lists.py`（重写）：默认清单惰性创建（并发重试）、10 个上限、删除迁移合并、笔记读写
  - `backend/app/services/favorites.py`、`services/shares.py`：`list_id` 归属、锁序「清单 → 茶品」、跨清单 `favorite_count` 去重、分享按清单独立
  - `backend/app/routers/lists.py`（6 端点）、`routers/favorites.py`、`routers/shares.py`、`core/response.py`（`ListNotFound=40420`）、`schemas/list.py`/`favorite.py`/`share.py`
  - `backend/tests/test_lists.py`（重写 16 条）、`test_favorites.py`/`test_shares.py`/`test_g5_system.py`/`test_admin.py`/`test_batch1_features.py`/`test_batch2_features.py`：路径与断言迁移
  - `frontend/src/types/index.ts`、`api/lists.ts`/`favorites.ts`/`shares.ts`、`views/MyListView.vue`（清单侧栏 + 条目区）、`components/NoteEditor.vue`/`SharePanel.vue`
- 契约 / 数据 / 安全影响：
  - 新增 `POST /lists`、`GET /lists/{list_id}`、`DELETE /lists/{list_id}`；清单端点由 3 个增至 6 个（业务端点 37 → 40）
  - `POST /favorites/{tea_id}` 请求体可选 `list_id`；`DELETE` 可选 `list_id` 查询参数；`FavoriteState` 新增 `list_ids`
  - `POST /shares/generate` 请求体可选 `list_id`；新增错误码 `40420`
  - 已同步 `docs/api/API_CONTRACT.md` v1.4、`docs/api/openapi.yaml` 1.4.0、`docs/architecture/DATA_MODEL.md` v1.3、`database/init.sql`、`docs/testing/TEST_PLAN.md` v1.2（MLIST-01–06）、`AGENTS.md`、`docs/api/README.md`、`scripts/check_constants.py`
  - 迁移 `0005_multi_lists` 已在 `tea_guide` 与 `tea_guide_test` 双库执行；9 张表不变
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `cd backend; python -m ruff check app tests` | Ruff | All checks passed | —— |
  | `cd backend; python -m pytest -q` | 后端全量 | 145 passed | 含多清单 16 条与 FAV-09 |
  | `cd frontend; npm run lint` | ESLint | 通过 | —— |
  | `cd frontend; npm run typecheck` | vue-tsc | 通过 | —— |
  | `cd frontend; npm run test:run` | Vitest | 45 passed | 纯函数用例，未新增 |
  | `cd frontend; npm run build` | Vite 生产构建 | 通过 | —— |
  | `python scripts/check_all.py` | 链接/常量/分层/前端/记录/密钥 | 全部 OK | 常量 40/76/33/9 |
  | 浏览器多清单冒烟 | 新建/改名/删除/迁移/笔记/分享 | 未运行 | 无浏览器自动化；需人工确认侧栏与迁移提示 |

- 验收结论：有条件通过 —— 代码、静态检查、后端 145 条与前端 45 条测试全部通过；多清单浏览器交互未手工验证
- 基线例外：无
- 遗留问题：S9 需人工在浏览器执行一次「新建清单 → 加入茶 → 删除清单」确认迁移与提示（责任人：用户；条件：前端 dev server + 已登录账号）
- 回滚方式：`alembic downgrade 0004_login_attempts` + 回退上述文件
- 关联 ADR：无（多清单决策见 DATA_MODEL §6 与 PLAN_剩余功能 §4）

## 2026-11-09｜批次二：S14 登录锁定 / S15 用户等级 / S16 个性化推荐 / S8 分享海报

- 任务编号 / 分级：TASK-20261109-batch2 / C（新表 + 登录安全规则；用户确认于 2026-11-09：锁定按「用户名 + IP」双维度、等级 4 档、允许引入前端 `qrcode` 依赖、本批不提交 Git）
- 需求来源：PRD S14/S15/S16/S8；[PLAN_剩余功能.md](../docs/development/plans/PLAN_剩余功能.md) §3
- 主要变更：
  - `backend/app/models/login_attempt.py`（新）、`models/__init__.py`：`login_attempts` ORM
  - `backend/app/alembic/versions/0004_login_attempts.py`（新）：建表 + 双维度索引
  - `backend/app/repositories/login_attempt_repo.py`（新）；`favorite_repo.py` 增收藏/笔记/茶类分布聚合；`share_repo.py` 增生效分享数
  - `backend/app/core/config.py`：`LOGIN_MAX_FAILURES` / `LOGIN_WINDOW_MINUTES` / `LOGIN_ATTEMPT_RETENTION_HOURS`
  - `backend/app/core/response.py`：`TooManyLoginAttempts(42900)`
  - `backend/app/services/auth.py`：锁定判定先于账号校验；失败记录 + 24h 清理；成功登录清空用户名记录
  - `backend/app/routers/auth.py`：登录传入 `request.client.host`
  - `backend/app/schemas/stats.py`、`services/stats.py`、`routers/me.py`（新）：`GET /me/stats` 与四档等级纯函数
  - `backend/app/services/teas.py`、`routers/teas.py`、`repositories/tea_repo.py`：`GET /teas/recommended`（偏好加权 + 排除已收藏 + 随机兜底）
  - `backend/tests/conftest.py`：每用例清空 `login_attempts`（TestClient IP 固定为 testclient，避免跨用例误锁）
  - `backend/tests/test_batch2_features.py`（新，10 条）；`backend/tests/test_g5_system.py`：AUTH-05 两段失败之间清空记录，避免与 S14 锁定交叉
  - `frontend/src/types/index.ts`、`api/me.ts`（新）、`api/teas.ts`：类型与接口
  - `frontend/src/views/HomeView.vue`：登录后随机发现改为「为你推荐」（推荐 id → 详情）
  - `frontend/src/views/MyListView.vue`：等级徽章与升级差距
  - `frontend/src/utils/poster.ts`（新）+ `poster.spec.ts`（新）；`components/SharePanel.vue`、`views/ShareView.vue`：canvas 海报 + 二维码下载
  - `frontend/package.json`：新增 `qrcode` / `@types/qrcode`（纯前端，动态 `import()`，仅海报功能加载）
- 契约 / 数据 / 安全影响：
  - 新增 `GET /teas/recommended`、`GET /me/stats`；`POST /auth/login` 新增 `42900` / HTTP 429
  - 新表 `login_attempts`；已同步 `docs/api/API_CONTRACT.md` v1.3、`docs/api/openapi.yaml` 1.3.0、`docs/architecture/DATA_MODEL.md` v1.2、`database/init.sql`、`docs/architecture/SECURITY.md` v1.1（S-33）、`docs/testing/TEST_PLAN.md` v1.1、`docs/product/PRD.md`（FR-4.4 / S14 / S15）
  - 迁移 `0004_login_attempts` 已在 `tea_guide` 与 `tea_guide_test` 双库执行
  - 安全项：新增 S-33；登录仍统一 40110，不泄露账号存在性；不记录密码明文
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `cd backend; python -m ruff check app tests` | Ruff | All checks passed | —— |
  | `cd backend; python -m pytest -q` | 后端全量 | 139 passed | 含批次二新增 10 条 |
  | `cd frontend; npm run lint` | ESLint | 通过 | —— |
  | `cd frontend; npm run typecheck` | vue-tsc | 通过 | —— |
  | `cd frontend; npm run test:run` | Vitest | 45 passed（6 文件） | 含 `poster.spec.ts` 7 条 |
  | `cd frontend; npm run build` | Vite 生产构建 | 通过 | `qrcode` 为独立异步 chunk |
  | 浏览器海报冒烟 | S8 生成/下载/扫码 | 未运行 | 无浏览器自动化；需人工点击「下载分享海报」确认 PNG 与二维码可扫 |

- 验收结论：有条件通过 —— 代码、后端/前端静态检查与单测全部通过；S8 的真实浏览器下载与二维码扫描未验证
- 基线例外：无
- 遗留问题：S8 需人工在浏览器执行一次「下载分享海报」并扫码确认（责任人：用户；条件：前端 dev server 打开任一分享清单）
- 回滚方式：`alembic downgrade 0003_batch1_filters` + 移除 `qrcode`/`@types/qrcode` + 回退上述文件
- 关联 ADR：无（规则细节已在 PLAN_剩余功能 与 S-33 中记录）

## 2026-11-09｜批次一：S1/S2/S3/S6/S7/S17（筛选扩展 / 对比 / 相关推荐 / 小贴士 / 热度）

- 任务编号 / 分级：TASK-20261109-batch1 / B（新增查询参数与两个只读端点，未破坏既有契约；表结构变更经用户确认按批次一方案执行）
- 需求来源：PRD S1/S2/S3/S6/S7/S17；`docs/development/plans/PLAN_剩余功能.md`
- 主要变更：
  - `backend/app/models/tea.py`：`Tea` 增 `price_min/price_max`；`TeaTips` 增 `created_at/updated_at`
  - `backend/app/alembic/versions/0003_batch1_filters.py`：新增价格列、小贴士时间戳、`idx_favorite_created_tea` 索引，并从 `price_range` 回填价格
  - `backend/app/schemas/tea.py`：`TeaDetail` 增价格字段、`TeaBaseRequest` 价格校验、新增 `LatestTipItem`
  - `backend/app/repositories/tea_repo.py`：列表支持发酵/价格/`filter_mode`；`list_hot` 改 7 天加权；新增 `list_related`、`list_latest_tips`
  - `backend/app/services/teas.py`、`backend/app/routers/teas.py`、`backend/app/routers/tips.py`、`backend/app/main.py`：相关推荐与最新小贴士端点
  - `frontend/src/types/index.ts`、`api/teas.ts`、`utils/teaQuery.ts`、`utils/compare.ts`（新）：类型、接口、筛选纯函数、对比矩阵
  - `frontend/src/views/TeaListView.vue`（发酵/价格/组合方式 UI）、`TeaDetailView.vue`（相关推荐改新接口）、`HomeView.vue`（小贴士区块）、`CompareView.vue`（新）、`router/index.ts`（/compare）
  - `database/init.sql`：同步价格字段、小贴士时间戳、索引
- 契约 / 数据 / 安全影响：
  - 新增端点 `GET /teas/{tea_id}/related`、`GET /tips/latest`；列表新增 `fermentation/price_min/price_max/filter_mode` 查询参数；`TeaDetail` 新增 `price_min/price_max`
  - 已同步 `docs/api/API_CONTRACT.md`（§2.3、§4.2.1、§4.2.4、新增 §4.2.8/§4.2.9）、`docs/api/openapi.yaml`、`docs/architecture/DATA_MODEL.md`
  - 迁移：`0003_batch1_filters`（已在 `tea_guide` 与 `tea_guide_test` 双库执行）
  - 安全项：无放宽；新增端点均为游客只读
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `cd backend; python -m pytest -q` | 后端全量 | 119 passed + 批次一新增 10 passed | 迁移后执行 |
  | `cd frontend; npm run lint` | ESLint | 通过 | —— |
  | `cd frontend; npm run typecheck` | vue-tsc | 通过 | —— |
  | `cd frontend; npm run test:run` | Vitest | 通过（含 teaQuery 19 + compare 3） | —— |
  | `cd frontend; npm run build` | Vite 生产构建 | 通过 | —— |

- 验收结论：通过
- 基线例外：无
- 遗留问题：无（S3 对比页每类各取 1 款代表茶，未做任意多茶对比，符合 MVP 范围）
- 回滚方式：`alembic downgrade 0002_content_expansion` + 回退对应前后端文件
- 关联 ADR：无

## 2026-11-09｜批量录入 30 款茶（六大茶类各 5 款）+ CC0 配图

- 任务卡 / 分级：B（新增业务数据，不改端点/契约/表结构）
- 需求来源：用户要求"多加一些茶"，从原 6 款扩展至 36 款
- 主要变更：
  - 通过 `POST /admin/teas` 录入 30 款茶（id 7–36），六大茶类各 5 款
  - 文字数据：茶名/产地/季节/发酵度/价格/代表品种/外形/汤色/香气/滋味/水温/投茶量/冲泡时间 + 4 项小贴士，参考公开茶知识改写，未直接复制第三方站点原文
  - 配图：每款 1 张主图 + 1 张图集，均来自 Wikimedia Commons CC0 / Public domain；部分茶未搜到专用图，用品类通用图或同品类已有图兜底
  - 修复：霍山黄芽主图曾误配玫瑰花，已替换为黄茶品类图
- 茶品清单（每类 5 款）：
  - 绿：碧螺春、黄山毛峰、信阳毛尖、六安瓜片、庐山云雾
  - 白：白牡丹、寿眉、贡眉、月光白、新工艺白茶
  - 黄：蒙顶黄芽、霍山黄芽、远安鹿苑、平阳黄汤、海马宫茶
  - 乌龙：铁观音、凤凰单丛、冻顶乌龙、武夷肉桂、武夷水仙
  - 红：祁门红茶、滇红、九曲红梅、宜红、川红
  - 黑：安化黑茶、六堡茶、千两茶、茯砖茶、康砖茶
- 契约 / 数据 / 安全影响：仅新增数据行，无代码/契约/表结构变更
- 测试证据：

  | 命令 | 范围 | 结果 |
  |---|---|---|
  | `GET /teas?page_size=100` | 茶品总数 | 36 款，六大茶类各 6 款 |
  | 36 款茶详情接口 | 主图+图集 | 全部 main_image_url 非空、image_set ≥ 1 |
  | `python -m pytest -q` | 后端全量 | **119 passed**（零回归） |

- 验收结论：通过
- 遗留问题：
  - 图片均为 CC0 品类示意图，非具体茶品实拍；正式上线前建议替换自有实拍
  - 部分茶复用了同品类图片，可能出现重复；仅作演示
  - 未做浏览器端对全部 36 款的逐一点验（已验首页与详情页基本功能）
- 回滚方式：`DELETE /admin/teas/{id}` 逐款删除，或直接清库重置种子数据
- 关联文档：[素材清单.md §5.3](../docs/product/素材清单.md)

## 2026-11-09｜文档与常量同步收口（X-02~08 遗留）

- 任务卡 / 分级：A（纯文档/常量同步，不改代码行为）
- 需求来源：`check_all.py` 全量检查暴露的契约与记录不同步问题
- 主要变更：
  - `docs/api/openapi.yaml`：v1.0.0 → v1.2.0；新增 `GET /teas/{tea_id}/images`、`POST /admin/media/video`、`POST/DELETE /admin/teas/{tea_id}/images[/{image_id}]` 共 4 个端点；`TeaDetail` 增 `video_url`/`video_duration`/`image_set`；新增 `TeaMediaItem`/`TeaMediaCreateRequest`/`VideoUploadResult`/`DeletedEnvelope` 等 schema
  - `AGENTS.md`：§6 表数 7→8（增 `tea_media`）、§7 端点数 29→33（teas 7 / admin 11）、§3.1 同步
  - `docs/api/README.md`：端点数 29→33
  - `scripts/check_constants.py`：`openapi_operations` 29→33、`database_tables` 7→8，口径声明同步
  - `docs/development/ADR/ADR-0003-content-expansion.md`：修正 5 个相对链接路径（少一级 `../`）
  - `docs/development/ADR/README.md`：索引补 ADR-0003
  - `docs/development/PLANS_扩展.md`：X-07 状态更新为已落地
  - `harness/build-log.md`：X-01/02~08/07 三条目移至记录区顶部，恢复日期倒序
- 契约 / 数据 / 安全影响：仅文档与常量对齐，无运行时行为变更
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `python scripts/check_all.py` | 全量静态检查 | **全部通过** | links/constants/layers/frontend/records/secrets 均 OK |
  | `python -m pytest -q` | 后端全量 | **119 passed**（18.90s） | 数据/文档变更零回归 |
  | `npm run build` | 前端生产构建 | 通过（1.53s） | 仅既有 chunk >500kB 警告 |
  | `python -c "yaml.safe_load(openapi.yaml)"` | OpenAPI 语法 | OK | YAML 可解析 |

- 验收结论：通过
- 遗留问题：见本条目之前的 X-07 条目（浏览器手工冒烟、君山银针/大红袍图集仅 1 张、git 未提交）
- 回滚方式：revert 上述文档/常量改动即可
- 关联 ADR：[ADR-0003](../docs/development/ADR/ADR-0003-content-expansion.md)

## 2026-11-09｜X-01 内容扩展：Alembic 基线接管 + S4/S5 表结构迁移

- 任务卡 / 分级：C（表结构变更；ADR-0003 已于 2026-11-09 经用户确认「全部按推荐方案执行」后采纳）
- 需求来源：内容扩展提案（PRD_扩展提案.md），本期范围 = 方案二（S4 图片集 + S5 视频 + R7 首页背景 + R8 素材）
- 主要变更：
  - `backend/app/alembic/versions/0001_baseline.py`：空操作基线迁移（基线结构由 `database/init.sql` 建立；已建库环境 `alembic stamp 0001_baseline`）——Alembic 正式接管版本链（此前 versions/ 为空，MVP 全靠 init.sql）
  - `backend/app/alembic/versions/0002_content_expansion.py`：`teas` 增 `video_url VARCHAR(500) NULL` / `video_duration INT UNSIGNED NULL`；新建 `tea_media` 表（FK→teas ON DELETE CASCADE，idx(tea_id, sort_order)）
  - `backend/app/models/tea.py`：Tea 增两列映射 + `media_images` relationship；新增 `TeaMedia` 模型；`models/__init__.py` 导出
  - `database/init.sql`：同步新列与 tea_media 建表语句（保持从零建库可用）
  - `docs/architecture/DATA_MODEL.md` v1.0→v1.1：§2 表清单第 8 行、§3 ER 图、§4.2 新列、§4.3.1 tea_media 小节、§10 S4/S5 标记已落地
  - `backend/alembic.ini`：中文注释改英文（修复 Windows GBK locale 下 configparser 解码失败；该文件此前从未实际运行所以未暴露）
  - 提案文档确认状态同步：ADR-0003 转「已采纳」，PRD_扩展提案 Q1–Q5、PLANS_扩展 前置清单全部标记已确认
- 契约 / 数据 / 安全影响：表结构变更（本次）；API 契约暂未变（TeaDetail 增字段属 X-04a）；无安全项变更
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `alembic stamp 0001_baseline && upgrade head` | tea_guide（开发库） | 通过 | current = 0002_content_expansion (head) |
  | stamp → upgrade → downgrade → upgrade 循环 | tea_guide_test（测试库） | 通过 | 升降级可重放，最终 current = head |
  | SHOW COLUMNS / SHOW INDEX 结构断言 | 两库 | 通过 | teas 两新列 NULL 许可正确；tea_media 5 列 + PK + idx_tea_media_tea 正确 |
  | `python -m pytest -q` | 后端全量 | **106 passed**（18.69s） | schema 变更对现有功能零破坏 |
  | `ruff check app tests` / `ruff format --check app` | 后端静态 | 通过 | 初次 format 有 1 文件待整理，已修复复检通过 |

- 验收结论：通过（X-01a/X-01b 出口标准全部满足）
- 遗留问题：
  - 首次执行 0002 时因 `op.create_table` 误用裸 kwargs（engine/charset）失败，teas 两列已落库但 tea_media 未建；已手工回滚中间态两列后重放成功。教训：方言参数必须用 `mysql_` 前缀；已修正迁移文件。
  - 前端 `types/index.ts` 的 TeaDetail 类型暂未加 video 字段——属 X-04a 范围，届时同步。
- 回滚方式：`alembic downgrade 0001_baseline`（两库均已验证可回滚）；revert 模型与文档变更
- 关联 ADR：[ADR-0003](../docs/development/ADR/ADR-0003-content-expansion.md)

## 2026-11-09｜X-02~X-08 内容扩展：S4 图片集 + S5 视频 + 首页装饰背景

- 任务卡 / 分级：ADR-0003 已采纳后落地；X-03/X-04a/X-05a 为契约追加（C 类已确认，实现级 B），X-02/X-04b/X-05b/X-06/X-08 为 B 类
- 主要变更（后端）：
  - `core/config.py`：新增 `MAX_VIDEO_SIZE_MB=50`、`MAX_VIDEO_DURATION_SECONDS=180`、`MAX_VIDEO_REQUEST_BODY_MB=52`
  - `core/response.py`：新增 `VideoTooLarge(41300)`、`UnsupportedVideo(41500)`、`VideoTooLong(40000)`、`VideoUnreadable(40000)`，沿用既有错误码族，不新增业务码
  - `main.py`：请求体上限按路径分流，仅 `/admin/media/video` 放宽到 52 MB
  - `services/upload.py`：新增 ISO BMFF `ftyp` 魔数判定与 `moov/mvhd` 时长解析（无 ffprobe 依赖），落盘 `uploads/videos/{YYYY}/{MM}/`
  - `services/admin.py` + `routers/admin.py`：新增 `POST /admin/media/video`
  - `schemas/tea.py`：`TeaDetail` 增 `video_url`/`video_duration`/`image_set`；`TeaBaseRequest` 增视频字段（`video_url` 强制 `/uploads/` 前缀，`video_duration` 1–180）
  - 新增 `repositories/tea_media_repo.py`、`services/tea_media.py`；`routers/teas.py` 增 `GET /teas/{id}/images`；`routers/admin.py` 增 `POST/DELETE /admin/teas/{id}/images[/{image_id}]`
  - `repositories/tea_repo.py`：详情查询 `selectinload(Tea.media_images)`
- 主要变更（前端）：
  - `types/index.ts`：`Tea` 增视频/图片集字段；新增 `AdminVideoUploadData`、`TeaMediaItem`；`AdminTeaPayload` 增视频字段
  - `api/admin.ts` / `api/teas.ts`：新增 `uploadAdminVideo`、`addAdminTeaImage`、`deleteAdminTeaImage`、`getTeaImages`
  - `TeaDetailView.vue`：视频播放器（无视频/加载失败整块隐藏）+ 图片集缩略图切换主图
  - 新增 `components/HeroBackground.vue`：纯装饰轮播（无跳转）、可关闭并记忆（localStorage）、尊重 prefers-reduced-motion、首张 eager 其余 lazy、加载失败自动剔除
  - `HomeView.vue`：Hero 接入装饰背景层，内容层 `z-index:1`
  - `AdminTeaEdit.vue`：视频上传/清除/预览 + 图片集上传/删除（上限 9 张提示）
  - 新增 6 张水墨风格占位背景 `public/images/banners/*.svg`（明确标注"占位图 · 待实拍替换"）
- 文档同步：
  - `docs/api/API_CONTRACT.md` v1.1→v1.2：`TeaDetail` 字段、§4.2.7、§4.6.9/10/11、§4.6.3/4.6.4 请求字段、变更记录
  - `docs/development/PLANS_扩展.md`：X-01~X-08 状态回填
  - 新增 `docs/product/素材清单.md`：目录/命名/格式/体积/兜底/来源登记/待补清单
- 契约 / 数据 / 安全影响：契约追加 4 个端点与 3 个详情字段（向后兼容，老字段不变）；无新增表（X-01 已完成）；请求体上限仅对视频端点放宽，其余仍 6 MB；视频与图片均校验魔数，不信任客户端类型
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `pytest tests/test_s4_s5.py -q` | 新增 S4/S5 | 13 passed | 视频上传正常/非视频/超时长/未登录/外链拒绝；图片集增删查/上限/越权/下架隐藏 |
  | `python -m pytest -q` | 后端全量 | **119 passed**（17.68s） | 原 106 条零回归 |
  | `ruff check app tests` / `ruff format --check app tests` | 后端静态 | 通过 | 格式化后复检通过 |
  | `npm run typecheck` | 前端类型 | 通过 | |
  | `npm run lint` | 前端 ESLint | 通过 | |
  | `npm run test:run` | 前端 Vitest | **30 passed** | 原有 30 条，无新增纯函数 |
  | `npm run build` | 生产构建 | 通过（4.90s） | 仅既有的 Element Plus chunk >500 kB 警告 |
  | 结构断言 | tea_guide / tea_guide_test | 通过 | X-01 已完成，本轮无 DDL 变更 |

- 验收结论：功能与门禁通过；**未做浏览器端手工冒烟**（未启动 dev server 实际点击），如需请另开一轮
- 遗留问题：
  - 图片集删除仅解除数据库关联，磁盘文件保留（同一 URL 可能被多茶复用）；已在 API 契约与素材清单注明
  - 视频时长解析依赖 `moov/mvhd`；缺失 `moov` 的异常封装文件会返回 40000「无法解析视频时长」
  - 六大茶类与每款茶的**真实实拍图尚未提供**，当前为占位图；`素材清单.md` 已列出待补项与来源登记字段
  - 首页背景在 `prefers-reduced-motion` 与用户关闭开关时停止轮播，但仍保留首张静图
- 回滚方式：revert 本轮提交即可；无 DDL 回滚需求
- 关联 ADR：[ADR-0003](../docs/development/ADR/ADR-0003-content-expansion.md)

## 2026-11-09｜X-07 素材落地：首页 6 张背景 + 6 款茶主图/图片集

- 任务卡 / 分级：B（仅新增静态素材与内容数据，不改端点行为、契约字段、表结构、业务规则）
- 需求来源：用户要求「图片去这些网站里找，加上；首页只加图片背景，不要视频」，并在 AskUserQuestion 中选择「用 CC0 公共领域图库」「茶品主图与图片集一起配」
- 关于用户给出的 5 个中文茶站（音茶网 / 茶语网 / ipucha / 茶百科 / 普洱茶网）：均为受版权保护的商业站点，且多启用防盗链，直接抓图存在侵权与失效风险，故**未采用**；改用 Wikimedia Commons 的 CC0 / Public domain 文件，可商用且可回溯
- 主要变更：
  - `frontend/public/images/banners/banner-{green,white,yellow,oolong,red,dark}.webp`：6 张首页装饰背景，1600×900，单张 92–307 KB（≤320 KB 限制）
  - `backend/uploads/2026/11/*.webp`：本轮生成 17 张茶品图片（6 张主图 + 11 张图集），1200×900，单张 ≤300 KB
  - 通过 admin API 写库：6 款茶 `teas.main_image_url` 全部指向本站 `/uploads/`；`tea_media` 图片集共 11 条（西湖龙井 3 / 白毫银针 2 / 正山小种 2 / 普洱熟茶 2 / 君山银针 1 / 大红袍 1）
  - `docs/product/素材清单.md`：§1 约束改写为"CC0 品类示意图"口径；§3 首页背景改为已落地 WebP；§5 重写为素材来源登记表（6 张背景 + 6 款茶，含 Commons 文件页、许可、日期）
  - 生成脚本与映射表仅存放于 `%TEMP%`，不进仓库
- 契约 / 数据 / 安全影响：无契约变更；仅写内容数据（`teas.main_image_url`、`tea_media` 行）；所有 URL 均由服务端 `POST /admin/upload` 生成，符合"禁止第三方外链"约束
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `python %TEMP%/build_dark.py` | 黑茶素材生成 | 通过 | banner 291 KB + 3 张茶图 |
  | `python %TEMP%/apply_tea_assets.py` | 写库（admin API） | 通过 | 6 款茶 PUT 均 200/0；图片集追加 11 条均 200/0 |
  | `python %TEMP%/verify_assets.py` | 落库与静态可访问性 | **failures = 0** | 6 款茶主图 + 图片集 URL 全部 HTTP 200；6 张 banner 全部 200（92–300 KB） |
  | `python -m pytest -q` | 后端全量 | 未运行 | 本轮无代码改动，仅数据与静态文件；如需可复跑 |

- 验收结论：通过（素材已落地并可访问）；浏览器端手工冒烟已通过（首页 6 张 CC0 背景轮播、无视频、无暂停按钮；详情页主图与缩略图切换正常）
- 已知局限：
  - CC0 图库只能提供**品类示意**：如"西湖龙井"主图为茶园/茶叶泛图，并非该款茶实拍；已在 `素材清单.md` §1.2 与 §5 顶部明确标注
  - 君山银针、大红袍已补足至各 2 张图集（2026-11-09 第二轮补充：Tieguanyin2、Tea cloth with autumn leaves motif 等 CC0/PD 图源）；六款茶图集均 ≥ 2 张
  - `banner-{category}.svg` 保留为三级兜底，未删除
- 回滚方式：删除 `frontend/public/images/banners/*.webp` 与 `backend/uploads/2026/11/` 下本轮新增文件；数据库侧清空 `teas.main_image_url`、删除 `tea_media` 对应行（或 `alembic downgrade` 后重建）
- 关联 ADR：[ADR-0003](../docs/development/ADR/ADR-0003-content-expansion.md)

## 2026-11-09｜项目交付 README 生成

- 任务编号 / 分级：TASK-20261109-README / A（纯文档产出，未触碰业务规则、契约、表结构与安全项）
- 需求来源：用户要求结合实际代码、配置与真实测试结果生成项目 README.md，并检查部署条件
- 主要变更：
  - `README.md`（新建）：项目简介 / 建设目标 / 功能介绍 / 技术栈 / 目录结构 / 数据库初始化 / 前后端启动 / 配置说明 / 测试方法与结果 / 截图 / 已知问题 / 部署条件与步骤
- 契约 / 数据 / 安全影响：无；README 未写入任何真实密码或密钥（种子管理员口令仅指引查阅 init.sql 注释并要求轮换）
- 测试证据（本次为验证 README 声明而实跑，非代码变更回归）：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `cd backend; python -m pytest -q --tb=no` | 后端全量 | 106 passed, 488 warnings in 47.02s | 与 README §10.2 一致 |
  | `cd frontend; npm run test:run` | 前端单测 | 30 passed（4 文件） | 与 README §10.2 一致 |
  | `cd frontend; npm run build` | 生产构建 | ✓ built in 3.51s | 仅有 chunk >500kB 既有告警 |
  | `python scripts/check_all.py` | 全量静态检查 | 全部通过 | 含 README 新增链接校验 |

- 验收结论：通过（截图缺失、CI 未实跑、未实机部署均已在 README 如实标注）
- 基线例外：无
- 遗留问题：README §11 截图待补充；首次部署需编写 Nginx 配置并实机验证 §13.2 步骤
- 回滚方式：删除 `README.md` 并回退本条记录
- 关联 ADR：无

## 2026-11-09｜全项目代码审查问题修复（S-1/S-2/G-1~G-6/O-1~O-3）

- 任务编号 / 分级：REVIEW-20261109 / B（无契约变更；涉及安全默认值与前台依赖调整）
- 需求来源：用户全项目代码审查报告的 10 个检查维度
- 主要变更：
  - `backend/app/core/config.py`：`DEBUG` 默认改为 `False`；`SECRET_KEY`/`MYSQL_PASSWORD` 取消弱默认值；新增启动校验，缺失 `SECRET_KEY` 拒绝启动（S-31）
  - `backend/alembic.ini`：移除 `root:root` 明文，改为占位值（实际连接仍由 `env.py` 注入）
  - `backend/app/repositories/tea_repo.py`：`origin` 筛选补 LIKE 通配符转义；`get_by_id` 增加 `with_tips` 参数
  - `backend/app/core/security.py`：`SESSION_EXPIRE_DAYS <= 0` 时显式判定立即过期（覆盖配置值分支）
  - `backend/app/routers/auth.py`：内联 import 上移，复用 `USERNAME_PATTERN`
  - `backend/app/services/favorites.py`：收藏查询跳过 `tea_tips` 联表
  - `backend/app/services/shares.py`：令牌重试耗尽改抛 `InternalError`，保持统一响应体
  - 新增 `repositories/_common.py`、`services/_common.py`、`schemas/_common.py`，消除 `escape_like`/`split_csv`/`iso_z` 重复定义
  - `frontend/src/stores/toast.ts` + `components/AppToast.vue`：自研 Toast 替代 `ElMessage`
  - `frontend/src/api/request.ts`：错误提示改用 Toast Store
  - `frontend/src/main.ts`：Element Plus 改为仅在 `/admin` 路由动态加载
  - `frontend/src/views/NotFound.vue`：`el-button` 改自研按钮
  - `frontend/src/types/index.ts`：新增 `ApiEnvelope<T>` 并统一 5 个 api 模块；删除未使用 `ShareToken`
  - 删除 `components/HelloWorld.vue`、`assets/{hero.png,vite.svg,vue.svg}`、`favorite_repo.count_by_user`
  - `scripts/check_layers.py` / `scripts/check_frontend.py`：清空历史遗留基线
  - `backend/tests/test_teas.py`：新增 origin 通配符转义回归用例
  - `backend/tests/conftest.py`：测试环境注入 `DEBUG`/`SECRET_KEY`
  - `AGENTS.md` §3.1：Element Plus 条目更新为已修复
- 契约 / 数据 / 安全影响：无端点、字段、表结构变更；SECURITY S-30/S-31 的代码兜底加强（默认值收紧 + 启动校验），未同步修改安全控制条目
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `cd backend; python -m ruff check app tests` | 后端风格 | 通过 | —— |
  | `cd backend; python -m ruff format --check app tests` | 后端格式 | 通过 | —— |
  | `cd backend; python -m pytest -q` | 后端全量 | 106 passed | 含新增 origin 转义用例 |
  | `cd frontend; npm run lint` | 前端 ESLint | 通过 | —— |
  | `cd frontend; npm run typecheck` | 前端类型 | 通过 | —— |
  | `cd frontend; npm run test:run` | 前端单测 | 30 passed | 纯函数用例 |
  | `cd frontend; npm run format:check` | 前端格式 | 通过 | —— |
  | `cd frontend; npm run build` | 生产构建 | 通过 | Element Plus 已拆分为 admin 异步 chunk |
  | `python scripts/check_all.py` | 全量静态检查 | 全部通过 | 五层 0 遗留、前台 UI 0 遗留 |

- 验收结论：通过
- 基线例外：无（AGENTS §3.1 Element Plus 遗留已清理）
- 遗留问题：
  - O-4 `ORDER BY RAND()` 未调整：当前茶品量级（<1000）下成本可接受，改为随机偏移会引入额外 count/offset 查询与分布偏差，待数据量增长后再评估
  - O-5 初始 Alembic 迁移未生成：当前建表仍以 `database/init.sql` 为准，正式上线前需在空库生成 baseline migration 并对现有环境 `alembic stamp`
- 回滚方式：`git revert` 本次提交
- 关联 ADR：无

## 2026-11-08｜G5 测试缺陷修复（D-01 ~ D-05）

- 任务编号 / 分级：TASK-20261108-G5FIX / **B**（未改 API 契约、表结构、权限/认证机制与安全控制口径；D-04 默认密码置空为向既有 SECURITY S-31 对齐，属实现向文档对齐）
- 需求来源：`docs/testing/TEST_REPORT.md` 缺陷清单；TEST_PLAN TC-AUTH-07 / TC-LIST-05 / TC-DEF-02 / TC-DEF-04；SECURITY S-21 / S-26 / S-31
- 主要变更：
  - `backend/app/core/security.py`：`max_age_days <= 0` 显式立即过期，修复 0 回落 30 天与 itsdangerous 同秒 `age=0` 不过期两处根因。
  - `backend/app/repositories/tea_repo.py` / `admin_repo.py`：新增 `_escape_like()`，转义 `\`/`%`/`_` 并显式 `escape="\\"`，修复搜索通配符返回全表。
  - `backend/app/main.py`：新增 6MB Content-Length 中间件（先注册，CORS 后注册为最外层），超限返回 413/41300。
  - `backend/app/core/response.py`：新增 `DataError → 400/40000`，仅记录方法/路径/异常类型，不写参数与 SQL。
  - `backend/app/core/config.py`：`ADMIN_PASSWORD` 默认置空（S-31），新增 `MAX_REQUEST_BODY_MB=6`。
  - `backend/.env.example`：清空 `ADMIN_PASSWORD` 并补充轮换命令；`backend/.env` 与 `database/init.sql` 的开发/演练种子保持不变。
  - 新增 `backend/app/scripts/rotate_admin_password.py` + `__init__.py`：bcrypt cost=10，复用 `user_repo`，输出不含明文。
  - `backend/tests/test_g5_system.py`：新增 DEF-02、DEF-04 两条回归，强化 AUTH-07（0/-1 过期、末位高位翻转篡改），共 23 条。
  - `docs/testing/TEST_REPORT.md`：更新统计、逐条结果、缺陷修复记录与命令输出。
- 契约 / 数据 / 安全影响：无 API 契约/表结构/迁移变更；未修改 SECURITY 规则；S-26 错误响应仍不泄露堆栈/SQL；S-31 通过默认密码清空 + 轮换脚本补齐。
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `python -m ruff format --check app tests` | 后端格式 | 55 files already formatted | 修复后复跑 |
  | `python -m ruff check app tests` | 后端 lint | All checks passed | 修复后复跑 |
  | `pytest -q <AUTH-07/LIST-05/DEF-02/DEF-04>` | 四条初测失败/未执行 | 4 passed | 失败用例全绿 |
  | `pytest -q <§7.1 门禁 9 条>` | 安全门禁 | 9 passed, 10 warnings in 6.86s | 含 DEF-04 真实轮换与恢复 |
  | `python -m pytest -q` | 后端全量 | 105 passed, 484 warnings in 17.25s | 0 skip |
  | `npm run lint / format:check / typecheck / test:run / build` | 前端质量门禁 | 全部通过；30 tests passed；build 12.21s | 主 chunk >500 kB 告警非失败 |
  | `python scripts/check_all.py` | 静态检查 | 全部通过 | 205 链接；29/60/32/7；153 文件无敏感信息 |
  | GitHub Actions CI | CI | 未运行 | 未在远端实跑，不标记通过 |

- 验收结论：**通过**（60/60 用例、32/32 高优先级；D-01～D-05 关闭；CI 未运行已如实标注）
- 基线例外：无新增；前台 Element Plus 仍为既有 3 项基线
- 遗留问题：
  - 生产 Nginx `client_max_body_size` 需配置为 6m 并复测 413（部署项，非代码范围）。
  - CI 需在 GitHub Actions 实跑后回填结果；未运行前不宣称通过。
  - `ADMIN_PASSWORD` 默认值为空需同步部署文档，避免新环境缺省注入导致无管理员。
- 回滚方式：`git revert` 本提交；代码回滚不影响数据库已存密码；如已在环境执行轮换，用原密码重新执行脚本恢复。
- 关联 ADR：无（均为既有规则内的缺陷修复，未产生架构级决策）

## 2026-11-08｜阶段 5（G5）系统测试

- 任务编号 / 分级：TASK-20261108-G5 / 测试任务（不改生产代码）
- 需求来源：TEST_PLAN v1.0 §5 / §7.1；用户阶段 5 系统测试要求
- 主要变更：
  - `backend/tests/test_g5_system.py`：新增 21 条补充用例，函数名携带 TC 编号，补齐认证边界、会话过期/篡改、管理员校验、分页排序、通配符、权限副作用、分享字段、并发与 E2E。
  - `docs/testing/TEST_REPORT.md`：新增 60 条用例执行记录、缺陷清单、并发与端到端证据、命令输出摘录。
- 契约 / 数据 / 安全影响：无接口、表结构、安全控制变更；发现 D-01–D-04 四项缺陷，未在本任务修复。
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `cd backend; python -m pytest -q --tb=no` | 后端全量 | 101 passed / 2 failed / 0 skipped | 失败为 TC-AUTH-07、TC-LIST-05，断言未放宽 |
  | `pytest -q <8 条安全门禁节点>` | TEST_PLAN §7.1 | 8 passed | TC-DEF-04 因脚本缺失未执行 |
  | `cd frontend; npm run lint / format:check / typecheck / test:run / build` | 前端质量门禁 | 全部通过；30 tests passed | 构建有 chunk >500 kB 告警，非失败 |
  | `python scripts/check_all.py` | 静态检查 | 全部通过 | 205 链接、29 端点、60 用例、32 安全项、7 表 |

- 验收结论：**不通过**（高优先级 TC-DEF-04 未执行，构成发布阻断；另有 3 条中优先级缺陷）
- 基线例外：无新增；前台 Element Plus 仍为既有 3 项基线
- 遗留问题：
  - D-01 `verify_session_token(max_age_days=0)` 回落 30 天，需按 `is not None` 修复。
  - D-02 搜索 `%`/`_` 未转义，返回全表，需在 repository 层转义。
  - D-03 10MB `shape_desc` 返回 500，需补请求体大小限制与字段长度上限。
  - D-04 `app.scripts.rotate_admin_password` 缺失；`admin123` 仍在 `.env`/`init.sql`，需实现轮换脚本并演练。
- 回滚方式：删除 `backend/tests/test_g5_system.py` 与 `docs/testing/TEST_REPORT.md` 即可；测试临时数据已清理。
- 关联 ADR：无

## 2026-11-08｜审计问题修复：门禁 / 错误处理 / 测试库隔离 / 认证回流

- 任务卡 / 分级：AUDIT-FIX-01 / **B**（未改 API 契约、表结构、认证机制与安全控制）；其中"创建测试库 + 测试配置"为 **C** 类，用户于 2026-11-08 通过选项明确确认
- 需求来源：PLANS.md T0-03、T0-04、T1-02、T5-01、T5-02、T5-03；TEST_PLAN TC-DEF-01、TC-DEF-03；AGENTS.md §4、§9、§10.1
- 主要变更：
  - `app/core/response.py`：新增兜底 `Exception` 处理器，统一返回 500/50000；服务端用 `logger.exception` 记录堆栈，响应体不含堆栈/SQL/表名
  - `backend/tests/conftest.py`（新建）：导入 `app.*` 前强制测试库；优先读取 `DATABASE_URL_TEST`，否则默认 `tea_guide_test`；启动断言库名必须 `*_test`；同时隔离 `UPLOAD_DIR` 到系统临时目录
  - `backend/tests/test_defense.py`（新建）：DEF-01（畸形 JSON、非 JSON Content-Type、参数类型错误、role 注入不落库）与 DEF-03（未捕获异常 500/50000、响应不泄露、服务恢复）
  - `backend/.env.example`：补充 `DATABASE_URL_TEST` 示例（注释状态）
  - `frontend/src/views/admin/AdminLogin.vue`、`AdminTeaEdit.vue`、`AdminTeas.vue`：Prettier 格式化
  - `frontend/src/utils/pendingAction.ts`（新建）+ `pendingAction.spec.ts`（新建）：登录前动作暂存/解析/30 分钟过期
  - `frontend/src/views/TeaDetailView.vue`：未登录点击笔记/分享时保存 pending_action，登录回跳后自动继续原动作并清理
- 契约 / 数据 / 安全影响：无端点、字段、表结构变更；500 响应符合 API_CONTRACT §1.6；未改动 SECURITY S-01–S-32
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `cd backend; python -m pytest -q` | 全部后端用例（82 条） | 82 passed | 已切换至 `tea_guide_test` |
  | `python -m ruff check app tests`、`ruff format --check` | 后端静态 | 通过 | 52 文件已格式化 |
  | `cd frontend; npm run test:run` | 前端 4 个 spec | 30 passed | 新增 pendingAction 5 条 |
  | `npm run lint`、`npm run typecheck`、`npm run build` | 前端 | 通过 | 仅既有 chunk >500kB 警告 |
  | `npm run format:check` | 前端格式 | 通过 | 3 个后台文件已修复 |
  | `python scripts/check_all.py` | 全量静态闸门 | 通过 | 29/60/32/7 常量一致；分层 0 违规 |
  | `SELECT COUNT(*) FROM tea_guide.users` / `tea_guide_test.users` | 数据库隔离 | 6 / 1 | 开发库未被测试写入；测试库仅种子管理员 |

- 验收结论：通过（本次用户确认的三项范围）
- 基线例外：`api/request.ts`、`main.ts`、`stores/toast.ts` 仍直接使用 Element Plus（AGENTS §3.1 基线，本次未扩大）
- 遗留问题：
  - DEF-02（超大请求体 413）、DEF-04（管理员密码轮换）仍未补用例；T5-04 上线安全项未开始
  - T1-02 仍采用整页登录而非 LoginModal，但笔记/分享/收藏的登录回跳动作已可自动续接
  - `tea_guide_test` 为本次手工创建并导入 `database/init.sql` 结构；CI 环境建库脚本尚未落地
- 回滚方式：回滚上述文件；如需彻底回滚测试库，执行 `DROP DATABASE tea_guide_test`
- 关联 ADR：无（沿用 PLANS.md §5.4 已定稿的测试库约定，非新增架构决策）

## 2026-11-08｜阶段 4：管理员后台（T4-01 ~ T4-06）

- 任务卡 / 分级：T4-01 ~ T4-06 / **B**（实现 API_CONTRACT §4.6 已定稿的 8 个 admin 端点与后台 5 页；未改契约路径/字段/错误码，未改表结构、认证机制与安全控制）
- 需求来源：PRD FR-6.1~6.5、模块 6；API_CONTRACT §4.6.1~§4.6.8；MODULE_DESIGN M6；DATA_MODEL `teas`/`tea_tips`/`operation_logs`；PAGE_SPECS 后台 A1~A5；SECURITY S-08/S-11/S-14/S-19/S-20/S-23/S-24/S-28；TEST_PLAN PERM-01~04、TEA-01~07、UPLOAD-01~05
- 主要变更：
  - **后端（T4-01 权限）**
    - `app/routers/admin.py`：router 级 `Depends(get_admin_user)` 先于参数校验执行；8 端点全部由后端鉴权
    - `backend/tests/test_admin.py`（新建）：游客 401/40100、普通用户 403/40300、角色实时读库、非法参数仍先返回 401/403
  - **后端（T4-02 ~ T4-06）**
    - `app/schemas/admin.py`（新建）：后台列表/统计/上下架/小贴士/上传响应 DTO；`extra='forbid'`
    - `app/schemas/tea.py`：`TeaBaseRequest` / `TeaCreateRequest` / `TeaUpdateRequest` 全量校验（枚举、必填非空、水温 70–100、最多 1 位小数、主图协议白名单）；`is_active`/`favorite_count`/`id` 不在请求体
    - `app/repositories/admin_repo.py`（新建）：含下架列表/状态筛选/分页、统计、写入与 operation_logs；只 add/flush，不 commit
    - `app/services/admin.py`（新建）：新增/编辑/上下架/小贴士/统计/上传业务；写操作与日志同事务；编辑 PUT 全量替换；小贴士省略保持、null/空白清空
    - `app/services/upload.py`（新建）：分块读取，>5 MB 立即 413/41300；JPEG/PNG/WebP 魔数判定，非法 415/41500；UUID 文件名；落盘路径强制在 `uploads/` 内
    - `app/main.py`：静态挂载目录与 `settings.UPLOAD_DIR` 对齐
    - `app/core/response.py`：新增 `FileTooLarge(41300)` / `UnsupportedMedia(41500)` / `InternalError(50000)`
  - **前端（T4-06）**
    - `src/types/index.ts`、`src/api/admin.ts`（新建）：admin 契约类型与 8 个请求封装
    - `src/views/admin/AdminLogin.vue`：管理员登录，非 admin 立即注销会话
    - `src/views/admin/AdminLayout.vue`：侧边栏/顶栏/退出；菜单改用真实路径，修复 `el-menu router` 按路由名跳转 404
    - `src/views/admin/AdminDashboard.vue`：3 张统计卡、六大茶类分布、最近 5 款
    - `src/views/admin/AdminTeas.vue`：茶类/状态/关键词筛选、分页、含下架列表、上下架二次确认
    - `src/views/admin/AdminTeaEdit.vue`：新增/编辑共用表单、主图上传、小贴士、上下架；不出现审核状态
    - `src/api/request.ts`：admin 端点 401 跳转 `/admin/login`
- 契约 / 数据 / 安全影响：**无契约与表结构变更**，无 Alembic 迁移；8 端点按 §4.6 实现。权限门禁、请求体白名单、日志同事务、上传魔数/大小/路径穿越均按 SECURITY 实现；前台可见性沿用既有 `is_active=1` 过滤，收藏与分享条目保留。
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `cd backend; python -m pytest tests/test_admin.py -q` | PERM/TEA/TIPS/STATS/UPLOAD | **19 passed** | 含 8 端点越权、上下架前台联动、收藏保留灰显、413/415、路径穿越 |
  | `cd backend; python -m pytest -q` | 后端全量 | **80 passed** | 364 warnings（既有 Pydantic/SQL echo），无失败 |
  | `cd backend; python -m ruff check app tests` | 后端 lint | All checks passed | —— |
  | `cd backend; python -m ruff format --check app tests` | 后端格式 | 通过 | —— |
  | `cd frontend; npm run test:run` | Vitest | **25 passed**（3 文件） | 本次未新增纯函数 |
  | `cd frontend; npm run lint` | ESLint | 通过 | —— |
  | `cd frontend; npm run typecheck` | vue-tsc | 通过 | —— |
  | `cd frontend; npm run build` | 生产构建 | 通过 | 仅 chunk >500kB 既有警告 |
  | `python scripts/check_all.py` | 链接/常量/分层/UI/记录/密钥 | **全部通过** | 205 链接；29/60/32/7 一致；五层 0 新增违规 |
  | 浏览器手工冒烟（3 次子代理） | 登录→概览→列表→新增→编辑 | **PASS** | `/admin` 统计卡与分布正常；`/admin/teas` 6 行+筛选；`/admin/teas/new` 表单完整；`/admin/teas/6/edit` 预填正确 |

- 验收结论：通过。首次冒烟发现侧边栏 `el-menu router` 使用路由名导致 404，已改为真实路径并复测；写操作（新增/编辑/上下架/上传提交）由 19 条 pytest 覆盖，浏览器仅做页面渲染与预填冒烟。
- 基线例外：无新增（后台组件使用 Element Plus 属既定规范；前台未新增 EP 引用）
- 遗留问题：
  - 浏览器冒烟未实际提交新增/编辑/上传表单，避免污染种子数据；对应写路径由 backend pytest 覆盖
  - `operation_logs` 仅写入、不提供查询接口（按需求约束）
- 回滚方式：revert 本次提交（移除 admin schema/repo/service、upload service、admin router 实现、`test_admin.py`、前端 admin api 与 5 页实现，恢复占位页与 request 拦截器）
- 关联 ADR：无（均为契约内实现；魔数自研校验未引入新依赖，故不触发技术选型决策）

## 2026-11-08｜阶段 3：收藏清单 + 品鉴笔记 + 分享（T3-01 ~ T3-06）

- 任务卡 / 分级：T3-01 ~ T3-06 / **B**（实现 API_CONTRACT §4.3–§4.5 已定稿的 10 个端点与对应前台页面；未改契约路径/字段/错误码，未改表结构、认证机制与安全控制）
- 需求来源：PRD FR-5.1~5.6；API_CONTRACT §2.4/§2.5/§2.6、§4.3.1~§4.5.4；DATA_MODEL §collection_lists/favorite_items/share_tokens；PAGE_SPECS §六/§七；TEST_PLAN FAV-01~07、NOTE-01~05、SHARE-01~10、PERM-03
- 主要变更：
  - **后端（T3-01 收藏）**
    - `app/schemas/favorite.py`、`app/repositories/favorite_repo.py`：收藏行查询/写入、`favorite_count` 原子 ±1（CASE 保证不低于 0）
    - `app/services/favorites.py`：收藏/取消幂等；下架茶新增收藏 40401、取消/状态允许；行写入与计数同事务；唯一冲突按已收藏处理
    - `app/routers/favorites.py`：POST/DELETE `/{tea_id}`、GET `/{tea_id}/status`
  - **后端（T3-02 清单与笔记）**
    - `app/schemas/list.py`、`app/repositories/list_repo.py`：默认清单 get-or-create、条目联查、标题/笔记更新
    - `app/services/lists.py`：标题 trim 后 2–20 字；笔记 ≤20,000 字、纯空白归一化为 null、清空不删除条目；未收藏写笔记 40430
    - `app/routers/lists.py`：GET `/lists`、PUT `/lists/title`、PUT `/lists/notes/{tea_id}`
    - `app/core/response.py`：新增 `FavoriteNotFound(40430)`
    - `app/core/auth_deps.py`：新增 `get_optional_user`（公开分享页计算 is_owner）
  - **后端（T3-03 分享）**
    - `app/schemas/share.py`、`app/repositories/share_repo.py`：8 位 URL-safe token、生效令牌查询、软撤销
    - `app/services/shares.py`：生成/复用、清单行锁 + 当前读保证并发生成仅一条生效令牌；撤销 403/409、不可复活；公开视图过滤笔记与所有者信息；copy 跳过已收藏/下架并返回 added/skipped/total，保存点兜底并发唯一冲突
    - `app/routers/shares.py`：POST `/generate`、POST `/revoke/{token}`、GET `/{token}`、POST `/{token}/copy`
  - **前端（T3-04 收藏交互）**
    - `src/types/index.ts`、`src/api/favorites.ts`、`src/api/lists.ts`、`src/api/shares.ts`：契约类型与请求封装
    - `src/components/FavoriteButton.vue`：图标/主按钮两态、乐观更新与失败回滚、pending 防重复、未登录跳转并在登录后自动重放收藏
    - `src/components/TeaCard.vue`、`src/views/TeaDetailView.vue`：接入收藏按钮与计数联动
    - 顺带修复：`LoginView.vue` / `RegisterView.vue` 密码输入内联事件经 Prettier 换行后触发 Vue 模板解析错误，提取为 `onPasswordInput` 方法
    - `AppHeader.vue` / `HomeView.vue` / `TeaListView.vue` 仅经 Prettier 全量格式化，无逻辑变更
  - **前端（T3-05 我的清单）**
    - `src/views/MyListView.vue`：标题内联编辑、条目列表、下架灰显、移除、空/错误/加载态、查询参数直达笔记/分享
    - `src/components/NoteEditor.vue`、`src/components/SharePanel.vue`：私密笔记编辑（20,000 字计数）、生成/复制/二次确认撤销
  - **前端（T3-06 分享公开页）**
    - `src/views/ShareView.vue`：只读展示、无笔记/所有者信息、下架灰显、撤销态与推荐、404 态；登录用户一键收藏并展示 added/skipped/total
  - **测试**
    - `backend/tests/test_favorites.py`（8 条，含 20 线程同用户收藏、12 用户并发收藏、10 线程取消）
    - `backend/tests/test_lists.py`（8 条，含 20 线程 get-or-create）
    - `backend/tests/test_shares.py`（10 条，含 20 线程生成令牌/20 线程 copy）
    - `frontend/src/utils/favorite.spec.ts`、`frontend/src/utils/list.spec.ts`（11 条纯函数用例）
- 契约 / 数据 / 安全影响：**无**（端点、字段、错误码均按 API_CONTRACT 实现；未改表结构，无 Alembic 迁移；未放宽 S 项。公开分享响应经测试断言不含 `tasting_note`/`username`/`user_id`）
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `cd backend; python -m pytest -q -k "FAV or fav_" tests/test_favorites.py` | TC-FAV-01~08 | 8 passed | 含 20 线程同用户收藏、12 用户并发收藏、10 线程并发取消 |
  | `cd backend; python -m pytest -q -k "note or perm or list" tests/test_lists.py` | TC-NOTE-01~05、PERM-03 | 8 passed | 含 20 线程清单 get-or-create |
  | `cd backend; python -m pytest -q -k "share" tests/test_shares.py` | TC-SHARE-01~10、PERM-03 | 10 passed | 含 20 线程生成、20 线程 copy |
  | `cd backend; python -m pytest -q` | 全量后端 | **61 passed** | 254 warnings（Pydantic/SQL echo），无失败 |
  | `cd backend; python -m ruff check app tests` | 后端 lint | All checks passed | —— |
  | `cd frontend; npm run test:run` | Vitest | **25 passed**（3 文件） | 新增 favorite 7 条、list 4 条 |
  | `cd frontend; npm run lint` | ESLint | 通过 | —— |
  | `cd frontend; npm run typecheck` | vue-tsc | 通过 | —— |
  | `cd frontend; npm run build` | 生产构建 | 通过 | 仅 chunk >500kB 既有警告 |
  | 浏览器手工冒烟（Playwright 子代理） | 登录→收藏→我的清单 | PASS | 心形按下、计数 2,180→2,181、`/my` 显示“共 1 款茶” |
  | 浏览器手工冒烟（Playwright 子代理） | 笔记→标题→生成→撤销→旧链接 | PASS | 笔记可见、标题“我的精选茶单”、token `IBLUuslR`、撤销后旧链接显示“这份分享已被撤销” |
  | `python scripts/check_all.py` | 链接/常量/分层/UI/记录/密钥 | **全部通过** | 205 条链接；29/60/32/7 一致；五层 0 违规；前台仅 3 项既有 EP 基线 |

- 验收结论：通过。手工冒烟未覆盖游客态公开页与游客一键收藏，这两项由 `test_share_05/09` pytest 覆盖。
- 基线例外：无新增（未在 `views/components` 直接 import Element Plus；分页、权限与响应字段均按契约）
- 遗留问题：
  - 前端人工冒烟未覆盖游客公开页与“一键收藏全部”的浏览器路径；已由 SHARE-05/09/10 后端用例覆盖，后续 T5-02 可补 Playwright 冒烟
  - `share_tokens.token` 大小写敏感依赖 MySQL 列 collation `utf8mb4_bin`；若未来切换数据库需补等价约束
- 回滚方式：revert 本次提交（移除 T3 新增 schema/repo/service/router、前端组件与页面、三份测试与两份 spec，恢复三个前端占位页与后端路由占位）
- 关联 ADR：无（均为契约内实现，无架构/技术选型变更）

## 2026-11-08｜阶段 2：茶品数据与浏览闭环（T2-01 ~ T2-05）

- 任务卡 / 分级：T2-01 ~ T2-05 / **B**（实现 API_CONTRACT 已定稿的 6 个只读端点与对应前台页面；未改契约路径/字段/响应体，未改表结构、认证机制与安全控制）
- 需求来源：PRD FR-1.1~1.6（列表/筛选/排序/搜索/分页）、FR-2.1~2.3（首页聚合/热门/随机）、FR-3.1（详情）、FR-6.3（下架不物理删除）；API_CONTRACT §4.2.1~§4.2.6、§2.2、§2.3、§2.3.1、§1.6；PAGE_SPECS §3/§4/§5；DESIGN_SYSTEM
- 主要变更：
  - **后端（T2-01）**
    - `app/repositories/tea_repo.py`（新建）：`list_teas` / `list_hot` / `get_random` / `count_by_category` / `count_by_province` / `get_by_id`；省级产地用 `substring_index(origin,' ',1)` 派生；仅查询，无业务判断
    - `app/services/teas.py`：参数解析、枚举校验（非法 → 40000）、keyword ≤50、page/page_size 夹取（上限 50）、sort 稳定次级键、`is_active=1` 过滤；详情不存在 40400 / 下架 40401；查询全部下沉到 repository（清除 §3.1 遗留）
    - `app/routers/teas.py`：6 个只读端点，静态段 `/categories` `/origins` `/hot` `/random` 先于 `/{tea_id}` 注册
    - `app/schemas/tea.py`、`app/schemas/__init__.py`：TeaListItem / TeaListResponse / TeaDetail（tips_* 扁平化、时间输出 `Z`）/ CategoryCount / OriginCount / TeaCreateRequest
    - `tests/test_teas.py`（新建）：20 条用例覆盖 6 端点、筛选组合、排序、分页夹取、搜索、40400/40401、下架隐藏
  - **前端（T2-02 ~ T2-05）**
    - `types/index.ts`：Tea / TeaListItem / TeaListData / CategoryCount / OriginCount / TeaSort / TeaListParams
    - `api/teas.ts`（新建）：6 个只读请求封装，路径与参数严格对齐契约
    - `utils/teaQuery.ts`（新建）+ `utils/teaQuery.spec.ts`（新建）：URL query（`category/origin/season/q/sort/page`）↔ 筛选状态 ↔ API 参数（keyword）双向转换、已选条件标签；14 条纯函数单测
    - `stores/tea.ts`：列表状态（list/total/page/pageSize/loading/error）+ 请求序号防竞态 + 茶类/产地计数缓存
    - `components/AppHeader.vue`、`AppFooter.vue`、`CategoryTag.vue`、`TeaCard.vue`（新建）：全站导航/页脚、茶类标签、图像失败占位茶卡；均无 Element Plus
    - `views/TeaListView.vue`：筛选面板（同维多选 / 跨维 AND，真实请求后端）、已选 pill 单项移除/清空、排序、搜索关键词 pill、URL 回填与前进后退同步、骨架屏、加载失败重试、空结果 + 热门推荐、分页（12 条/页）
    - `views/HomeView.vue`：Hero 搜索 150ms 防抖建议（最多 6 条，真实请求）、六大茶类计数入口、热门轨道（8 条）、随机发现 + 换一批
    - `views/TeaDetailView.vue`：骨架屏、主图失败占位、可点击茶类标签回跳筛选、冲泡参考、四大感官、tips 空值整块隐藏、同类推荐（同 category 排除自身，最多 4）、40400/40401 友好引导 + 3 款热门；收藏/笔记/分享仅入口（未登录跳登录，已登录提示下一阶段）
- 契约 / 数据 / 安全影响：无契约变更（6 端点均按 API_CONTRACT §4.2 实现）；无表结构/迁移变更；无安全控制项变更（只读接口对游客开放，权限不变）。文档无需同步修改。
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `cd backend; python -m pytest -q` | 后端全量 | **34 passed**（1 health + 13 auth + 20 teas），12 warnings（既有依赖弃用告警） | 覆盖 6 端点与筛选/排序/分页/404 |
  | `cd backend; python -m ruff check app tests` | 后端 lint | All checks passed | —— |
  | `cd backend; python -m ruff format --check app tests` | 后端格式 | 33 files already formatted | 本次格式化 `tests/test_teas.py` |
  | `cd frontend; npm run lint` | ESLint | 通过（无输出即 0 error） | 新组件未引入 Element Plus |
  | `cd frontend; npm run typecheck` | vue-tsc | 通过 | —— |
  | `cd frontend; npm run test:run` | Vitest | **14 passed**（1 file） | `src/utils/teaQuery.spec.ts` |
  | `cd frontend; npm run build` | 生产构建 | 通过（1719 modules，5.11s） | 仅有既有 chunk >500kB 体积告警 |
  | `python scripts/check_all.py` | 链接/常量/分层/UI/记录/密钥 | 全部 OK | 五层遗留 **0 项**；前台 Element Plus 仅剩 3 项既有基线 |
  | 浏览器实测（真实 HTTP） | 列表页 | PASS | 6 张真实卡片；点「绿茶」后 `?category=green` 且仅剩西湖龙井；切「收藏最多」后 `?sort=favorite` |
  | 浏览器实测（真实 HTTP） | 首页 | PASS | 6 类计数各 1（合计 6）；热门 6 张（数据仅 6 条）；随机发现显示西湖龙井；输入「龙井」出现建议 |
  | 浏览器实测（真实 HTTP） | 详情页 `/teas/1` | PASS | 西湖龙井、85℃/3g/90s、四大感官、4 块小贴士；茶类标签跳 `?category=green` |
  | 浏览器实测（真实 HTTP） | 下架 `/teas/3` | PASS | 临时将 id=3 `is_active=0`：显示「这款茶已下架」+ 列表/首页入口 + 3 款热门；**已验证恢复 `is_active=1` 与 `updated_at`** |

- 已确认口径（本阶段）：
  - 40401 响应 `data=null`，无法得知茶类，下架详情引导改用「热门推荐 3 款」而非 PRD 的「同类 3 款」（PAGE_SPECS 对无效 id 同样用热门引导）
  - 详情页收藏/笔记/分享按钮只做入口，写操作属阶段 3
- 验收结论：通过
- 基线例外：未新增。触达 `services/teas.py` 时已把 `db.query` 下沉到 repository，`check_layers` 历史遗留由 2 项降为 0 项；Element Plus 3 项基线未触碰
- 遗留问题：
  - 收藏清单内「下架灰显占位」依赖阶段 3 收藏清单页面，本阶段尚无清单模块；后端详情已按 40401 处理，未物理删除
  - 同类推荐逻辑已实现，但种子数据每类仅 1 款，当前详情页不展示同类卡；补种子数据后自动生效
  - 种子主图为外链 URL（前端原样消费、不构造路径；加载失败已占位）；上传接口与 `/uploads` 落地属 T4-04
  - 前端 `api/request.ts`、`stores/toast.ts`、`main.ts` 仍引用 Element Plus（既有基线，未新增引用）
- 回滚方式：回退本批前端/后端改动并删除 `app/repositories/tea_repo.py`、`api/teas.ts`、`utils/teaQuery*`、4 个组件即可；数据库无结构变更，无需迁移回滚
- 关联 ADR：无

## 2026-11-08｜用户认证模块（注册/登录/当前用户/退出）

- 任务卡 / 分级：B（实现已有契约定义的 5 个认证端点，跨 Router/Service/Repository/Schema 多层 + 前后端联动；不改契约、不改表结构、不改认证机制）
- 需求来源：用户要求实现用户认证模块，含注册、登录、获取当前用户、退出登录；前后端联动；表单校验与路由守卫
- 认证机制确认：用户确认沿用项目已确认的 **HttpOnly Cookie 方案**（`tea_session` + itsdangerous 签名），不使用 JWT/Authorization 头（C 类冲突已对话确认，2026-11-08）
- 主要变更：
  - **后端**：
    - `core/security.py`：bcrypt `rounds=10` 对齐 SECURITY S-01；新增 `DUMMY_HASH` 常量用于登录等时比对（S-04）
    - `schemas/auth.py`：用户名正则 `^[A-Za-z0-9\u4e00-\u9fa5]{3,20}$`、密码 6-64、`extra='forbid'`；`UserResponse` 补 `created_at`/`role` Literal；新增 `UsernameAvailabilityResponse`
    - `repositories/__init__.py` + `repositories/user_repo.py`（新建）：`get_by_username`/`get_by_id`/`create_user`，纯查询无业务判断
    - `services/auth.py`：下沉到 repository；注册捕获 `IntegrityError`→40910；登录对不存在用户做哑哈希等时比对（S-04）
    - `core/auth_deps.py`（新建）：`get_current_user`（验签→查库→40100）、`get_admin_user`（role 校验→40300）
    - `routers/auth.py`：新增 `GET /username-availability`；`/register`、`/login` 返回契约 `User`；Cookie 补 `secure`/`path`；`/me` 用 `Depends(get_current_user)`；`/logout` 清 Cookie 带相同属性；移除对 Model 的直接 import
    - `core/response.py`：新增 `RequestValidationError` 处理器，FastAPI 422 重映射为 400/40000（API_CONTRACT §1.6）
    - `tests/test_auth.py`（新建）：13 条用例覆盖注册/重复注册/格式校验/登录成功/错误密码/不存在用户/未登录 /me/已登录 /me/登出/可用性/密码哈希
  - **前端**：
    - `types/index.ts`：`User` 补 `created_at`
    - `api/auth.ts`（新建）：`login`/`register`/`logout`/`getMe`/`checkUsernameAvailability`
    - `stores/user.ts`：接 `api/auth`；`hydrate()` 调 `/auth/me` 校验 Cookie；移除 localStorage 依赖
    - `api/request.ts`：401 非公开接口跳转 `/login?redirect=...`；公开接口不跳转避免死循环
    - `views/LoginView.vue`（新建）：自研表单，必填校验、错误提示、登录成功跳来源页
    - `views/RegisterView.vue`（新建）：用户名 3-20 中英数、密码 6-64、确认密码、防抖可用性校验
    - `router/index.ts`：加 `/login`、`/register`；守卫用 `useUserStore`；受保护页未登录跳登录
    - `main.ts`：启动时 `userStore.hydrate()` 恢复登录态后再挂载
  - **环境**：`backend/.env` 的 `MYSQL_PASSWORD` 更新为实际密码；执行 `database/init.sql` 建库 + 种子数据
- 契约 / 数据 / 安全影响：无（严格按 API_CONTRACT §4.1 实现；未改表结构；未改 SECURITY 控制项；bcrypt cost=10 与文档一致）
- 清理的基线遗留：
  - `services/auth.py` 的 `db.query` 直查 → 下沉到 `repositories/`（§3.1 遗留 -1）
  - `core/auth_deps.py` 不存在 → 已创建（G-01）
  - `routers/auth.py` 响应缺 role/created_at → 已按契约补齐（G-02）
  - `main.py` 异常处理器未注册 → 此前任务已注册；本次补 `RequestValidationError` 映射
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `cd backend; python -m pytest -q` | 后端全量 | 14 passed（1 health + 13 auth） | AUTH-01~AUTH-09 全覆盖 |
  | `cd backend; python -m ruff check app tests` | 后端 lint | All checks passed | —— |
  | `cd backend; python -m ruff format --check app tests` | 后端格式 | 31 files already formatted | —— |
  | `python scripts/check_layers.py` | 五层分层 | 通过 | 仅遗留 `services/teas.py` 基线项，未新增违规 |
  | `python scripts/check_frontend.py` | 前台 UI | 通过 | 仅遗留 Element Plus 3 项基线 |
  | `cd frontend; npm run lint` | ESLint | 通过（0 errors, 0 warnings） | —— |
  | `cd frontend; npm run typecheck` | vue-tsc | 通过 | —— |
  | `cd frontend; npm run build` | 生产构建 | 通过 | 仅有 chunk >500kB 警告（预存） |
  | 端到端冒烟（真实 HTTP） | 注册/登录/me/登出 | 全部通过 | 见下方明细 |

  端到端冒烟明细：
  - 注册 → 200 + User(id/username/role/created_at) + `Set-Cookie: tea_session=...; HttpOnly; Max-Age=2592000; Path=/; SameSite=lax`
  - 重复注册 → 409 + `{"code":40910,"message":"用户名已存在","data":null}`
  - 错误密码登录 → 401 + `code=40110`
  - 正确密码登录 → 200 + User
  - `/me` 带 Cookie → 200 + User
  - `/me` 无 Cookie → 401 + `code=40100`
  - `/me` 无效 Cookie → 401 + `code=40100`
  - 登出 → 200，后续 `/me` → 401
  - 用户名可用性 → 200 + `available:false`（已存在用户）
  - 种子 admin/admin123 登录 → 200 + `role=admin`
  - 数据库验证：`users.password_hash` 以 `$2b$10$` 开头，响应体与日志不含密码

- 验收结论：通过（14 测试全绿；ruff/分层/前端检查全过；端到端 9 场景全部符合契约）
- 遗留问题：
  - 前端 `api/request.ts`、`stores/toast.ts`、`main.ts` 仍引用 Element Plus（基线遗留，本次未触碰 toast 替换）
  - `services/teas.py` 仍 `db.query` 直查（基线遗留，非本次范围）
  - TEST_PLAN 其余 47 条用例待落地（本次落地 AUTH 组 13 条 + 已有 health 1 条）
- 回滚方式：revert 本提交；数据库可 `DROP DATABASE tea_guide` 后重跑 init.sql
- 关联 ADR：无（沿用已确认的认证机制设计，未产生新架构决策）

## 2026-11-08｜前后端基础工程核对与补齐

- 任务编号 / 分级：TASK-20261108-01 / A
- 需求来源：开发计划第一个任务（搭建前后端基础工程）；AGENTS.md §5/§7（统一响应体）、§13 已知待办（`register_exception_handlers` 未注册，安全 P0）
- 现状核对（7 项）：接口前缀 `/api/v1`、`request.ts` 的 `withCredentials: true`、npm lockfile 均已合规，跳过；`repositories/` 层本次不建——健康检查不查库，按 §3.1 基线待 teas/auth 端点触达查询时再下沉
- 主要变更：
  - `backend/app/main.py`：注册 `register_exception_handlers(app)`；`/api/v1/health` 改为统一响应体 `ok({"status": "ok"})`
  - `backend/tests/test_health.py`：断言同步为 `{code: 0, message: "ok", data: {status: "ok"}}`
  - `backend/.env.example`：新增（数据库 / SECRET_KEY / 管理员账号等参数示例）
  - `backend/.env`：由示例复制生成（开发默认值，.gitignore 已覆盖，不进 Git）
- 契约 / 数据 / 安全影响：健康检查不在 API_CONTRACT 29 个业务端点内，契约文档无需变更；安全影响为正面修复（业务异常不再退化为 500）
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `python -m ruff check app tests` | 后端静态检查 | All checks passed | —— |
  | `python -m pytest -q` | 健康检查用例 | 1 passed（2 条 deprecation 警告，为依赖既有行为） | —— |
  | `npm run build` | 前端 typecheck + 构建 | 成功（vue-tsc + vite build 通过；chunk >500kB 警告为既有体积提示） | —— |
  | `Invoke-WebRequest http://127.0.0.1:8000/api/v1/health` | 后端直连 | 200，`{"code":0,"message":"ok","data":{"status":"ok"}}` | —— |
  | `Invoke-WebRequest http://localhost:5173/api/v1/health` | 经 Vite 代理前后端通信 | 200，同上统一响应体 | 5173 监听在 `[::1]`，需用 localhost 访问 |
  | `Invoke-WebRequest http://localhost:5173/` | 前端首页 | 200 | —— |
  | `npm run test:run` / `npm run lint` | 前端测试 / lint | 未运行 | 本次无前端代码改动 |

- 验收结论：通过（前后端均在本机运行，健康检查经代理返回统一响应体）
- 基线例外：无新增；`request.ts` 引用 ElMessage 属 §3.1 既有遗留，本任务未触达
- 遗留问题：
  - MySQL 建库与 `init.sql` 种子数据为下一任务（T0-02a），本次健康检查不依赖数据库
  - `config.py` 使用 class-based Config（Pydantic V2 弃用警告），触达配置项时再迁移为 `ConfigDict`
  - SECRET_KEY / 管理员密码为默认值，上线前必须轮换（AGENTS §13）
- 回滚方式：还原 `main.py`、`test_health.py`，删除 `.env` / `.env.example`
- 关联 ADR：无

## 2026-11-07｜生成 MVP 开发计划

- 任务编号 / 分级：TASK-20261107-PLAN / B（纯文档产出，未触碰业务规则、契约、表结构与安全项）
- 需求来源：用户要求基于已确认文档生成 `docs/development/PLANS.md`，并在答复决策项后继续完善计划（不编码）
- 主要变更：
  - `docs/development/PLANS.md`：v1.0 新增 6 阶段 / 27 个任务的开发计划，含目标、输入、输出、模块、依赖、验收标准、测试要求与非目标
  - 计划将用户建议顺序中的"失物拾物/认领"更正为"茶品发现/收藏分享"（依据 API_CONTRACT §1.12 与 PRD 核心闭环），该修正已获用户确认（D1）
  - 明确 G3 为 MVP 闭环里程碑、G0–G3 为优先交付范围，并列出 3 组允许并行的任务对与关键路径
  - v1.1 按用户答复更新：D1 认可、D2（Alembic 基线）暂缓、D3 由用户逐阶段下达指令、D4 本机 MySQL 已装但无数据库、D5 暂不编码
  - v1.1 新增：任务总索引、27 任务实施步骤、测试环境与数据约定、通用 DoD、文档同步矩阵、前置环境核对清单；T0-02 拆分为 02a（建两库 + init.sql，可先做）/ 02b（Alembic 基线，待 D2）
- 契约 / 数据 / 安全影响：无（未改端点、字段、表结构、S 项）
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `python scripts/check_all.py` | 链接/常量/分层/前端/记录/密钥 | OK：204 条链接有效，29/60/32/7 一致，无新增基线违规 | 文档改动后复跑 |
  | `pytest` / `npm run test:run` | 业务测试 | 未运行 | 本次仅完善计划文档，无代码改动 |

- 验收结论：通过（计划 v1.1 已按用户答复定稿；按 D5 不进入编码）
- 基线例外：无
- 遗留问题：仅 D2（Alembic 基线口径）待定，不阻塞 G0 的 T0-01/02a/03/04 准备；开工需用户另行指令；计划确认后可回填 AGENTS.md 文档索引
- 回滚方式：删除 `docs/development/PLANS.md` 并回退本条记录
- 关联 ADR：无（D2 确认后若选择"init.sql 即基线"，再补提议 ADR）

## 2026-11-07｜规范化落地：自动化闸门与现状基线

- 任务编号 / 分级：TASK-20261107-NORMS / C（修改 CI 关键流程与项目规范；用户于 2026-11-07 以"全部优化一下"确认）
- 需求来源：用户对 AI 项目规范有效性审计后的整改要求
- 主要变更：
  - `AGENTS.md`：新增 §0 速览（命令/路由表/五条红线）、§3.1 现状基线；补全 C 类清单与用户豁免；新增文档冲突优先级；更新 §13 待办
  - `docs/development/DEVELOPMENT_GUIDE.md` v1.2：A/B 唯一边界、npm 命令、CI/构建类 C 项、用户豁免、C 类前置 ADR、测试与 CI 现状
  - `harness/TASK_TEMPLATE.md`：新增任务编号、边界确认、用户确认记录、基线例外；修正 `tea_type`→`category` 与 npm 命令
  - `harness/build-log.md`：模板补任务编号/基线例外；明确 ADR 时点
  - `docs/development/ADR/README.md` + `ADR-0002-enforce-norms-with-automation.md`：自动化闸门决策（基线 + CI + 渐进清理）
  - `.github/workflows/ci.yml`：替换 Next.js 模板，改为后端 lint/format/test、前端 lint/format/typecheck/test、文档与记录守卫三个作业
  - `.github/pull_request_template.md`：任务卡、C 类确认、测试证据、文档同步清单
  - `scripts/check_links.py` / `check_constants.py` / `check_layers.py` / `check_frontend.py` / `check_records.py` / `check_secrets.py` / `check_all.py`：可执行规范检查
  - `frontend/`：新增 lint/format/typecheck/test 脚本与 ESLint、Prettier、Vitest 配置；移除 `toast.ts` 未使用 import；Prettier 统一 `src/` 格式
  - `backend/`：新增 `pyproject.toml`、`tests/test_health.py`；Ruff 自动修复 21 项并格式化 14 个文件
  - `docs/architecture/TECH_STACK.md`：包管理器统一为 npm
  - `specs/*`：标注为历史草稿，非权威
- 契约 / 数据 / 安全影响：无（未改端点、字段、表结构、S 项）
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | `python scripts/check_all.py` | 链接/常量/分层/UI/记录/密钥 | 全部 OK | 链接 189 条；常量 29/60/32/7；2 项分层与 3 项 Element Plus 为基线遗留 |
  | `cd backend; python -m ruff check app tests` | 后端 lint | All checks passed | 自动修复 21 项 |
  | `cd backend; python -m ruff format --check app tests` | 后端格式 | 27 files already formatted | 首次基线格式化 14 个文件 |
  | `cd backend; python -m pytest -q` | 健康检查 | 1 passed, 2 warnings | 仅验证应用可启动；TEST_PLAN 未落地 |
  | `cd frontend; npm run lint` | ESLint | 通过 | 基线文件已豁免 |
  | `cd frontend; npm run format:check` | Prettier | 通过 | 覆盖 `src/**` |
  | `cd frontend; npm run typecheck` | vue-tsc | 通过 | —— |
  | `cd frontend; npm run test:run` | Vitest | 0 tests, exit 0 | `--passWithNoTests`；尚无纯函数用例 |
  | `cd frontend; npm run build` | 生产构建 | 通过 | 仅有 chunk >500kB 警告 |
  | `npm ci --dry-run --prefix frontend` | lockfile 同步 | 通过 | —— |
  | `python -c "import yaml; ..."` | CI YAML 语法 | 通过 | —— |

- 验收结论：有条件通过（TEST_PLAN 未落地；CI 尚未在 GitHub Actions 实跑）
- 基线例外：Element Plus 3 个文件、Service 直连查询 2 个文件；本次只登记，未新增违规
- 遗留问题：
  - TEST_PLAN 60 条用例待落地；前端 Vitest 尚无用例
  - CI 配置已完成本地静态检查，但尚未在 GitHub Actions 实跑
  - `npm ci` 尚未在干净环境验证（本地使用 `npm install`）
  - 历史遗留清理：repositories 下沉、`auth_deps.py`、异常处理器注册、Element Plus 前台替换
- 回滚方式：revert 本提交；脚本与 CI 为新增文件，不影响运行时
- 关联 ADR：ADR-0002（本次为规范机制建设，ADR 与实施同批完成；后续 C 类按新规前置）

## 2026-11-07｜建立开发知识沉淀机制

- 任务卡 / 分级：B（纯文档与流程建设，未触碰业务规则、API 契约、表结构与安全项；用户已明确指定产出物）
- 需求来源：用户要求建立 ADR 与 build-log 机制，并更新 AGENTS.md
- 主要变更：
  - `docs/development/ADR/README.md`：新增 ADR 目录说明、触发条件、编号与状态规则、索引
  - `docs/development/ADR/TEMPLATE.md`：新增决策记录模板（背景 / 驱动因素 / 备选方案 / 最终选择 / 影响 / 验证）
  - `docs/development/ADR/ADR-0001-knowledge-capture-mechanism.md`：记录本机制自身的三方案对比与选型
  - `harness/build-log.md`：新增本日志、条目模板与问题复发台账
  - `docs/api/README.md`：新增接口文档目录索引与变更同步清单
  - `docs/architecture/README.md`：新增架构/数据文档索引与变更同步清单
  - `AGENTS.md`：§10 增补文档索引，新增 §10.1 知识沉淀机制，§12 增加交付留痕要求
  - `docs/development/DEVELOPMENT_GUIDE.md`：阶段 9「更新相关文档」增加任务留痕一行
- 契约 / 数据 / 安全影响：无（未修改 API_CONTRACT、openapi.yaml、DATA_MODEL、init.sql、Alembic、SECURITY）
- 测试证据：

  | 命令 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | PowerShell 相对链接存在性校验 | 新增/修改的 8 份 Markdown 中的相对链接 | 8 文件全部通过 | 输出 `ALL LINKS OK (8 files)` |
  | `pytest` / `vitest` | 后端 / 前端 | 未运行 | 本次无代码改动，不声称通过 |

- 验收结论：通过（纯文档变更，链接校验通过；无代码测试可跑）
- 遗留问题：无
- 回滚方式：优先 `git checkout backup-20261107-pre-knowledge-capture` 回到本次变更前（tag 指向 e37a97c）；或删除新增的 ADR/build-log/README 文件，还原 AGENTS.md 与 DEVELOPMENT_GUIDE.md 对应段落
- 关联 ADR：[ADR-0001](../docs/development/ADR/ADR-0001-knowledge-capture-mechanism.md)




## 2026-11-10 素材替换候选检索（实拍图）

- 任务卡 / 分级：A（只做检索与文档登记，未下载、未替换、未改代码与数据）
- 需求来源：用户要求"去网上找可以放上去替换的实拍图，先找，后续再替换"
- 主要变更：`docs/product/素材清单.md` 新增 §7「替换候选：实拍图」，登记 36 款茶品主图候选与 20 条内容封面候选（均来自 Wikimedia Commons，含许可与尺寸），并列出缺口清单与三条可选路线
- 检索方式：Commons API 分类遍历 + 关键词检索（namespace 6），按 mime=JPEG/PNG/WebP、宽度 ≥1200、许可 ∈ CC0/PD/CC BY/CC BY-SA 过滤
- 契约 / 数据 / 安全影响：无
- 测试证据：

  | 项目 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | 候选许可核验 | 36 茶品 + 20 内容 | 完成 | 元数据取自 Commons `extmetadata`，未下载原图 |
  | 图片题材核验 | 全部候选 | 未完成 | 仅依据文件名与描述筛选，替换前需逐张开图确认 |
  | `pytest` / `vitest` | 后端 / 前端 | 未运行 | 本次无代码改动 |

- 验收结论：候选清单已落盘；缺口 11 款茶品需自拍或采购商业授权
- 遗留问题：商业图库（视觉中国、千库网、Pexels、Unsplash）因授权或反爬限制未纳入；若用户接受商业授权图片，可再补一轮


## 2026-11-10 素材替换候选补齐（第二轮：网页检索）

- 分级：A（仅检索与文档登记；未进 uploads、未替换、未改代码）
- 需求：用户要求 36 款茶品"必须全都有图"
- 做法：Commons 中文关键词 + 全分类遍历仍缺 12 款，改用 360 图片检索补齐；下载 3 张/款预览图至 `%TEMP%\tea_preview2`（不进仓库），拼图目检后每款选 1 张
- 结果：36 款茶品全部有候选（24 款可商用 §7.1 / 12 款网页预览 §7.3）；内容封面补 3 项（玻璃茶壶、安溪、祁门）
- 关键修正：祁门原网页候选实为临沧昔归茶园，已改用 Commons `Flickr - cyclonebill - Keemun.jpg`
- 风险：§7.3 候选版权未核实，多数带店铺水印或平台角标；**未经授权不得上线**
- 测试证据：本轮无代码改动，`pytest` / `vitest` 未运行


## 2026-11-10 素材替换落地（第三轮：全量替换 36 茶品主图 + 19 内容封面）

- 分级：A（仅替换素材文件与两个图片字段数据，未改业务规则、API 契约、表结构、安全项与代码）
- 需求来源：用户「现在直接替换这些图」「必须全都有」
- 数据变更范围：`teas.main_image_url`（36 条全量）、`content_items.cover_image`（19 条）；其余字段与业务数据未动，表结构未变（无 Alembic 迁移）
- 做法：
  1. Commons 24 张按 `Special:FilePath/<文件名>?width=1600` 下载；§7.3 网页候选 14 张直接从 `%TEMP%\tea_preview2` 取用
  2. 统一处理：EXIF 方向校正 → 透明底压白 → 转 JPEG → 最长边 ≤1600px → 质量 85/75/70/60 逐级压至 ≤400KB
  3. 以 `uuid4().hex.jpg` 落盘 `backend/uploads/2026/11/`（脚本批量处理，未走 `POST /admin/upload`；命名与格式约束与服务端校验一致）
  4. 目检发现武夷肉桂、川红带「惠农网」水印，已裁除底部 9% / 14.5% 后覆盖保存
  5. 回填 DB → 启动后端逐条 `GET` 校验 → 登记 §7.5
- 结果：36/36 茶品主图 + 19/19 内容封面替换完成；36 茶品 + 39 内容条目图片 URL 全部 HTTP 200，无死链
- 测试证据：

  | 项目 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | 静态文件 + HTTP 校验 | 36 茶品 + 39 内容封面 | 通过 | 逐条 `GET http://127.0.0.1:8000/uploads/...`，全部 200 且 `content-type: image/jpeg` |
  | 列表接口抽查 | `GET /api/v1/teas?page=1&page_size=3` | 通过 | `code=0`，返回新 URL |
  | 目检 | 12 张网页来源图（拼图）+ 2 张裁切复核 | 通过 | 题材匹配；2 张水印已消除 |
  | `pytest -q` | 后端全量 | 通过 | 170 passed |
  | `vitest` | 前端 | 未运行 | 本次无前端代码改动 |

- 素材体积：多数 130–330KB，最大 670KB（西双版纳古茶林），均 < 5MB 服务端上限
- 遗留问题（重要）：
  - §7.3 来源的 **14 张（12 茶品 + 2 内容）版权未核实**，仅作 MVP 演示，上线前必须替换或取得书面授权；已在 §7.3 / §7.5 显式标注
  - Commons 中 CC BY / CC BY-SA 图上线需按作者署名，署名依据见 §7.5 表格
  - 庐山云雾（600×450）、川红（400×256）、海马宫茶（400×400）分辨率偏低，卡片展示可接受，详情页大图会糊
  - 旧主图文件仍保留在 `backend/uploads/2026/11/`，未删除（便于回滚），后续可统一清理
- 回滚方式：本次每个字段的旧 URL 见 `%TEMP%\tea_apply_db.py` 运行输出（tea/ct 行），旧文件均未被覆盖，可直接回填恢复


## 2026-11-10 首页背景高清重制（六大茶类 banner）

- 分级：A（只替换 `frontend/public/images/banners/*.webp` 静态素材，未改组件、样式、接口与表结构）
- 需求来源：用户「首页的背景图要高清的，和项目要契合匹配的」
- 变更内容：6 张背景由 1600×900 品类特写（茶叶/干茶/盖碗）换为 ≥3000px 原图的**茶园 / 茶山实拍**，统一 16:9 裁切重编码

  | 茶类 | 新来源（Commons） | 授权 | 作者 | 输出 |
  |---|---|---|---|---|
  | 绿茶 | Tea Garden Hangzhou（杭州茶园云雾石径） | CC BY 4.0 | Takashishin | 2200×1238 / 500KB |
  | 白茶 | 太姥山石景（福鼎太姥山，白茶发源地） | CC BY 3.0 | rheins | 2560×1440 / 307KB |
  | 黄茶 | Xiding Tea Plantation 01（茶山梯田） | CC BY-SA 4.0 | 阿道 | 2200×1238 / 375KB |
  | 乌龙茶 | 深山茶园（武夷岩壁＋茶园梯田） | CC BY 3.0 | rheins | 2200×1238 / 476KB |
  | 红茶 | Camellia sinensis 02（茶园行垄） | CC BY-SA 3.0 | Armin Kübelbeck | 2200×1238 / 371KB |
  | 黑茶 | 景迈大寨与景迈山（普洱景迈山古茶林） | CC BY-SA 4.0 | Zhangmoon618 | 2200×1238 / 368KB |

- 处理：EXIF 校正 → 16:9 中心裁切（oolong 下偏 0.92 保留茶园梯田）→ LANCZOS 缩放 → WebP（质量 56–74，`method=6`）逐级压至 ≤500KB
- 问题与修复：首次按 2560 批量裁切时，`green`/`oolong` 原图 4:3 被误用「宽向裁切」分支导致左右各出现黑边，已改为按实际比例分支裁切并复检（左右 5% 区域灰度 45–133，无零值黑边）
- 测试证据：

  | 项目 | 范围 | 结果 | 说明 |
  |---|---|---|---|
  | HTTP 校验 | 6 张 banner | 通过 | `GET http://localhost:5173/images/banners/banner-*.webp` 全部 200、`image/webp`、307–500KB |
  | 目检 | 6 张成图 + 裁切复核 | 通过 | 题材为茶园/茶山，构图完整，无黑边、无水印 |
  | `pytest` / `vitest` | — | 未运行 | 本次无后端/前端代码改动，仅静态资源替换 |

- 溯源：登记已同步至 [素材清单 §5.1](../docs/product/素材清单.md)，旧图未删除（Commons 同名文件可随时重新生成）
- 遗留：CC BY / CC BY-SA 图上线需署名；白茶 banner 为太姥山风景（非茶园），如不认可可换为 `Camellia sinensis 03` 茶树芽叶特写


## 2026-11-10 首页 Hero 背景清晰度与文字可读性调整

- 分级：A（纯样式调整，未改组件结构、数据与接口）
- 需求来源：用户「可以把模糊度再调低一点，对应的字也调下，防止看不清」
- 变更：
  1. `HeroBackground.vue`：遮罩 `.hero-bg__veil` 由 0.60 / 0.48 / 0.36 下调至 **0.34 / 0.26 / 0.16**，背景照片细节更清楚（此前发灰「模糊」感来自这层白色遮罩，非图片本身）
  2. `HomeView.vue`：新增 `.hero__content::before` 柔和留白光晕（radial-gradient，中心 0.92 → 88% 处透明），只在文字背后提亮，画面四角保持通透
  3. 文字补偿：标题光晕加强（26px 白光 + 6px 近距白描边），副标题不透明度 0.82 → 0.92、光晕同步加强，徽标底色 0.78 → 0.9
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | Vite 编译 | 通过 | `GET /src/views/HomeView.vue`、`/src/components/HeroBackground.vue` 均 200 |
  | 目检 | 未运行（无浏览器截图工具） | 已按对比度推算：文字中心区叠加 92% 米白光晕，标题/副标题为深茶褐色，6 张背景（含太姥山亮天空）均可读 |

- 回滚：还原两处 CSS（veil 三档透明度、`.hero__content::before` 与 text-shadow / opacity / badge 背景）


## 2026-11-10 首页 Hero 遮罩「割裂」修正

- 分级：A（纯样式）
- 反馈：截图显示遮罩呈有明显边界的浅色块，与背景图割裂
- 定位：两个层叠加造成——eil 用 160deg 渐变（透明度沿对角线变化，出现斜向明暗分界）＋上一轮新增的 .hero__content::before 径向光斑（矩形区域内提亮，边缘可见）
- 改动：
  1. HeroBackground.vue：eil 改为**单一平铺** 
gba(250,248,245,0.12)，无方向、无渐变，肉眼不可辨认为独立图层
  2. HomeView.vue：删除 .hero__content::before 光斑；.hero::after 装饰绿斑 display:none（它原本叠在照片之上）
  3. 文字补偿：标题 / 副标题改为贴字白光（2px + 9~10px + 18~22px 三层），副标题不透明度 0.95，保证在清晰照片上仍可读
- 验证：Vite 编译 200；对比度估算——文字色 #2c2c2c 叠 12% 米白后，标题区平均对比度 > 7:1，最深叶丛处由白色贴字光晕兜底
- 回滚：恢复渐变 veil / 光斑 / 装饰绿斑


## 2026-11-10 首页背景第二版：更契合 + 更高清

- 分级：A（静态素材替换 + 文档登记，未改组件与业务）
- 反馈：「背景图换成更契合项目的，图片一定要清晰，原来的有点模糊」
- 根因：上一版输出 2200×1238 / WebP q56–74，在大屏上被 cover 放大；且 6 张中有 2 张题材偏（太姥山岩石、茶叶特写），不属茶园/茶山语境
- 变更（源图全部 ≥4000px，Commons）：

  | 茶类 | 新/沿用 | 来源 | 授权 | 作者 |
  |---|---|---|---|---|
  | 绿茶 | 沿用 | Tea Garden Hangzhou（杭州茶园云雾石径） | CC BY 4.0 | Takashishin |
  | 白茶 | **换新** | White tea hand-picking（白茶手工采摘） | CC BY-SA 4.0 | KZZZ01 |
  | 黄茶 | 沿用 | Xiding Tea Plantation 01（茶山梯田） | CC BY-SA 4.0 | 阿道 |
  | 乌龙茶 | 沿用 | 深山茶园（武夷岩壁＋茶园梯田） | CC BY 3.0 | rheins |
  | 红茶 | **换新** | 在武夷山虎啸岩景观台远望天游峰（武夷云雾） | CC BY-SA 4.0 | Lhy123456 |
  | 黑茶 | 沿用 | 景迈大寨与景迈山（普洱景迈山） | CC BY-SA 4.0 | Zhangmoon618 |

- 输出：统一 **2560×1440 WebP**，质量 79–88，单张 419–885 KB；16:9 裁切；统一色调整形（饱和度 ×0.86、对比 ×1.05、R×1.02 / B×0.97）使六张色调一致偏暖低饱和
- 裁切修正：white 左裁 16% 去掉边缘半截采茶人；oolong 下偏 0.88 保住茶园梯田
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | HTTP | 通过 | 6 张 GET localhost:5173/images/banners/banner-*.webp 均 200；首页 200 |
  | 目检 | 通过 | 拼图核对：均为茶园/茶山实拍，无水印、无半截人物、无黑边；色调统一 |
  | 体积 | 记录 | 6 张合计 4.4 MB（首屏加载当前首张约 0.9 MB）；如需可后续改 1920 宽 + srcset |
  | pytest / itest | 未运行 | 无后端/前端逻辑改动 |

- 遗留：hero 轮播一次加载 6 张，生产建议加 srcset 或仅预载当前+下一张（属组件改造，需另开任务）


## 2026-11-10 将 backend/uploads 纳入版本管理

- 分级：A（仓库配置与静态素材入库，无代码行为变更）
- 背景：交付给他人的仓库缺少 ackend/uploads/ 时，	eas.main_image_url / content_items.cover_image / 	ea_media.image_url 指向的图片全部缺失，页面虽回退到内置 SVG 占位、不产生死链，但图鉴视觉为空
- 同时修正：.gitignore:40 原为 uploads/          # FastAPI 图片上传目录，gitignore 不支持行尾注释，该行从未生效（ackend/uploads/ 一直是未跟踪状态）；本次删除该规则并注明 uploads 纳入版本管理
- 入库内容：159 个文件 / 38.4 MB（jpg 98、webp 59、png 2），即 36 款茶品主图、图片集与 39 条内容封面
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | 暂存核对 | 通过 | git diff --cached --stat = 160 files（159 图 + .gitignore），无 .env、日志、临时文件 |
  | 单文件体积 | 通过 | 最大单文件 < 1 MB，远低于 Gitee 100 MB 限制 |
  | 静态检查 | 通过 | python scripts/check_all.py |

- 后续约定：此后通过后台新增/替换的上传素材会以未跟踪文件出现，需随功能提交一并 git add backend/uploads
- 遗留：仓库体积将持续增长，若素材规模上量，建议迁移 Git LFS（需评估 Gitee LFS 配额）


## 2026-11-11 扩充「茶文化」五大内容板块

- 分级：B（仅内容数据与静态配图，无表结构、API 契约与代码逻辑变更）
- 背景：顶栏「茶文化」下五个板块每类仅 7–8 条，内容单薄；本次补齐到每类约 30 条，并保证每条有配图
- 变更（content_items 数据）：

  | 板块 | 原有 | 新增 | 现计 |
  |---|---|---|---|
  | 茶具茶器 teaware | 8 | 24 | 32 |
  | 茶叶产地 origin | 8 | 25 | 33 |
  | 茶叶文化 culture | 8 | 24 | 32 |
  | 茶叶品牌 brand | 7 | 23 | 30 |
  | 茶叶知识 knowledge | 8 | 25 | 33 |
  | 合计 | 39 | 121 | 160 |

- 新增脚本（scripts/content_expand/）：`data_*.py`（五类条目文案与 meta）、`fetch_and_import.py`（百度图片抓取 + 筛选 + 入库）、`make_montage.py`（配图拼图目检）
- 配图规则：按条目标题关键词检索；剔除价格/批发/礼盒/海报/素材等电商与资讯图；品牌板块只用品类示意与产地风貌，不使用商标、包装与店面实拍
- 目检与修正：五个板块各出拼图逐条核对，替换错图 40 余张（如湄潭茶园换掉带文字海报、横州换茉莉花田、正山堂换桐木关茶园、大益换熟茶汤、茶具清洁换茶垢清洁图）
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | 封面完整性 | 通过 | 160/160 条 cover_image 文件均存在（脚本校验） |
  | 接口 | 通过 | GET /api/v1/contents?type=teaware 返回 HTTP 200 / code 0，items 正常 |
  | 目检 | 通过 | 五个板块拼图核对，均已匹配条目主题；闻香杯沿用近似杯型图 |
  | pytest / vitest | 未运行 | 未改动后端与前端代码，仅数据与静态图 |

- 遗留：①「万里茶道」配图为路线示意图，非实景；②部分产地条目为产区茶园风貌，未精确到村寨；③「看懂茶叶标签与等级」配图为茶叶罐示意，未展示标签细节
- 素材说明：图片来自百度图片检索，仅供个人学习使用，未商用；如需对外发布需逐张核验授权

## 2026-11-11 冲泡参考时间单位统一为「秒」

- 分级：A（仅前台展示文案，无 API 契约、数据结构与业务规则变更）
- 背景：用户反馈详情页「浸泡时间」显示疑似「60年代」。核查结果：数据库 `teas.brew_time` 为 DECIMAL(秒)，井冈翠绿（id=97）实际值 60.0；接口返回 `60.0`，页面原渲染 `${brew_time}s`，全仓库与构建产物均无「年代」文案，未能复现。为避免 `60s` 被浏览器翻译/误读为「60年代」，并按 PRD「浸泡时间 单位：秒」与原型「60秒」统一中文单位
- 变更：
  - `frontend/src/views/TeaDetailView.vue`：浸泡时间 `s` → `秒`
  - `frontend/src/views/HomeView.vue`：随机发现卡 `s` → `秒`
- 数据排查：211 款茶冲泡参数均在合理区间（水温 80–100℃、投茶量 3–8g、浸泡 8–180s，无空值/越界）；全库无把时间写成「年代」的数据；「年代」仅出现在 3 条史料文案（川红 20 世纪 50 年代创制、日照南茶北引始于上世纪六十年代、紫砂壶源于宋代），表述正确
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | npm run lint | 通过 | eslint 无告警 |
  | npm run typecheck | 通过 | vue-tsc 无错误 |
  | npm run test:run | 通过 | 6 文件 / 50 用例全通过 |
  | 浏览器实测 | 通过 | `/teas/97` 冲泡参考显示 85℃ / 3g / 60秒 |
  | 数据库核查 | 通过 | brew_time=60.0；全量参数范围与异常文本扫描无异常 |

- 遗留：PRD/PAGE_SPECS 线框示意图中仍有「3min」示例文案，属文档示意非页面实际显示，未改动

## 2026-11-11 茶文化五大板块正文扩写（160 条）

- 分级：B（内容数据批量更新 + 前台渲染调整；无 API 契约、表结构、权限变更）
- 需求：茶文化详情正文过于简略（原 90–280 字）。经确认：覆盖全部 160 条，每篇 300–500 字、3–5 段、2–3 个小标题
- 变更：
  - 新增 `scripts/content_expand/detail_bodies.py`：160 条详版正文，按「板块编码 + 标题」索引；`## 小标题` 单独成块，块之间空行分隔
  - 新增 `scripts/content_expand/apply_detail_bodies.py`：按 (板块, 标题) 回写 `content_items.body`，支持 `--dry-run`
  - `scripts/content_expand/fetch_and_import.py`：新增条目优先取 `detail_bodies` 正文，避免后续导入退回简版
  - `frontend/src/views/ContentDetailView.vue`：正文按空行切块，`## ` 渲染为 h2 小标题，其余为段落；补 `.detail__subheading` 样式
- 内容口径：保留原条目事实，仅补充常识性背景；不编造精确年代、价格、排名、奖项；品牌条目保持中性客观
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | 结构与字数校验 | 通过 | 160/160 条，长度 380–468 字符；每条 2–3 小标题、3–5 段（脚本断言） |
  | 入库 | 通过 | dry-run 匹配 160 / 未匹配 0；实际更新 160 条 |
  | 数据库复核 | 通过 | 五板块平均 391–403 字符，无空值 |
  | npm run lint / typecheck | 通过 | eslint、vue-tsc 无错误 |
  | npm run test:run | 通过 | 6 文件 / 50 用例 |
  | 浏览器实测 | 通过 | `/contents/origin/3` 显示 3 个小标题与扩写正文，无 `##` 残留 |
  | python scripts/check_all.py | 通过 | 链接 / 常量 / 分层 / 前台 UI / 记录 / 密钥 |

- 遗留：正文格式为内部约定（`## ` 小标题 + 空行分段），后台手工编辑正文时需沿用；`detail_bodies.py` 为详版正文来源，`data_*.py` 仍保留首版简文用于初始导入

## 2026-11-11 首页 hero 背景图更换为高清版

- 分级：A（仅替换静态资源，组件与交互逻辑未改）
- 背景：用户反馈首页背景图不清晰。排查确认原 6 张图虽为 2560×1440，但源图细节偏软，其中 `banner-red.webp` 边缘清晰度最低（edge_std 22.4，其余 56–83）
- 变更：替换 `frontend/public/images/banners/` 下 6 张 `banner-{green,white,yellow,oolong,red,dark}.webp`，统一为 2560×1440、WebP quality 86（545–982KB），分别对应绿茶、白茶、黄茶、乌龙茶、红茶、黑茶主题；`HeroBackground.vue` 的 `webp → jpg → svg` 加载顺序与轮播逻辑不变
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | 浏览器实测 | 通过 | 首页 6 张背景均加载 `.webp`，`naturalWidth=2560 / naturalHeight=1440`；hero 显示照片背景而非渐变/占位 |
  | 图片规格 | 通过 | 全部 2560×1440；`banner-red` 清晰度指标由 22.4 提升至 71.8 |
  | python scripts/check_all.py | 通过 | 273 条相对链接、常量、五层、前台 UI、记录、密钥全部通过 |

- 遗留：新图为 AI 生成的实景风格示意图，非真实产地实拍；后续若要换成实拍图，保持同名 `.webp`（2560×1440）覆盖即可，无需改代码

## 2026-11-11 首页背景图二次更换（去雾提锐）

- 分级：A（仅替换静态资源）
- 背景：用户反馈上一版背景仍偏模糊、发灰。原因是原图雾气重、对比度低（白茶图边缘清晰度仅 31.5）
- 变更：重新生成并替换 6 张 `frontend/public/images/banners/banner-*.webp`，统一 2560×1440 WebP quality 86（415–1289KB）；构图改为晴日高对比、全画面锐利、无雾无景深虚化；白茶版改为银针茶园全景
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | 图片规格 | 通过 | 6 张均 2560×1440；边缘清晰度 68.0–84.3（上一版 31.5–72.5） |
  | 浏览器实测 | 通过 | 首页 6 张均加载 `.webp`，`naturalWidth=2560`，画面清晰无灰雾 |
  | 后台轮播 | 通过 | 组件与 7 秒轮播逻辑未改，当前 active 正常切换 |

- 遗留：仍为 AI 生成示意图，非真实产地实拍；需实拍时同名覆盖即可

## 2026-11-11 首页白茶 / 乌龙背景图按主题重制

- 分级：A（仅替换 2 张静态资源）
- 背景：用户指出白茶与乌龙两张背景与站点「清新水墨」主题不够贴合。原白茶图为白色花穗状茶园、乌龙图为高饱和蓝天峡谷，色调偏艳
- 变更：
  - `banner-white.webp`：银针白茶近景茶园，前景白毫茶芽清晰，远景薄雾，暖绿与米白基调，上方留出浅色负空间
  - `banner-oolong.webp`：武夷岩茶丹霞梯田，暖灰低饱和，茶垄清晰、远山轻雾，上方天空留白
  - 均 2560×1440、WebP quality 90，并做轻度 USM 锐化（白茶 310KB / 乌龙 724KB）；其余 4 张与轮播逻辑未动
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | 图片规格 | 通过 | 两张均 2560×1440，白茶 310KB、乌龙 724KB |
  | 浏览器实测 | 通过 | 两张 `naturalWidth=2560 / naturalHeight=1440`，加载成功；当前 active 为 `banner-white.webp`，画面清晰 |
  | 主题一致性 | 通过 | 低饱和暖调 + 上方留白，贴合「清新水墨」且不压标题文字 |

- 遗留：AI 生成示意图，非实拍；如需实拍同名覆盖即可

## 2026-11-11 文档与实现基线同步（P0）

- 分级：A（纯文档同步；无业务规则、接口行为、表结构、权限变更）
- 背景：全局体检发现权威文档滞后于已实现代码：README 端点/用例/测试数均为旧值；AGENTS 仍声明 S1–S17 不开发；API_CONTRACT 缺整个内容板块章节；openapi.yaml 缺已实现的 `GET /admin/contents/{item_id}`
- 变更：
  - `docs/api/API_CONTRACT.md`：新增 §4.9 内容板块（8 个端点：`/content-types`、`/contents`、`/contents/{item_id}`、`/admin/contents` 增删改查）；§1.1 路由分组表新增 `/api/v1/contents`；§3 接口总览由 46 条补齐为 56 条（补 `/me/avatar` POST/PUT 及内容板块 8 条）；版本 v1.6 → v1.7
  - `docs/api/openapi.yaml`：补 `GET /admin/contents/{item_id}`（`adminGetContent`），operations 55 → 56
  - `README.md`：端点 29 → 56、用例 60 → 89、pytest 106 → 170、Vitest 30 → 50、表 7 → 13、安全项 32 → 35、链接 205 → 273、文件 153 → 236；Alembic 说明改为 0001–0010
  - `AGENTS.md`：阶段改为「MVP + 第二阶段扩展已完成，S1–S17 已实现并冻结，X1–X13 不开发」；业务端点 55 → 56
  - `scripts/check_constants.py`、`docs/api/README.md`：常量与引用同步 55 → 56
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | 文档与运行时端点对比 | 通过 | 运行时 57 operations（56 业务 + health），openapi 补齐后 56 业务；无缺漏 |
  | python scripts/check_all.py | 通过 | 273 链接、常量 56/89/35/13、五层 0 违规、前台 UI、记录、密钥全部通过 |
  | pytest / Vitest | 未运行 | 本次零代码改动，沿用当日已执行的 170 passed / 50 passed 基线 |

- 遗留：openapi 部分 `summary` 仍引用旧章节编号（§4.2.10/§4.6.12），不影响契约语义，后续随接口改动一并修正；P1 功能项待用户确认后实施

## 2026-11-11 P1 功能补全（6 项）

- 分级：B/C（清单导出、浏览历史、投稿标记为前端功能；内容搜索、修改密码、操作日志涉及接口/表结构，经用户确认后实施）
- 需求：补齐体检发现的 6 项缺口；用户确认改密采用 `users.session_version` 吊销旧会话、投稿通知采用轻量本地标记
- 变更：
  - 清单一键导出：`frontend/src/utils/export.ts` + 我的清单页，CSV（UTF-8 BOM、RFC 4180 转义）与 JSON
  - 浏览历史：`frontend/src/utils/viewHistory.ts`（localStorage、去重、上限 50）+ 详情页写入 + 个人中心展示/清空
  - 内容搜索：`GET /contents` 新增 `keyword`（≤100，title/summary，复用 `escape_like`），前端 300ms 防抖搜索框
  - 修改密码：`PUT /auth/password`；`users.session_version` 列 + Alembic `0011_user_session_version`；改密递增版本并清 Cookie，旧会话立即 40100；个人中心「账号安全」表单
  - 操作日志：`GET /admin/operation-logs`（分页/动作/目标类型/管理员/日期筛选）+ 后台「操作日志」页
  - 投稿结果标记：`frontend/src/utils/contributionRead.ts` + 我的投稿页统计与新结果提示（localStorage 已读）
  - 文档同步：API_CONTRACT v1.9（业务端点 58）、openapi.yaml（58 operations）、DATA_MODEL、SECURITY S-06/S-08/S-10、MODULE_DESIGN、TEST_PLAN v1.6（94 条）、README/AGENTS/check_constants
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | python -m ruff check app tests | 通过 | All checks passed |
  | pytest | 通过 | 184 passed（新增内容搜索 5、改密 4、操作日志 5） |
  | npm run lint / typecheck / format:check | 通过 | 同时修复 8 个历史文件的 Prettier 格式基线 |
  | npm run test:run | 通过 | 9 文件 / 73 用例（新增导出 8、浏览历史 7、投稿标记 8） |
  | python scripts/check_all.py | 通过 | 273 链接、常量 58/94/35/13、五层 0 违规、密钥 0 |
  | Alembic | 通过 | 测试库与开发库均升级至 `0011_user_session_version` |

- 遗留：
  - `operation_logs` 表无 IP 列，操作日志的 `ip_address` 恒为 null，已在契约标注预留；真实采集需另开 C 类表结构变更
  - 浏览历史与投稿已读标记仅存本机 localStorage，不跨设备
  - 内容搜索仅匹配标题与摘要，不含正文
  - 本次改动未提交 git

## 2026-11-11 详情页新增「去淘宝搜索」购买入口

- 任务编号：TASK-20261111-01
- 分级：C
- 判定理由：用户明确要求新增功能，且触及 PRD §2.3 X10「茶叶电商、交易、支付不在产品契约内」边界；经用户确认后按外链导流实现
- 边界确认：不改数据库、不改 API 契约、不改后端；仅新增前端展示与外链 → 无契约变更
- 用户确认记录：2026-11-11 对话确认 —— 方案 A（前端按茶名拼淘宝搜索 URL，零后端/零数据库改动）；位置后续两次调整，最终定于茶名右侧
- 变更：
  - 新增 `frontend/src/utils/purchase.ts`：`buildTaobaoSearchUrl(name)`，trim + 50 字截断 + `encodeURIComponent`，空茶名返回 null
  - 新增 `frontend/src/utils/purchase.spec.ts`：5 条用例（中文、特殊字符、首尾空白、空值、超长截断）
  - `frontend/src/views/TeaDetailView.vue`：详情页茶名右侧（与标题同行、右对齐）新增购买入口，`target="_blank" rel="noopener noreferrer"`，并在按钮下方标注「跳转第三方平台，本站不参与交易」；仅 ready 且茶名非空时渲染；样式全部引用 CSS 变量。2026-11-11 追加调整：位置经两次用户指定，由「主图下方通栏」→「产地下方」→ 最终「茶名右侧」，按钮文案为「去淘宝搜索同款」
  - `docs/product/PRD.md`：v1.1 → v1.2；§2.3 X13 后新增 2026-11-11 决策注记，明确该入口不构成 X10 电商能力
  - `docs/design/PAGE_SPECS.md`：§5.1 新增「购买入口」规格行
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | npm run lint | 通过 | eslint 无告警 |
  | npm run typecheck | 通过 | vue-tsc 无错误 |
  | npm run test:run | 通过 | 10 文件 / 78 用例（新增 purchase 5 条） |
  | npm run format:check | 通过 | Prettier 全部通过 |
  | python scripts/check_all.py | 通过 | 284 链接、常量 58/94/35/13、五层 0 违规、前台 UI 0、密钥 0 |
  | 手工浏览器冒烟 | 通过 | 最终位置复验 `/teas/212`：按钮与茶名同行、位于标题右侧，免责提示在按钮下方；产地与冲泡参考正常，无重复入口；点击后新标签页地址为 `https://s.taobao.com/search?q=%E7%BC%99%E4%BA%91%E9%BB%84%E8%8C%B6`（淘宝要求登录） |

- 遗留：
  - 淘宝搜索页可能要求登录或滑块验证，无法保证直达商品结果；移动端可能提示下载 App
  - 仅按茶名关键词搜索，无法锁定具体商品、品牌或规格

## 2026-11-12 冲泡参考升级为分步冲泡教程

- 任务编号：TASK-20261112-01
- 分级：C
- 判定理由：新增第 14 张表、1 个 Alembic 迁移、2 个管理员端点（业务端点 58 → 60），属数据库结构与 API 契约变更
- 用户确认记录：2026-11-12 对话确认 —— 决策见 [ADR-0005](../docs/development/ADR/ADR-0005-tea-brewing-guide.md)；已确认「每款茶单独录入」「速查条 + 步骤默认全部收起、点击展开」（后续微调：按钮加箭头、折叠与滚动回位同步动画）「存量茶自动生成草稿」「自由步骤 + 模板填充」「教程录入内嵌茶品编辑页」
- 变更：
  - 后端：新增 `models/tea.py::TeaBrewingGuide`（1:1，`steps` JSON，3–8 步）与 `Tea.brewing_guide` 关系；Alembic `0012_brewing_guides`；`database/init.sql` 第 14 张表
  - 后端：`schemas/tea.py` 新增 `BrewingStep/BrewingGuide`，`TeaDetail` 增加 `brewing_guide`；`repositories/tea_repo.py` joinedload；`repositories/admin_repo.py` 新增教程 CRUD
  - 后端：`services/admin.py` / `routers/admin.py` 新增 `PUT/DELETE /api/v1/admin/teas/{tea_id}/brewing-guide`，`operation_logs` 记 `update_brewing_guide` / `delete_brewing_guide`；DELETE 幂等，未删除时 `deleted=false`
  - 后端：新增幂等脚本 `app/scripts/seed_brewing_guides.py`，按茶类模板 + 本茶水温/投茶量/时间生成 6 步草稿，只补无教程茶品，支持 `--dry-run`
  - 前端：`types/index.ts` 增加 `BrewingGuide` 等类型；`TeaDetailView.vue` 教程卡（速查三格默认可见，步骤与注意事项默认收起；按钮右侧下箭头随展开翻转；折叠为 320ms `grid-template-rows` 过渡，收起时用同 320ms `easeInOutCubic` 逐帧补偿滚动回到展开前位置，遵循 `prefers-reduced-motion`），无教程时回退原三格卡
  - 前端：`utils/brewing.ts::buildBrewingDraft` 纯函数；`AdminTeaEdit.vue` 内嵌教程录入区块（总览/步骤上移下移删除/添加步骤/按茶类生成草稿/删除教程/当前 N/8 步）
  - 文档：API_CONTRACT v1.11（新增 §4.6.13/§4.6.14）、openapi.yaml（60 operations）、DATA_MODEL v1.7、MODULE_DESIGN、ARCHITECTURE 数据层图示、PAGE_SPECS v2.1、PRD v1.3、TEST_PLAN v1.7（100 条）、docs/api/README、AGENTS、`scripts/check_constants.py` 基线（60/100/35/14）
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | python -m ruff check / format --check | 通过 | 无告警 |
  | pytest | 通过 | **190 passed，1 warning**（第三方 httpx/starlette 提示）；新增 `tests/test_brewing_guides.py` 6 条 |
  | npm run lint / typecheck / format:check | 通过 | 无错误 |
  | npm run test:run | 通过 | 11 文件 / **82 用例**（新增 `brewing.spec.ts` 4 条） |
  | python scripts/check_all.py | 通过 | 299 链接、常量 60/100/35/14、五层 0 违规、前台 UI 0、密钥 0 |
  | Alembic | 通过 | 开发库与测试库 `tea_guide_test` 均升级至 `0012_brewing_guides` |
  | 种子脚本 | 通过 | `--dry-run` 待生成 211 → 实际生成 211 款草稿；再次 `--dry-run` 为 0（幂等） |
  | 浏览器冒烟（前台） | 通过 | `/teas/212` 默认仅显示标题、简介与速查三格；按钮右侧下箭头展开后翻转朝上并显示 1–6 步与注意事项；收起时折叠高度（grid 行高 320ms）与滚动回位（同 320ms easeInOutCubic 逐帧补偿）同步执行，采样呈先加速后减速的连续缓变（1201→618，8 个中间值），最终 scrollY 回 618（Y1=618，偏差 0px），箭头恢复朝下；无白屏 |
  | 浏览器冒烟（后台） | 通过 | `/admin/teas/212/edit` 教程区块显示 6 张步骤卡、「当前 6 / 8 步」与「添加步骤」「按茶类生成草稿」按钮；仅只读检查，未保存 |

- 契约 / 数据 / 安全影响：新增 2 个管理员端点与 1 张表；管理员门禁沿用 S-27/S-28，无新增安全项；茶品详情仅新增可选字段，旧客户端不受影响。
- 遗留：
  - 草稿内容为茶类通用手法，个别名茶仍需管理员逐款润色（ADR-0005 已登记）
  - 步骤 JSON 的字段约束依赖 Pydantic 与前端校验，数据库层无 CHECK（MySQL 5.7 限制）
  - 收起动画依赖 `grid-template-rows` 过渡，需现代浏览器（Chrome 107+ / Safari 16+）；不支持时退化为瞬时折叠，不影响功能
- 回滚方式：停用前端教程卡与后台区块后，回退代码；数据库执行 `alembic downgrade 0011_user_session_version` 删除 `tea_brewing_guides`（不影响 `teas` 与 `tea_tips`）。

## 2026-11-12 前台视觉动效优化（ReactBits 灵感四件套）

- 任务编号：TASK-20261112-02
- 分级：B
- 判定理由：仅改前台展示层（组件样式与动效），不改 API 契约、数据库、业务规则与路由；零新增第三方依赖
- 用户确认记录：2026-11-12 对话确认 —— 采用「推荐四件套」（纸纹噪点 / 标题模糊入场 / 茶卡柔光 / 数字滚动），动效尺度「适中有层次」；明确要求不提交、不推送，等待后续指令
- 变更：
  - 新增 `frontend/src/components/effects/PaperTexture.vue`：静态 SVG fractalNoise 纸纹层，`opacity` 取 `--paper-noise-opacity`（0.035），`pointer-events: none`，无 rAF 重绘
  - 新增 `frontend/src/components/effects/RevealText.vue`：中文逐字 / 英文逐词 `blur → clear` 入场，IntersectionObserver 只播一次，`prefers-reduced-motion` 下直接呈现
  - 新增 `frontend/src/components/effects/SpotlightCard.vue`：pointermove 写入 CSS 变量并经 rAF 合并，暖白柔光以 soft-light 叠加；可选 ≤4° 3D 倾斜；触摸设备与减少动效自动降级
  - 新增 `frontend/src/components/effects/CountUp.vue`：进入视口后 rAF 缓动计数，值变化时重播，减少动效直显终值
  - `frontend/src/style.css`：新增 §6 动效与质感 token（`--motion-ease`、`--motion-duration-*`、`--paper-noise-opacity`、`--spotlight-color`）
  - `frontend/src/App.vue`：按当前路由挂载纸纹层，`/admin` 下不挂载
  - `frontend/src/views/HomeView.vue`：hero 主副标题与三大区块标题接入 RevealText；六类卡、小贴士、随机发现卡接入 SpotlightCard（随机卡开启 4° 倾斜）；六类计数接入 CountUp；补充 host wrapper 布局样式
  - `frontend/src/components/TeaCard.vue`：外层改用 SpotlightCard，收藏按钮绝对定位与原有 hover 行为保持不变
  - `frontend/src/views/TeaDetailView.vue`：茶名接入 RevealText，收藏数接入 CountUp，移除冗余的 `favoriteText` 计算
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | npm run typecheck | 通过 | vue-tsc 无错误 |
  | npm run lint | 通过 | 无告警 |
  | npm run format:check | 通过 | Prettier 全部通过（HomeView 已格式化） |
  | npm run test:run | 通过 | 11 文件 / 82 用例，无回归 |
  | npm run build | 通过 | 生产构建成功 |
  | python scripts/check_frontend.py | 通过 | 前台 UI 终检：历史遗留 0 项，无 Element Plus、无硬编码 HEX |
  | 浏览器冒烟（首页） | 通过 | 约 600px 视口：hero 标题 blur 动画结束可读（`filter: none`）、六类卡 6 张对齐、纸纹层 `opacity 0.035` 生效、`spotlight-card__glow` 节点存在、无白屏；后端在线时六类计数正常显示 |

- 未验证 / 遗留：
  - 桌面 ≥1024px 六列布局未做实机截图复验（网格列数未改动，仅新增 wrapper 层）
  - 详情页与后台页未做浏览器复验（后台已按路由排除纸纹层）
  - 本次未提交、未推送，等待用户指令
- 回滚方式：回退上述前端文件即可，无数据与契约影响

## 2026-11-12 布局优化：内容瀑布流 + 详情瓦片聚焦图集（已于同日回退，代码未保留）

- 任务编号：TASK-20261112-03
- 分级：B
- 判定理由：仅改前台展示层布局（两个视图的模板结构与 CSS），不改 API 契约、数据库、业务规则；沿用 `tea.image_set` 既有字段，无新增依赖
- 用户确认记录：2026-11-12 对话确认 —— 在四个布局方案中先看预览图，最终选定「方案 B 瓦片聚焦」，并确认「两个页面都用」（茶详情图集 + 内容列表）
- 变更：
  - `frontend/src/views/ContentListView.vue`：内容列表由固定比例网格改为 CSS 多列瀑布流（`columns: 3` + `column-gap: 24px`，卡片 `break-inside: avoid` + `margin-bottom: 24px`）；卡片封面改自适应高度（`height: auto; max-height: 320px; object-fit: cover`），无封面时保留 180px 占位块；断点 1024px 起 3 列、768–1023px 2 列、<768px 1 列
  - `frontend/src/views/TeaDetailView.vue`：≥2 张图片时头部改为「瓦片聚焦图集」——3 列 Grid（`grid-auto-rows: 96px`、`gap: 8px`、`grid-auto-flow: dense`），当前瓦片 `grid-column/row: span 2` 放大到 2×2；由 `featuredIndex` 状态驱动，点击或键盘聚焦切换，避免 hover 改 span 造成的元素跳位与页面高度抖动；单图/无图回退原 4:3 主图与占位块；移除 `activeImage` / `displayImage` 与横向缩略图条，`hasImage` 改为基于 `tea.main_image_url`；移动端 2 列，`prefers-reduced-motion` 下关闭缩放与过渡
  - 文档：`docs/design/PAGE_SPECS.md` §5.1 头部区块行同步为瓦片聚焦图集规格
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | npm run typecheck | 通过 | vue-tsc 无错误 |
  | npm run lint | 通过 | 无告警 |
  | npm run format:check / prettier --check | 通过 | 两个视图文件格式合规 |
  | npm run test:run | 通过 | 11 文件 / 82 用例，无回归 |
  | npm run build | 通过 | 生产构建成功（仅有既存的 element-plus chunk >500kB 提示） |
  | python scripts/check_frontend.py | 通过 | 历史遗留 0 项，无 Element Plus、无硬编码 HEX |
  | 浏览器冒烟（`/teas/1`） | 通过 | 599px 视口：4 张瓦片渲染，初始第 1 张为 2×2 放大块（552×176），点击第 2 张后放大块随之切换；无白屏、无布局断裂 |
  | 浏览器冒烟（`/contents/teaware`） | 通过 | 599px 视口为 1 列，12 张卡片正常渲染、无重叠/截断；模拟 3 列时卡片高度 246–385px 呈瀑布流 |

- 未验证 / 遗留：
  - 环境浏览器视口固定约 599px，桌面 3 列瀑布流与 3 列瓦片网格仅通过 CSS 与模拟宽度验证，未做 ≥1024px 实机截图
  - 种子数据中仅茶品 1（3 张图集）触发多图分支，其余茶品为单图，单图回退分支已随机抽查
  - 本次未提交、未推送，等待用户指令

**回退记录（2026-11-12，用户要求「回退吧，不要这个改动」）**

- 已回退：`frontend/src/views/ContentListView.vue`、`docs/design/PAGE_SPECS.md` 用 `git checkout` 还原至提交版本（内容零差异，仅按 Prettier 规范保留 LF）；`frontend/src/views/TeaDetailView.vue` 手工还原图集部分（恢复 `activeImage` / `displayImage` 与横向缩略图条、删除 `featuredIndex` 与 `.detail-tiles` 样式），同文件内 ReactBits 四件套改动保留
- 回退后复测：typecheck / lint / format:check / test:run（82 用例）/ build / `python scripts/check_frontend.py` 全部通过
- 影响：前台布局回到改造前；无数据、契约、依赖变化

## 2026-11-12 前端视觉优化 P0：统计带 + 卡片去框化 + 筛选工具条

- 任务编号：TASK-20261112-04
- 分级：B
- 判定理由：仅改前台展示层（组件结构、CSS、列表页筛选面板的展开/收起交互），不改 API 契约、数据库、业务规则与权限；筛选逻辑与 URL 同步完全沿用原实现，无新增依赖
- 需求来源：用户对照 Meoo 创意社区模板（寻味湖州茶事、茶饮口味测评）与同类站（茶库·茶品图鉴、Tea Community、Teaco 复盘）提出优化，确认执行 P0 三项 A+B+C
- 变更：
  - `frontend/src/components/TeaCard.vue`：卡片去框化 —— 图片独立 `radius-lg` 圆角容器，信息区去掉白底与边框，改为两行（茶名 + `茶类色圆点 · 产地 · ♡ 收藏数`）；hover 改为图片 `scale(1.04)` + 茶名转 `--color-primary`，移除背景/边框/阴影变化；紧凑模式使用 `--text-body` / `--text-caption`；`prefers-reduced-motion` 下关闭过渡
  - `frontend/src/views/HomeView.vue`：Hero 下方新增统计带（已收录茶品数 / 六大茶类 / 覆盖产地数），数字使用既有 `CountUp`；数据取自 `teaStore.categories` 汇总与 `fetchOrigins()`，未新增接口；移动端隐藏分隔线
  - `frontend/src/views/TeaListView.vue`：筛选区由「面包屑 → 5 组筛选 → 已选条 → 排序栏」改为单行工具条（茶类 chips 常显 + 「筛选」按钮带高级条件数量角标 + 排序下拉），产地 / 季节 / 发酵 / 价格 / 组合方式折叠进 `filter-panel`，默认收起、命中高级条件时自动展开；原排序栏收敛为一行结果数；骨架屏同步去框化
  - 文档：`docs/design/DESIGN_SYSTEM.md` §4.3 列表页卡片、§4.6 筛选面板；`docs/design/PAGE_SPECS.md` P1 统计带、P2 筛选工具条 / 结果数 / 卡片网格
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | npm run typecheck | 通过 | vue-tsc 无错误 |
  | npm run lint | 通过 | 无告警 |
  | npm run format:check | 通过 | Prettier 全部合规 |
  | npm run test:run | 通过 | 11 文件 / 82 用例，无回归 |
  | npm run build | 通过 | 生产构建成功（仅既存 element-plus chunk >500kB 提示） |
  | python scripts/check_frontend.py | 通过 | 历史遗留 0 项，无硬编码 HEX |
  | 浏览器冒烟（`/`） | 通过 | 统计带渲染 `211 款茶品已收录 / 6 大茶类体系 / 42 个产地覆盖`；599px 视口无溢出 |
  | 浏览器冒烟（`/teas`） | 通过 | 工具条显示「筛选 / 最新上架」；面板默认 `display:none`、`aria-expanded=false`，点击后 `display:flex`、`aria-expanded=true`、含 5 个筛选分组；卡片元信息为 `黄茶 · 浙江 丽水 缙云 · ♡ 1,444` |

- 未验证 / 遗留：
  - 环境浏览器视口固定约 599px，桌面 ≥1024px 的三列网格与工具条单行布局仅通过 CSS 推断，未做实机截图复验
  - 收藏按钮点击与 Toast 未逐项复测（逻辑未改动，仅容器层级随去框化调整）
  - 本次未提交、未推送，等待用户指令
- 回滚方式：回退 `TeaCard.vue` / `HomeView.vue` / `TeaListView.vue` 与两份文档即可，无数据与契约影响

## 2026-11-12 前端视觉优化 P1：首页引导入口 + 茶类卡升级

- 任务编号：TASK-20261112-05
- 分级：B
- 判定理由：首页信息架构增加一块引导区（不改路由、不改接口、不改筛选逻辑，仅复用既有查询参数），茶类卡为纯视觉替换
- 变更：
  - `frontend/src/views/HomeView.vue`
    - 新增「引导入口」区块：3 张 guide-card（序号 + 意图标题 + 一行说明 + hover 箭头），位于统计带与六大茶类之间
      - 新手入门 → `?fermentation=不发酵,微发酵`
      - `{当季}正当时` → `?season={当季}`，当季由当前月份推导（3-5 春茶 / 6-8 夏茶 / 9-11 秋茶 / 12-2 冬茶）
      - 六大茶类对比 → `/compare`
    - 六大茶类卡升级：emoji 图标替换为 40px 茶类色圆形色块（`--cat-color` + 内描边避免白茶色过浅），新增英文小标（GREEN TEA / WHITE TEA / YELLOW TEA / BLACK TEA / OOLONG TEA / DARK TEA），数量保留 CountUp
  - 文档：`docs/design/PAGE_SPECS.md` P1 区块列表新增「引导入口」行，更新「六大茶类入口」行
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | npm run typecheck | 通过 | 无错误 |
  | npm run lint | 通过 | 无告警 |
  | npm run format:check | 通过 | 合规 |
  | npm run test:run | 通过 | 82 用例无回归 |
  | npm run build | 通过 | 构建成功 |
  | python scripts/check_frontend.py | 通过 | 无硬编码 HEX（色块走 `--cat-color`） |
  | 浏览器冒烟（`/`） | 通过 | 三张 guide-card 渲染正常，href 分别为 `?fermentation=不发酵,微发酵`、`?season=秋茶`、`/compare`；茶类卡显示 `绿茶 GREEN TEA 66 款已收录` 等（CountUp 需滚入视口后触发，属既有行为） |
  | 浏览器冒烟（`/teas?fermentation=不发酵,微发酵`） | 通过 | 面板自动展开，角标 `2`，两个 chip 命中，结果 100 款 |
  | 浏览器冒烟（`/teas?season=秋茶`） | 通过 | 面板自动展开，角标 `1`，结果 3 款 |

- 观察 / 遗留：
  - 种子数据中秋茶仅 3 款，`秋茶正当时` 入口的落地面偏空；如需更好的第一印象，可在补充数据后维持，或将该入口改为春茶 / 产地维度（需用户确认）
  - 桌面 ≥1024px 仅做 CSS 推断，未实机截图复验
  - 本次未提交、未推送
- 回滚方式：回退 `HomeView.vue` 与 `PAGE_SPECS.md` 对应两行即可

## 2026-11-12 首页搜索入口去重

- 任务编号：TASK-20261112-06
- 分级：A
- 判定理由：纯展示层调整，无契约、数据、路由、业务规则变化
- 问题：首页在 ≥768px 下同时出现页头搜索框与 Hero 搜索框，重复且有歧义
- 变更：
  - `frontend/src/views/HomeView.vue`：`@media (min-width: 768px)` 下隐藏 `.hero__search`
  - 保留策略：≥768px 只用页头搜索框；<768px 页头搜索本身被隐藏（`AppHeader` `max-width:767px` 规则），因此 Hero 搜索保留，保证移动端始终有搜索入口
  - 文档：`docs/design/PAGE_SPECS.md` P1 Hero 行补充显示条件
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | npm run lint | 通过 | 无告警 |
  | npm run format:check | 通过 | 合规 |
  | npm run build | 通过 | 构建成功 |
  | 浏览器冒烟（599px） | 通过 | 实测 `window.innerWidth=599`：`.app-header__search` 计算样式 `display:none` 且不可见，`.hero__search` `display:block` 且可见 —— 可见搜索入口仅 1 个 |

- 未验证：≥768px 下的隐藏效果未做桌面视口实机截图（当前浏览器视图宽度固定 599px，无视口调整能力）；该分支仅由 `@media (min-width: 768px)` 规则推断，与 `<768px` 分支互斥、无断点缝隙
- 回滚方式：删除 `@media (min-width: 768px) { .hero__search { display: none } }` 即可

## 2026-11-12 首页 Hero 副标题可读性提升

- 任务编号：TASK-20261112-07
- 分级：A
- 判定理由：纯展示层调整（单文件 CSS），无契约、数据、路由、业务规则与组件结构变化
- 需求来源：用户确认「Hero 文字对比度」为下一项优化；同轮确认「秋茶正当时」入口**保持现状**
- 方案取舍：
  - 原提议为「Hero 底部加渐变蒙层」，**放弃**：`build-log 2026-11-10「首页 Hero 遮罩割裂修正」` 已记录渐变 veil 与径向光斑都会形成肉眼可辨的图层边界（斜向明暗分界 / 矩形提亮边），属已否决方案，不得重试
  - 改为纯文字层增强，不新增任何覆盖图层，从而不产生新的分界风险
- 变更：`frontend/src/views/HomeView.vue` `.hero__subtitle`
  - `opacity: 0.95 → 1`：半透明会让深色字透出背景照片、整行"灰化"
  - `font-weight: 400 → 500`：移动端副标题降为 `--text-body` 后笔画偏细
  - 新增近距实心光晕 `0 0 4px rgba(250,248,245,0.95)`，原有 `9px / 18px` 远距光晕保留用于深色背景兜底
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | npm run lint | 通过 | 无告警 |
  | npm run format:check | 通过 | 合规（`prettier --write` 后复跑） |
  | npm run typecheck | 通过 | 无类型错误 |
  | 浏览器冒烟（599px） | 通过 | 截图目检：副标题笔画由发灰变为实心，压在茶园/天空交界处仍可读 |
  | 6 张背景亮度采样 | 已测 | 文字带平均亮度 green 123 / white 133 / yellow 126 / oolong 128 / red 112 / dark 108（0–255），最暗为 `banner-dark` |

- 未验证：未在 ≥768px 桌面视口实机查看（当前浏览器视图宽度固定 599px）；6 张背景仅做了亮度采样，未逐张截图目检最深色背景下的实际观感
- 回滚方式：还原 `.hero__subtitle` 的 `opacity` / `font-weight` / `text-shadow` 三条声明

## 2026-11-12 借鉴三个参考站点优化首页排版

- 任务编号：TASK-20261112-08
- 分级：A
- 判定理由：纯展示层（模板结构 + 局部 CSS），无契约、数据、路由、业务规则变化
- 参考来源（用户指定）：
  - `meoo.com/explore/61613`（兴国红色文旅）：深色压边 Hero + 双行大标题、第二行落强调色
  - `meoo.com/explore/452020`（雨未停—苍苔遗闻）：大衬线标题 + 宽字距英文 + `标签/值` 规格行 + 发丝分割线
  - `meoo.com/explore/223214`（地质品牌 Hero 页）：居中对称排版，kicker 两侧发丝线 + 衬线主标题 + 细分隔
- 落地取舍：只借鉴**排版语言**，不搬深色/沉浸式场景（与本项目「清新水墨 × 暖米白」冲突），也不重试 `2026-11-10` 已被否决的渐变遮罩
- 变更（均在 `frontend/src/views/HomeView.vue`）：
  1. Hero 主标题拆为双行：`一杯茶的` / `千种风味`，第二行 `.hero__title-accent` 落 `--color-primary-dark`；整体仍为单个 `h1`
  2. 新增 `.section-kicker`：宽字距英文小标（0.24em、uppercase、`--text-caption`），居中区块两侧 32px 发丝线
  3. 区块标题去 emoji：「🔥 热门推荐」→ `POPULAR TEAS` + 热门推荐；「📖 茶知识 · 小贴士」→ `TEA NOTES` + 茶知识 · 小贴士
  4. `.section-header` 由 `align-items: baseline` 改为 `flex-end`，新增 `.section-header__main` 纵向堆叠 kicker 与标题
- 文档同步：`PAGE_SPECS.md` P1 Hero 行改为双行标题 + 新增区块标题规范说明；`DESIGN_SYSTEM.md` 新增 §4.7 区块标题、§4.8 双行主标题
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | npm run lint | 通过 | 无告警 |
  | npm run format:check | 通过 | 合规 |
  | npm run typecheck | 通过 | 无类型错误 |
  | npm run build | 通过 | 成功，仅既存 element-plus chunk >500kB 提示 |
  | 浏览器冒烟（599px） | 通过 | 实测 `.hero__title` 子元素 2 个、第二行计算色 `rgb(107,87,64)`；`SIX CATEGORIES` kicker 伪元素宽 32px；`POPULAR TEAS` 与「热门推荐」同时渲染、动作链接右对齐 |

- 未验证：≥768px 桌面视口未实机查看（浏览器视图宽度固定 599px）；未做轮播切换后其他 5 张背景下的双行标题对比度目检
- 可回滚：还原 `HomeView.vue` 的三处模板与 `.section-kicker` / `.hero__title-accent` / `.section-header__main` 样式块

## 2026-11-12 首页沉浸式首屏（Hero Scene）

- 任务编号：TASK-20261112-09
- 分级：B（用户明确要求，方案当场说明后实施）
- 判定理由：涉及首页首屏结构与页头透明/实底切换，视觉行为变化较大；不改契约、数据、路由与业务规则
- 参考来源：`meoo.com/explore/61613`（深色压边 + 大标题）、`meoo.com/explore/223214`（居中对称 + kicker）、`meoo.com/explore/452020`（大衬线 + 宽字距英文）
- 与历史否决项的区分（重要）：
  - `2026-11-10` 否决的是"低透明度斜向渐变 veil + 矩形径向光斑"，问题是**边界肉眼可见**
  - 本次为**竖向、按高度分段的暗色压边**（顶部 0.62 / 中段 0.18 / 72% 0.52 / 底部 0.86），承担明确的"页头可读 + 标题托底"职责，中段主动留亮保持照片清晰；599px 截图目检无可见分界带
- 变更：
  - `frontend/src/views/HomeView.vue`
    - `.hero` 改为满屏（`min-height: max(560px, calc(100vh - 64px))`）、flex 居中、背景色 `--color-bg-hero`
    - 新增 `.hero__bg-layer`（包住 `HeroBackground`，上探 20% 供视差）与 `.hero__scrim`（暗色压边层）
    - `.hero__badge`（白色胶囊 + 🍵）替换为 `.hero__kicker`（两侧 28px 发丝线的宽字距小标）
    - 标题改白字 + 暗色投影，第二行 `--color-tea-yellow`；副标题改 `rgba(255,255,255,0.9)` + 暗色投影
    - 新增 `.hero__cue`「向下探索」+ 呼吸竖线
    - 新增滚动视差：`requestAnimationFrame` 直改 style（不触发响应式重渲染），背景 `scroll × 0.28`、内容 `scroll × -0.06` 且按 `scroll/360` 淡出、提示按 `scroll/160` 淡出；`prefers-reduced-motion` 下整体不启动
    - `.home-page` 去掉 `padding-top`（Hero 顶到视口顶部），移动端同步移除 56px 顶距
  - `frontend/src/components/AppHeader.vue`
    - 新增 `overHero` 态：`route.name === 'home'` 且 `scrollY < hero 高度 - 80` 时加 `.app-header--over-hero`（透明背景、无分隔线、文字与搜索框转白），滚过 Hero 自动转纯白；`nextTick` 处理路由切换后的 DOM 时序
- 文档同步：`PAGE_SPECS.md` P1 导航栏与 Hero 两行重写；`DESIGN_SYSTEM.md` 新增 §4.9 沉浸式首屏
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | npm run lint | 通过 | 无告警 |
  | npm run format:check | 通过 | 合规 |
  | npm run typecheck | 通过 | 无类型错误 |
  | npm run build | 通过 | 成功，仅既存 element-plus chunk >500kB 提示 |
  | npm run test:run | 通过 | 11 个文件 / 82 条用例全部通过 |
  | 浏览器冒烟（599px，scroll=0） | 通过 | `hero.height=576`、`hero.top=0`；页头 `backgroundColor=rgba(0,0,0,0)` 且带 `app-header--over-hero`；kicker 文本正常；页面无横向溢出（`scrollWidth 584 < innerWidth 599`） |
  | 浏览器冒烟（599px，scroll=300） | 通过 | 背景 `translate3d(0,84px,0)`、内容 `opacity 0.2857` / `translate3d(0,-18px,0)`，视差与淡出生效 |
  | 浏览器冒烟（599px，scroll=620） | 通过 | 页头类名回落为 `app-header`，背景 `rgb(255,255,255)`，说明滚过 Hero 后转实底 |
  | 列表页回归 | 通过 | `/teas` 页头无 `over-hero` 类、背景纯白，透明态未泄漏到其他页面 |

- 未验证：≥768px 桌面视口未实机查看（浏览器视图宽度固定 599px）；未逐张轮播切换检查 6 张背景在暗色压边下的观感；未做 Lighthouse 对比度量化
- 可回滚：还原 `HomeView.vue` Hero 结构（`.hero__bg-layer` / `.hero__scrim` / `.hero__cue` 及视差脚本）与 `AppHeader.vue` 的 `overHero` 逻辑，并把 `.home-page` 的 `padding-top` 改回 64px / 56px

## 2026-11-12 首页统计带与 Hero 衔接（消除硬切边）

- 任务编号：TASK-20261112-10
- 分级：A
- 判定理由：纯展示层（单文件模板结构 + 局部 CSS），无契约、数据、路由、业务规则变化
- 问题来源：用户上传截图指出「这个放在这里很突兀」，经确认指**统计带**——Hero 深色底直接切到浅色横条，小灰字孤立悬在页面底色上，与沉浸式首屏前后割裂
- 方案：统计带由「文档流横条」改为**悬浮玻璃面板**，负上边距 -34px 上探压住 Hero 底边，横跨深浅交界，视觉上把两段缝在一起
  - 数值由 `--text-h2` 提升到 `--text-h1`（衬线、`--color-primary-dark`），单位说明由 `--color-text-muted` 提到 `--color-text-secondary`，解决"小灰字孤立"
  - `backdrop-filter: blur(10px)` + `rgba(255,255,255,0.94)`：压在照片上透出茶山，落在页面底色上与正文无缝
  - 阴影只向下投射（`0 22px 44px -30px`），避免顶部灰边形成新的分界线（沿用 `2026-11-10` 否决项的教训：不做会形成可见边界的覆盖层）
  - 滚动提示上移（`bottom: 32px → 46px`，竖线 `44px → 30px`），与面板顶边留 12px 空隙
- 变更：
  - `frontend/src/views/HomeView.vue`
    - 模板：`.stats` 内改为 `.container > .stats__inner`（原 `.container` 与 `.stats__inner` 同元素，卡片内边距会与容器内边距互相覆盖）
    - CSS：`.stats` 新增 `position: relative; z-index: 2; margin-top: -34px`；`.stats__inner` 新增 `max-width: 760px`、`padding: 22px 40px`、`border-radius: var(--radius-lg)`、玻璃底色、向下投影、`backdrop-filter`；`.stats__value` 字号与行高调整；`.stats__label` 提色
    - 移动端（<640px）：`gap: 12px 26px`、`padding: 18px 20px`，保留隐藏分隔线与 `--text-h3` 降级
    - `.hero__cue` / `.hero__cue-line`：改为 `bottom: 46px` / `height: 30px`
- 文档同步：`PAGE_SPECS.md` P1 统计带行补充玻璃面板上探描述；`DESIGN_SYSTEM.md` 新增 §4.10 统计带（Stat Strip），§4.9 滚动提示竖线由 44px 更正为 30px
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | npm run lint | 通过 | 无告警 |
  | npx prettier --check src/views/HomeView.vue | 通过 | 合规 |
  | npm run typecheck | 通过 | 无类型错误 |
  | npm run build | 通过 | 成功，仅既存 element-plus chunk >500kB 提示 |
  | npm run test:run | 通过 | 11 个文件 / 82 条用例全部通过 |
  | 浏览器冒烟（599px，scroll=0） | 通过 | `innerWidth=599`、`heroBottom=576`、`cardTop=542` → 上探 34px；`cardW=552`、`cardH=59.7`、`borderRadius=12px`、`backgroundColor=rgba(255,255,255,0.94)`、`backdropFilter=blur(10px)`；面板在下缘露出一截，形成"下探"暗示 |
  | 浏览器冒烟（599px，scroll=430） | 通过 | 截图目检：深色首屏与浅色正文之间不再有硬切边，面板骑在交界处；提示竖线底边到面板顶边实测间距 12px，无重叠 |

- 未验证：≥768px 桌面视口未实机查看（浏览器视图宽度固定 599px，无视口调整能力）；面板在 6 张轮播背景下的毛玻璃观感未逐张目检；`backdrop-filter` 在低版本浏览器降级为纯白 0.94 底色，未做 Safari 实机验证
- 可回滚：还原 `.stats` / `.stats__inner` / `.stats__value` / `.stats__label` 样式块与 `.hero__cue` 的 `bottom` / `height`，并把模板 `.container > .stats__inner` 改回 `.container.stats__inner`
- **后续（同日）**：用户反馈统计带进入首屏后显得拥挤，本任务按用户要求整体回退，见 TASK-20261112-11

## 2026-11-12 统计带移出首屏 + Hero 文字排版优化

- 任务编号：TASK-20261112-11
- 分级：A
- 判定理由：纯展示层（模板顺序 + 局部 CSS），无契约、数据、路由、业务规则变化
- 需求来源：用户「把这个移到下一页吧，就要修改之前的那样，首页就把中间的文字排版优化一下」
  - 「这个」= 统计带；「移到下一页」= 移出首屏、在第二屏出现；「修改之前的那样」= 恢复 TASK-20261112-10 之前的朴素横条
- 变更（`frontend/src/views/HomeView.vue`）：
  1. **回退 TASK-10**：`.stats` 恢复 `padding: 28px 0 4px`（去负边距 / `z-index`）；`.stats__inner` 恢复普通 flex 横排（去 `max-width` / 卡片内边距 / 圆角 / 玻璃底色 / 投影 / `backdrop-filter`）；数值回 `--text-h2`、标签回 `--color-text-muted`；`.hero__cue` 恢复 `bottom: 32px`、竖线 `44px`
  2. **位置下移**：统计带由 `Hero → 统计带 → 引导入口` 改为 `Hero → 引导入口 → 统计带 → 六大茶类`，首屏只留 Hero，统计带在第二屏出现
  3. **Hero 文字排版优化**：
     - `.hero__title`：`line-height 1.2 → 1.18`、新增 `letter-spacing: 0.04em`、下间距 `18px → 20px`
     - `.hero__title-accent`：新增 `margin-top: 6px`（两行之间留一口气）与 `letter-spacing: 0.12em`（暖金行更舒展）
     - `.hero__subtitle`：新增 `line-height: 1.8`、`letter-spacing: 0.04em`；`max-width 600px → 520px` 收窄成一行舒适行长；下间距 `40px → 42px`
- 文档同步：`PAGE_SPECS.md` P1 区块表把「统计带」行移到「引导入口」之后并注明不进入首屏；`DESIGN_SYSTEM.md` §4.8 补双行标题的行距/字距规则，删除 §4.10 统计带，§4.9 滚动提示竖线改回 44px
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | npm run lint | 通过 | 无告警 |
  | npx prettier --check src/views/HomeView.vue | 通过 | 合规 |
  | npm run typecheck | 通过 | 无类型错误 |
  | npm run build | 通过 | 成功，仅既存 element-plus chunk >500kB 提示 |
  | npm run test:run | 通过 | 11 个文件 / 82 条用例全部通过 |
  | 浏览器冒烟（599px，scroll=0） | 通过 | 截图目检：首屏仅 Hero（kicker / 双行标题 / 副标题 / 搜索框 / 向下探索），统计带不再出现在首屏；标题两行分色与字距生效 |
  | 浏览器冒烟（599px，scroll=760） | 通过 | 截图目检：顺序为「引导入口 → 统计带 → 六大茶类」，统计带恢复朴素横排，分隔线在 <640px 隐藏 |

- 未验证：≥768px 桌面视口未实机查看（浏览器视图宽度固定 599px）；未逐张轮播背景检查新字距下标题的实际观感
- 可回滚：把统计带 `<section class="stats">` 移回 Hero 之后，并还原 `.hero__title` / `.hero__title-accent` / `.hero__subtitle` 三条新增声明
- **后续（同日）**：用户要求回退到沉浸式场景第一版，本任务对新版文字排版的调整被撤销，见 TASK-20261112-12

## 2026-11-12 回退到沉浸式首屏第一版

- 任务编号：TASK-20261112-12
- 分级：A
- 判定理由：纯展示层回退，无契约、数据、路由、业务规则变化
- 需求来源：用户「回退到让你改沉浸式场景的第一版」
- 回退目标：`TASK-20261112-09` 交付时的首页状态（沉浸式首屏 + Hero 正下方朴素统计带 + 引导入口 → 六大茶类 …），即撤销 TASK-10 与 TASK-11 的全部改动
- 变更（`frontend/src/views/HomeView.vue`）：
  1. 统计带移回 Hero 正下方（`Hero → 统计带 → 引导入口`），恢复 `<div class="container stats__inner">` 单层结构
  2. `.stats` 保持 TASK-09 时的朴素横排（`padding: 28px 0 4px`、`gap: 32px`、数值 `--text-h2`、标签 `--color-text-muted`）
  3. `.hero__title` 还原：`line-height 1.2`、去掉 `letter-spacing`、下间距回 `18px`
  4. `.hero__title-accent` 还原：仅保留 `color: var(--color-tea-yellow)`，去掉 `margin-top` 与 `letter-spacing`
  5. `.hero__subtitle` 还原：`max-width: 600px`、`margin: 0 auto 40px`，去掉 `line-height` / `letter-spacing`
  6. `.hero__cue` 保持 `bottom: 32px`、竖线 `44px`（TASK-10 曾改，TASK-11 已恢复）
- 文档同步：`PAGE_SPECS.md` 统计带行移回 Hero 之后并去掉"不进入首屏"描述；`DESIGN_SYSTEM.md` §4.8 双行主标题还原为 TASK-08 版本文案
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | npm run lint | 通过 | 无告警 |
  | npx prettier --check src/views/HomeView.vue | 通过 | 合规 |
  | npm run typecheck | 通过 | 无类型错误 |
  | npm run build | 通过 | 成功，仅既存 element-plus chunk >500kB 提示 |
  | npm run test:run | 通过 | 11 个文件 / 82 条用例全部通过 |
  | 浏览器冒烟（599px，scroll=0） | 通过 | 截图目检：满屏 Hero（kicker / 双行标题 / 副标题 / 搜索框 / 向下探索），统计带紧接 Hero 在页面底缘露出，与 TASK-09 交付时一致 |

- 未验证：≥768px 桌面视口未实机查看（浏览器视图宽度固定 599px）；未逐张轮播背景检查标题观感
- 可回滚：按 TASK-11 记录重新应用「统计带移出首屏 + 文字排版优化」即可

## 2026-11-12 其余前台页面适配沉浸式视觉体系

- 任务编号：TASK-20261112-13
- 分级：A
- 判定理由：纯展示层（模板小标 + 局部 CSS + 全局工具类），无契约、数据、路由、业务规则变化
- 需求来源：用户「把其他的页面也适配优化一下」
- 问题（改前调查结论）：
  - 投稿页 / 我的提交页 `padding-top: 32px`，**内容被 64px 固定页头压住**；两页均未定义 `.container`，内容贴着视口左边；两页 h1 未使用 `--font-display`
  - 其余一级页面 `padding-top: 64px`（等于页头高度，无呼吸空间），移动端 56px；篇幅类页面（茶文化列表/详情）已是 88/76，口径不一致
  - 全站仅首页有 kicker，其余页面标题层级单一；面包屑 `/` 与 `›` 混用
- 变更：
  1. `frontend/src/style.css` 新增全局 `.page-kicker`（text-caption / letter-spacing 0.24em / uppercase / text-muted）与 `.page-kicker--center`（两侧 32px × 1px 发丝线）
  2. 顶部留白统一 88px（≤767px 76px）：`TeaListView` / `CompareView` / `TeaDetailView` / `MyListView` / `ProfileView` / `ShareView` / `ContributeView` / `MyContributionsView`
  3. `ContributeView` / `MyContributionsView` 补齐 `.container`（1200 / 32px，≤1023px 24px，≤767px 16px）；h1 补 `font-family: var(--font-display)`；投稿页标题/说明包进 `.contribute-hero__main` 以免 kicker 挤进 flex 行
  4. 新增 kicker：对比页「Side by Side」（居中带线）、茶文化列表「Tea Culture」、茶文化详情「Article」、茶品详情「Tea Detail」、个人中心「Profile」、投稿「Contribute」、我的提交「My Contributions」；我的清单保留原页内眉标、分享页保留徽章行，不叠加 kicker
  5. 面包屑分隔符 `ContentListView` / `ContentDetailView` 的 `/` 统一为 `›`
  6. 茶品列表页保持原型结构（面包屑 + 工具条），未新增 h1，仅调整顶部留白
- 文档同步：`DESIGN_SYSTEM.md` 新增 §4.10 一级页面标题区；`PAGE_SPECS.md` 新增「十三、前台一级页面统一标题区」表
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | npm run lint | 通过 | 无告警 |
  | npx prettier --check "src/**/*.{vue,css,ts}" | 通过 | 全部符合格式 |
  | npm run typecheck | 通过 | 无类型错误 |
  | npm run build | 通过 | 成功，仅既存 element-plus chunk >500kB 提示 |
  | npm run test:run | 通过 | 11 个文件 / 82 条用例全部通过 |

- 未验证：**未做浏览器目检** —— 本轮会话无可用浏览器工具（`browser_*` 未注册），仅通过静态检查与构建验证；投稿页解遮挡、各页 kicker 观感、599px 下换行均需人工过目
- 可回滚：删除 `.page-kicker` 两条全局样式；各页 `padding-top` 还原为 64/56（投稿与我的提交还原为 `32px 0 64px` 并删除新增 `.container`）；移除各页新增 `<p class="page-kicker">` 与 `font-family` 声明；面包屑 `›` 还原为 `/`

## 2026-11-12 新增第七茶类「再加工茶」并录入 8 款边界茶

- 任务编号：TASK-20261112-14
- 分级：**C**（数据库 ENUM、API 契约、PRD 业务规则变更）
- 判定理由：扩展茶类枚举属于数据契约与业务规则变更；已由用户明确确认「新增第七茶类再加工茶」，确认记录见本节需求来源
- 需求来源：用户「先同步，再把边界茶也加入」；随后确认选择**新增「再加工茶」类**而非归入现有六类，并指定茉莉花茶、茉莉毛尖、茉莉银针、桂花乌龙、白桃乌龙，另由 AI 补充最具代表性的 3 款
- 命名与样式：`category = reprocessed`；中文「再加工茶」；标签色 `--color-tea-reprocessed: #B98A9B`（柔和玫瑰色，仅 `style.css` 定义 HEX）
- 入库 8 款（`scripts/tea_expand/data_reprocessed.py`）：茉莉花茶 / 茉莉毛尖 / 茉莉银针 / 桂花乌龙 / 白桃乌龙 / 玫瑰花茶 / 杭白菊 / 陈皮普洱
- 变更：
  1. 迁移 `backend/app/alembic/versions/0013_reprocessed_category.py`：`teas.category` 与 `tea_name_category_map.category` ENUM 追加 `reprocessed`（顺序固定在 `dark` 之后）
  2. 后端枚举：`models/tea.py`、`models/contribution.py`、`schemas/tea.py`（`CATEGORY_VALUES` / `CategoryValue` / `CategoryCount`）、`services/contributions.py` 中文映射、`scripts/seed_brewing_guides.py`（默认水温/投茶/时长、导语、注意事项、`reprocessed` 专用 6 步模板）
  3. 前端：`types/index.ts`、`utils/teaQuery.ts`（`TEA_CATEGORIES` + `CATEGORY_LABELS`）、`utils/brewing.ts`、`CategoryTag.vue`、`TeaListView.vue`（chip 选中态）、`HomeView.vue`（字标 / 标题 / 7 列网格 / 1023px 断点 4 列）、`CompareView.vue`（7 列，min-width 1000）、`style.css` 新增色 token；页脚 / 路由标题 / 投稿页 / 后台看板等用户可见文案由「六大」改为「七大」
  4. 数据：新增 `scripts/tea_expand/data_reprocessed.py`；`__init__.py` 合并为 `ALL_TEAS`；`import_teas.py` 补 `reprocessed: (150, 1000)` 价格区间
  5. 文档：PRD v1.4（七大茶类、枚举表、FR-2.1、S3 命名）、DATA_MODEL（ENUM / 索引说明 / 选型理由）、API_CONTRACT + openapi.yaml（枚举与固定顺序）、DESIGN_SYSTEM（标签色）、PAGE_SPECS（首页 7 张卡片、chips、对比页、后台分布图）、MODULE_DESIGN / ARCHITECTURE / AGENTS 的枚举表述、`database/init.sql`（两处 ENUM + 8 条名品映射）
- 数据执行结果：`python -m alembic upgrade head` 成功；`python scripts/tea_expand/import_teas.py` 新增 8 款，当前库 **219** 款（green 66 / white 20 / yellow 14 / red 36 / oolong 41 / dark 34 / reprocessed 8）；`python -m app.scripts.seed_brewing_guides` 为新茶生成教程；`tea_name_category_map` 补 8 条（共 30 条）
- 主图补充：8 款新茶各生成 1 张 4:3 实拍风格主图（玻璃杯冲泡特写，与既有茶品图风格一致），存放于 `backend/uploads/2026/11/`，`teas.main_image_url` 全部写入；`data_reprocessed.py` 同步补 `main_image_url`，重复导入不会丢图。校验：`main_image_url IS NULL` 数量为 0，`/uploads/...` 经后端与 Vite 代理均返回 200
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | `python -m ruff check app tests` | 通过 | All checks passed |
  | `python -m ruff format --check app tests` | 未通过（既存） | 本轮修改的 `schemas/tea.py` 已格式化；仍有 `services/admin.py`、`tests/test_brewing_guides.py` 两处**本轮未改动**的既存格式差异，未顺手改动 |
  | `python -m pytest -q` | 通过 | 190 passed（含更新后的七大茶类顺序断言） |
  | `npm run lint` | 通过 | 无告警 |
  | `npx prettier --check "src/**/*.{vue,css,ts}"` | 通过 | 全部符合格式 |
  | `npm run typecheck` | 通过 | 无类型错误 |
  | `npm run build` | 通过 | 成功，仅既存 element-plus chunk >500kB 提示 |
  | `npm run test:run` | 通过 | 11 个文件 / 82 条用例全部通过 |
  | `python scripts/check_all.py` | 通过 | 链接 / 常量 / 五层 / UI / 记录 / 密钥全部通过 |

- 未验证：**未做浏览器目检** —— 首页 7 列卡片与对比页 7 列在 599px / 桌面视口的实际观感需人工过目；库中 8 款新茶详情页 UI 未逐款点击核对
- 可回滚：`python -m alembic downgrade 0012_brewing_guides`（需先移除或改类 `reprocessed` 茶品，严格模式下否则失败）；还原本轮 ENUM / 类型 / 文档改动，删除 `data_reprocessed.py` 与对应 8 款数据

### 追加（同日）：残留「六大茶类」排查与修正

- 需求来源：用户截图首页统计带仍显示「6 大茶类体系」，要求修正并排查其他不适配处
- 变更：
  1. `HomeView.vue` 统计带数值由硬编码 `6` 改为 `TEA_CATEGORIES.length`（实际渲染 7），避免今后枚举再变时再次失配
  2. `HomeView.vue` `.categories__grid` 响应式断点：`≤1199px` 4 列、`≤767px` 2 列，桌面 `repeat(7, 1fr)`
  3. `CompareView.vue` 文件头注释「六列对比表」→「七列对比表」
  4. 注释 / 文案同步：`backend/app/main.py`（OpenAPI 描述）、`routers/teas.py`、`repositories/admin_repo.py`、`services/admin.py`、`services/teas.py`（「固定六项」→「固定七项」）、`schemas/tea.py`
  5. 文档同步：`openapi.yaml`（`/teas/categories` 摘要与「固定返回七项」）、`API_CONTRACT.md`（茶类枚举 / FR-2.1 入口）、`DESIGN_SYSTEM.md`（筛选 Chip、工具条、验收清单）、`TECH_STACK.md`（设计 token）、`DATA_MODEL.md`（名品映射 22 → 30）、`README.md`（项目定位、功能说明、截图标题）
- 不改动项（判定为准确的历史/领域表述）：`原型/`（禁止修改）、`specs/`（历史草稿）、`build-log` 历史条目、`init.sql` 中「六大茶类分类原理」「古六大茶山」等内容数据、`素材清单.md` 中 6 张首页背景图的记录
- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | `python -m ruff check app tests` | 通过 | All checks passed |
  | `python -m pytest -q` | 通过 | 190 passed |
  | `npm run lint` | 通过 | 无告警 |
  | `npx prettier --check src` | 通过 | 全部符合格式 |
  | `npm run typecheck` | 通过 | 无类型错误 |
  | `npm run build` | 通过 | 成功，仅既存 element-plus chunk >500kB 提示 |
  | `npm run test:run` | 通过 | 11 个文件 / 82 条用例全部通过 |
  | `python scripts/check_all.py` | 通过 | 链接 / 常量 / 五层 / UI / 记录 / 密钥全部通过 |

- 未验证：未做浏览器目检 —— 统计带「7 大茶类体系」、7 列分类网格在 1199/767 断点的换行观感、对比页 7 列在 1024 视口的横向滚动需人工过目
- 可回滚：还原上述 5 组文件改动即可（统计带数值亦可回退为常量 6）

## 2026-11-12 代码审查 8 项缺陷修复（认证 / 部署 / 推荐 / 演示数据 / 文档 / 密钥）

- 任务编号：TASK-20261112-15
- 分级：**B / C 混合**。B：Cookie 配置化、Nginx 视频体积、导入脚本收藏数、README/SECURITY 同步、`scripts/check_secrets.py` 增强。C（已获授权）：`/teas/recommended` 新增 `exclude_id` 属 API 契约变更，用户「按上面的优先级逐项改并补测试」视为确认；未改任何已冻结业务规则。
- 需求来源：用户提交第三方代码审查截图（列 7 条），要求核对是否真实存在并分析；随后明确「按上面的优先级逐项改并补测试」。核对结论：截图 7 条中 6 条属实、1 条（`.env` 泄露）部分属实，另**新发现第 8 条**（刷新守卫早于登录态）为截图未列的同类认证缺陷。
- 逐项变更：

  | # | 问题 | 修复 |
  |---|---|---|
  | 1 | 会话过期重登 404：`frontend/src/api/request.ts` 对 `redirect` 先 `encodeURIComponent`，`LoginView.vue` 再 `router.push`，产生 `%252F...` 二次编码 → 落入 404 兜底路由 | 新增 `frontend/src/utils/redirect.ts`：`buildLoginRedirect()` 只拼接不编码、`resolveLoginRedirect()` 仅接受以单 `/` 开头且非 `//` 的路径（防开放重定向）。`request.ts`、`LoginView.vue:38`、`RegisterView.vue:111` 统一走该模块；新增 `utils/redirect.spec.ts` 5 条用例 |
  | 2 | HTTP 部署下 Cookie 恒为 `Secure`，浏览器不保存 → 登录 200 但后续全部 401 | `core/config.py` 新增 `COOKIE_SECURE: bool \| None = None` 与 `cookie_secure` 派生属性（显式值优先，否则 `not DEBUG`）；`routers/auth.py` 删除导入期 `_COOKIE_KWARGS`，改 `_cookie_kwargs()` 运行时读取；`main.py` 在 `not DEBUG and not cookie_secure` 时启动告警；`deploy/env.example`、`backend/.env.example`、`docker-compose.yml` 补配置项；`test_auth.py` 新增 2 条用例 |
  | 3 | 后端允许 50MB 视频，Nginx 全局 `client_max_body_size 6m` → 6–50MB 在网关层 413 | `deploy/nginx.conf` 全局保持 6m，新增 `location = /api/v1/admin/media/video`（52m、`proxy_read_timeout 120s`）；新增 `tests/test_deploy_config.py` 2 条用例（网关块存在 + 50/52/6 三处常量自洽） |
  | 4 | 首页「换一款」对登录用户可能不换：登录分支调 `getRecommendedTeas(1)` 未传排除项，推荐服务只排除已收藏 | `routers/teas.py` 增加 `exclude_id` 查询参数；`services/teas.py` 在偏好与随机两条路径都排除 `exclude_id`；`frontend/src/api/teas.ts`、`HomeView.vue` 传当前茶 id；`API_CONTRACT.md` §4.2.10 + `openapi.yaml` 同步；`test_batch2_features.py` 新增 2 条用例（游客随机排除、登录偏好排除） |
  | 5 | 导入脚本用 `random.randint(100, 2000)` 伪造 `teas.favorite_count`，污染热门排序 | `scripts/tea_expand/import_teas.py` 改为 `fav_count = 0` 并注释来源约束；新增 `backend/app/scripts/recount_favorite_counts.py`（按 `COUNT(DISTINCT favorite_items.user_id)` 重算，支持 `--dry-run`）+ `tests/test_favorite_count_recount.py` 1 条用例 |
  | 6 | README 与代码严重不一致（称第二阶段未开发、58 端点、13 表、184 测试、迁移 0011、94 条用例；SECURITY 称 Cookie 缺 `secure`） | `README.md` 全面校准：标题/§1 加第二阶段扩展、新增 §3.4「第二阶段扩展（已完成）」、端点数 60（admin 17）、表 14、迁移 0001–0013、§10 测试结果改为 2026-11-12 实测数据、§9 补 `COOKIE_SECURE` 与「分享前排除 `.env`」、§12/§13 补视频 52m 与 HTTPS 必须项；`SECURITY.md` S-07 改为 `COOKIE_SECURE` 生效机制并关闭 G-02，清理 S-11/S-12/S-13 的「待创建」过期标记 |
  | 7 | `backend/.env` 含非空口令与密钥 | 核实：已被 `.gitignore` 忽略、未进 Git、`.dockerignore` 排除，**未泄露到仓库**；风险在整目录打包分享。`scripts/check_secrets.py` 新增 `local_env_report()`：只报告非空键名不打印值，普通模式 WARN，`--share-check` 时存在 `backend/.env` 即 FAIL 退出 1；README 补分享前检查说明。**轮换口令/密钥属用户操作，未代为修改** |
  | 8 | （截图未列）硬刷新 `/my`、`/admin` 等受保护页被守卫提前踢到登录页：`main.ts` 先 `app.use(router)`（内部立即 `push` 当前地址）再异步 `hydrate()` | 新增 `frontend/src/bootstrap.ts`：`await hydrate()` 完成后才 `app.use(router)` 并 mount（hydrate 失败仍继续，避免白屏）；`main.ts` 改用 bootstrap；新增 `bootstrap.spec.ts` 2 条用例验证时序 |

- 测试证据：

  | 项目 | 结果 | 说明 |
  |---|---|---|
  | `python -m ruff check --no-cache app tests` | 通过 | All checks passed |
  | `python -m ruff format --no-cache --check app tests` | 通过 | 102 files already formatted（顺带修正 `services/admin.py`、`tests/test_brewing_guides.py` 既存格式差异，纯换行/折行） |
  | `cd backend; python -m pytest -q -p no:cacheprovider --log-cli-level=WARNING` | 通过 | **197 passed, 1 warning**（Starlette httpx 弃用告警），28.45s，连真实 MySQL |
  | `npm run lint` | 通过 | 无告警 |
  | `npm run format:check` | 通过 | All matched files use Prettier code style |
  | `npx vue-tsc --noEmit -p tsconfig.app.json` | 通过 | 无类型错误 |
  | 前端 Vitest 全量 | 通过 | **13 个 spec / 89 条用例**（新增 redirect 5 + bootstrap 2 + 既有用例） |
  | 生产构建 | 通过 | `vite build` 1825 modules，主入口 104.09 kB（gzip 37.18 kB），`vendor-element-plus` 998.39 kB（gzip 320.75 kB，>500 kB 提示非失败） |
  | `python scripts/check_all.py` | 通过 | 300 条文档链接；常量 `60/100/35/14`；五层 0 违规；268 个文本文件无敏感信息；`backend/.env` 输出 WARN |
  | `python scripts/check_secrets.py --share-check` | 通过（按设计失败） | 退出码 1 并提示 `backend/.env` 存在，符合分享前阻断预期 |

- 运行环境限制（如实记录）：
  1. 沙箱内 `npm run test:run` 必报 `Error: spawn EPERM`（Vite `windowsSafeRealPathSync` 执行 `net use`）；本次用临时 Node 预加载脚本拦截该调用 + 临时 Vitest 配置跑通，**临时文件已清理**，全量用例数可信，但直连命令未能原样复现。
  2. `npm run typecheck` / `npm run build` 因写 `node_modules/.tmp/*.tsbuildinfo` 与 `frontend/dist` 被沙箱拒绝（TS5033 / EPERM）；类型检查改用 `vue-tsc --noEmit` 等价验证，构建改用 `--outDir $TEMP/...` 验证，**未写入仓库 `dist/`**。
  3. `frontend/.tmp-vitest.config.mjs`（临时 Vitest 配置）已清空但**文件本身无法删除**（宿主对该路径 unlink 报 Permission denied），需人工删除；该文件未被 Git 跟踪，`npm run test:run` 不受影响。
  4. **未做浏览器 E2E**：401 重定向、硬刷新受保护页、HTTP 下 Cookie 保存三项均以单元测试与代码时序验证，未在真实浏览器跑 Playwright。
  5. **未实机复测 Nginx 413**：视频 6–50MB 上传仅做配置断言，未在真实 Nginx 环境验证（与 §12 已知问题 8 同一事项）。

- 可回滚：还原上表 8 项涉及的源码/文档改动（`git` 中 27 个修改文件 + 以下新增文件）；删除新增源码 `frontend/src/utils/redirect.ts`、`frontend/src/bootstrap.ts`、`backend/app/scripts/recount_favorite_counts.py` 与新增测试 `frontend/src/utils/redirect.spec.ts`、`frontend/src/bootstrap.spec.ts`、`backend/tests/test_deploy_config.py`、`backend/tests/test_favorite_count_recount.py`；`exclude_id` 为向后兼容的可选参数，回退时可保留。

