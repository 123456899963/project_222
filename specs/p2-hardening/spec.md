# P2 工程加固规格（spec）

> 状态：已实施（2026-11-11）
> 日期：2026-11-11
> 范围：P2 全部待办项；用户已确认 Docker Compose 单机部署、CI 迁移 Gitee Go、四项优化全做。

## 1. 目标与已确认决策

| 项 | 决策 |
|---|---|
| 部署形态 | Docker Compose 单机：`web`(Nginx+静态) + `api`(Uvicorn) + `mysql`(5.7) |
| CI | 新增 Gitee Go 流水线，保留 `.github/workflows/ci.yml` 作为备份 |
| 登出会话吊销 | 复用 `users.session_version`，登出时递增使旧 Cookie 立即失效 |
| Python 告警清理 | 清理 `datetime.utcnow()` 与 Pydantic `class Config` 弃用告警（不升级 Pydantic 大版本） |
| 前端 chunk | 路由懒加载 + vendor 手动分包，降低主 chunk 体积 |
| README 截图 | 实机截取前台/后台页面，放入 `docs/images/` 并更新 README §11 |

## 2. T1 登出会话吊销（安全行为变更，用户已确认）

### 2.1 代码改动

1. `backend/app/repositories/user_repo.py`
   - 新增 `revoke_sessions(db: Session, user: User) -> User`：`session_version = (session_version or 0) + 1` → `commit` → `refresh`。
2. `backend/app/services/auth.py`
   - 新增 `logout(db: Session, user: User | None) -> None`：`user is not None` 时调用 `user_repo.revoke_sessions`；无效会话保持幂等。
3. `backend/app/routers/auth.py`
   - `import get_optional_user`。
   - `logout` 改为 `def logout(response: Response, current_user=Depends(get_optional_user), db: Session = Depends(get_db))`。
   - 先 `auth_service.logout(db, current_user)`，再 `_clear_session_cookie(response)`。

### 2.2 测试改动

1. `backend/tests/test_auth.py::test_logout_clears_cookie`
   - 注册响应取 `cookies.get("tea_session")` 保存旧令牌。
   - 登出后用新 `TestClient` 重放旧 Cookie 调 `/auth/me`，断言 `401` / `40100`。
2. `backend/tests/test_g5_system.py::test_tc_auth_08_logout_clears_cookie_and_replay_risk`
   - 步骤④由「旧 Cookie 仍有效 200」改为「已吊销 401」，并重命名为 `..._and_replay_revoked`。
   - 直接查库断言 `users.session_version` 递增 1。

### 2.3 文档同步

1. `docs/architecture/SECURITY.md`
   - S-10 行：登出改为「递增 `session_version`，该用户全部旧 Cookie 立即失效」；注明取舍——无 `sessions` 表，故登出会使该用户所有设备会话失效。
   - §5 风险表 G-12：状态改为「已缓解」，保留残余风险（未登出前被窃取的 Cookie 在 30 天内仍有效）。
   - 变更记录追加 v1.5。
2. `docs/api/API_CONTRACT.md`
   - §1.5「退出」行改为服务端递增会话版本。
   - §4.1.4 规则补充：携带有效 Cookie 时递增 `session_version`，未登录/无效 Cookie 仅清 Cookie。
   - 变更记录更新版本。
3. `docs/testing/TEST_PLAN.md`
   - `TC-AUTH-08` 步骤④期望改为 401/`40100`，增加 `session_version +1` 校验。
   - §7 排除项「旧 Cookie 重放」行更新为已通过登出吊销关闭。
4. `docs/api/openapi.yaml`
   - 若 `logout` 有 description，补充吊销语义；无则仅确认无需改动。
5. `README.md` §12 已知问题 6：从「已知问题」移入已修复说明。

## 3. T2 Python 弃用告警清理

### 3.1 新增工具

`backend/app/core/clock.py`：

```python
from datetime import datetime, timezone

def utcnow() -> datetime:
    """当前 UTC 时间（naive），对齐 DATETIME 列语义。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
```

### 3.2 替换清单（`datetime.utcnow` → `utcnow`）

- `backend/app/models/user.py`
- `backend/app/models/favorite.py`（2 处）
- `backend/app/models/contribution.py`（1 处）
- `backend/app/models/content.py`（2 处）
- `backend/app/models/tea.py`（7 处）
- `backend/app/models/collection_list.py`（3 处）
- `backend/app/models/operation_log.py`（1 处）
- `backend/app/models/login_attempt.py`（1 处）
- `backend/tests/test_batch1_features.py`（2 处）
- `backend/tests/test_batch2_features.py`（1 处）

保留各文件用于类型注解的 `datetime` 导入；不再使用 `datetime.utcnow`。

### 3.3 Pydantic 配置

`backend/app/core/config.py`：
- 引入 `SettingsConfigDict`。
- `class Config: env_file = ".env"` → `model_config = SettingsConfigDict(env_file=".env")`。

## 4. T3 前端 chunk 拆分

1. `frontend/src/router/index.ts`
   - 仅 `HomeView` 保持同步导入。
   - 其余前台页面（`TeaListView`、`TeaDetailView`、`CompareView`、`MyListView`、`ContributeView`、`MyContributionsView`、`ProfileView`、`ShareView`、`LoginView`、`RegisterView`、`NotFound`）改为 `() => import(...)`。
