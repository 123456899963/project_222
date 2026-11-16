# P2 工程加固任务清单（tasks）

> 依据：[spec.md](./spec.md)
> 状态：待确认后执行

## 阶段一：后端安全与告警（T1 + T2）

- [x] T1-1 `user_repo.py` 新增 `revoke_sessions`
- [x] T1-2 `services/auth.py` 新增 `logout`
- [x] T1-3 `routers/auth.py` logout 接入 `get_optional_user` 并调用吊销
- [x] T1-4 更新 `test_auth.py` 登出重放断言
- [x] T1-5 更新 `test_g5_system.py` AUTH-08 断言与 `session_version` 校验
- [x] T1-6 同步 SECURITY / API_CONTRACT / TEST_PLAN / openapi / README
- [x] T2-1 新增 `core/clock.py` 的 `utcnow()`
- [x] T2-2 替换 8 个模型文件中的 `datetime.utcnow`
- [x] T2-3 替换 2 个测试文件中的 `datetime.utcnow`
- [x] T2-4 `config.py` 改用 `SettingsConfigDict`
- [x] T2-5 运行 `ruff check` + `ruff format --check` + `pytest -q`，确认告警下降

## 阶段二：前端 chunk 拆分（T3）

- [x] T3-1 路由改为按页面懒加载（Home 除外）
- [x] T3-2 `vite.config.ts` 增加 `manualChunks`
- [x] T3-3 运行 `lint` / `typecheck` / `format:check` / `test:run` / `build`
- [x] T3-4 记录构建前后主 chunk 体积对比

## 阶段三：部署与 CI（T4 + T5）

- [x] T4-1 新增 `deploy/Dockerfile.backend`
- [x] T4-2 新增 `deploy/Dockerfile.frontend`
- [x] T4-3 新增 `deploy/nginx.conf`
- [x] T4-4 新增 `docker-compose.yml`
- [x] T4-5 新增 `deploy/env.example` 与 `.dockerignore`
- [x] T4-6 `docker compose config` 校验（Docker 不可用，改为 PyYAML 语法解析通过）
- [x] T4-7 更新 README §13 部署说明
- [x] T5-1 核对 Gitee Go 官方语法并新增 `.workflow/ci.yml`
- [x] T5-2 保留 `.github/workflows/ci.yml`
- [x] T5-3 文档注明远端未验证

## 阶段四：截图与交付（T6 + 回归）

- [x] T6-1 启动 MySQL / 后端 / 前端
- [x] T6-2 截取前台 5 张 + 后台 3 张页面图并放入 `docs/images/`
- [x] T6-3 更新 README §11
- [x] T6-4 若截图受阻，如实记录原因
- [x] R-1 全量回归：pytest / Vitest / check_all / build
- [x] R-2 回填 `harness/build-log.md`
- [x] R-3 汇总交付证据，不提交 Git（除非用户要求）

## 完成定义（DoD）

1. spec §10 验收清单全部勾选或如实标注阻塞原因。
2. 所有测试实跑并记录真实结果。
3. 文档与代码同步，无未同步的契约/安全行为变更。
4. build-log 含任务编号、分级、改动、测试证据、遗留与回滚方式。