2. `frontend/vite.config.ts`
   - 新增 `build.rollupOptions.output.manualChunks`：
     - `vendor-vue`: `vue`, `vue-router`, `pinia`
     - `vendor-qrcode`: `qrcode`
   - Element Plus 继续走 `/admin` 动态 import，不额外拆。

验收：`npm run build` 成功；主 chunk 体积较当前（约 1.1 MB）明显下降；`lint` / `typecheck` / `format:check` / `test:run` 全过。

## 5. T4 Docker Compose 部署配套

新增文件：

1. `deploy/Dockerfile.backend`
   - `python:3.11-slim`；安装 `backend/requirements.txt`；复制 `backend/`；`CMD uvicorn app.main:app --host 0.0.0.0 --port 8000`。
2. `deploy/Dockerfile.frontend`
   - 多阶段：`node:20-alpine` 执行 `npm ci && npm run build`；`nginx:1.27-alpine` 复制 `dist` 与 `deploy/nginx.conf`。
3. `deploy/nginx.conf`
   - `listen 80`；`client_max_body_size 6m`；`try_files $uri $uri/ /index.html`；`/api/` 与 `/uploads/` 反代 `http://api:8000`（保留原始路径）。
4. `docker-compose.yml`
   - `mysql:5.7`：`MYSQL_DATABASE=tea_guide`、`MYSQL_ROOT_PASSWORD` 来自环境、挂载 `database/init.sql` 到 `/docker-entrypoint-initdb.d/`、healthcheck。
   - `api`：依赖 mysql 健康；注入 `MYSQL_HOST=mysql`、`SECRET_KEY`、`ADMIN_PASSWORD` 等；挂载 `uploads` 卷。
   - `web`：依赖 api；映射 `8080:80`。
5. `deploy/env.example`
   - 列出 `MYSQL_ROOT_PASSWORD`、`SECRET_KEY`、`ADMIN_PASSWORD`、`SESSION_EXPIRE_DAYS` 等占位与生成命令。
6. `.dockerignore`
   - 排除 `.git`、`node_modules`、`dist`、`backend/uploads`、`.env`、测试缓存。

文档同步：`README.md` §13 更新为「Docker Compose 部署」主路径，保留手工部署作为备选；标注「配置已编写，尚未在真实服务器验证」。

## 6. T5 Gitee Go CI

新增 `.workflow/ci.yml`，覆盖与现有 GitHub Actions 等价的三个检查：

- 后端：`ruff check` → `ruff format --check` → `pytest -q`
- 前端：`npm ci` → `lint` → `format:check` → `typecheck` → `test:run`
- 文档守卫：`python scripts/check_all.py`

要求：
- 使用 Gitee Go 官方流水线语法（实施时核对官方文档）。
- 保留 `.github/workflows/ci.yml` 不变。
- 文档注明「流水线文件已提交，远端实际执行结果未验证」。

## 7. T6 README 系统截图

- 启动 MySQL + 后端 + 前端。
- 截取：首页、茶品列表（筛选展开）、茶品详情、我的清单、分享页、后台登录、后台概览、茶品管理。
- 保存到 `docs/images/`，更新 `README.md` §11 为真实截图与说明。
- 若本机服务/数据库不可用导致无法截图，README 如实标注「未完成」并记录原因，不伪造。

## 8. 验证与交付

| 步骤 | 命令 | 通过标准 |
|---|---|---|
| 后端 lint | `cd backend; python -m ruff check app tests` | 0 错误 |
| 后端格式 | `cd backend; python -m ruff format --check app tests` | 全部已格式化 |
| 后端测试 | `cd backend; python -m pytest -q` | 全通过，且本仓库代码无 `datetime.utcnow` 告警 |
| 前端检查 | `cd frontend; npm run lint; npm run typecheck; npm run test:run` | 全过 |
| 前端构建 | `cd frontend; npm run build` | 成功，主 chunk 下降 |
| 静态检查 | `python scripts/check_all.py` | 全过 |
| Compose 校验 | `docker compose config`（若 Docker 可用） | 配置可解析 |
| 记录 | `harness/build-log.md` 追加条目 | 含改动、测试证据、遗留 |

## 9. 影响面与风险

- T1 属安全行为变更：登出会使该用户所有设备会话失效；已在 SECURITY/契约中明示取舍。
- T1 会修改现有两条测试断言，必须同步 TEST_PLAN。
- T4/T5 为新增部署与 CI 配置，不改运行时代码；远端实际执行/真实服务器验证不在本次保证范围。
- T3 只改路由加载方式与构建配置，不改页面行为。
- T2 不改变时间语义（仍为 naive UTC），只消除弃用 API。

## 10. 验收清单

- [x] 登出后旧 Cookie 重放返回 401，`session_version` +1
- [x] 后端 pytest 全过，无 `datetime.utcnow` 弃用告警
- [x] 前端 lint/typecheck/test/build 全过，主 chunk 体积下降
- [x] `docker compose config` 可解析（Docker 可用时）
- [x] Gitee Go 与 GitHub CI 配置并存
- [x] README 截图完成或如实标注阻塞
- [x] SECURITY / API_CONTRACT / TEST_PLAN / README / build-log 已同步
