# 阶段 5（G5）系统测试报告

- 执行日期：2026-11-08（初测 + 缺陷修复复测）
- 执行范围：TEST_PLAN v1.0 §5 全部 60 条用例（含 §7.1 安全门禁与 4 条真实并发）
- 执行方式：真实 MySQL 5.7 测试库 + FastAPI TestClient + 真实浏览器操作 + 前端质量门禁
- 结论：**修复后通过**。高优先级 **32 / 32** 全部通过且无 skip；60 条用例 **60 / 60** 通过；后端全量 105 passed。CI 未运行（不计为通过）。

---

## 1. 测试环境与基线

| 项目 | 实际值 |
|---|---|
| 操作系统 | Windows（PowerShell 5） |
| Python | 3.12（项目要求 3.11+） |
| Node / npm | v24.21.0 / 11.19.0 |
| 数据库 | MySQL 5.7.19，库 `tea_encyclopedia`，InnoDB，utf8mb4 |
| 后端 | FastAPI + SQLAlchemy 2.0 同步模式，`http://127.0.0.1:8000` |
| 前端 | Vue 3 + Vite，`http://localhost:5173` |
| 浏览器 | Trae 内置浏览器（真实页面操作） |
| 测试数据 | 种子茶 6 款、种子管理员 `admin`；临时数据均在用例结束清理 |
| CI | **未运行**（未在 GitHub Actions 实际执行，不标记为通过） |

补充说明：

- 现有测试套件 82 条；初测新增 `backend/tests/test_g5_system.py` 21 条，修复阶段补充 2 条（DEF-02、DEF-04）并强化 AUTH-07，共 23 条；后端全量 105 条。
- 新增测试均为真实接口调用与数据库断言，无 skip；初测失败用例保留失败状态，修复后逐条复测，未放宽断言、未修改 TEST_PLAN 口径。

---

## 2. 真实命令输出摘录

### 2.1 后端全量（初测 → 修复后复测）

初测（缺陷复现证据，保留）：

```text
> python -m pytest -q --tb=no
...............................................F......F................. [ 69%]
...............................                                          [100%]
=========================== short test summary info ===========================
FAILED tests/test_g5_system.py::test_tc_auth_07_tampered_foreign_and_expired_session
FAILED tests/test_g5_system.py::test_tc_list_05_wildcards_are_escaped
2 failed, 101 passed, 469 warnings in 12.36s
```

初测失败断言原文：

```text
AssertionError: assert 480 is None
 +  where 480 = verify_session_token('eyJ1aWQiOjQ4MH0.avA_8Q.8bxJd7Q2YlOeFb5MtFQvD03G_4c', max_age_days=0)
AssertionError: %
assert 6 < 6
```

修复后复测：

```text
> python -m pytest -q
........................................................................ [ 68%]
.................................                                        [100%]
105 passed, 484 warnings in 17.25s
```

### 2.2 安全门禁批次（按 TEST_PLAN §7.1 顺序）

```text
> python -m pytest -q tests/test_admin.py::test_admin_perm_02_normal_user_gets_403_for_all_endpoints ^
    tests/test_admin.py::test_admin_perm_01_guest_gets_401_for_all_endpoints ^
    tests/test_g5_system.py::test_tc_auth_06_all_protected_endpoints_require_session ^
    tests/test_g5_system.py::test_tc_auth_09_no_password_in_response_or_logs ^
    tests/test_admin.py::test_admin_upload_02_oversize_returns_413 ^
    tests/test_admin.py::test_admin_upload_03_rejects_non_image_by_magic_and_empty_file ^
    tests/test_shares.py::test_share_04_revoked_cannot_revive_and_new_token_required ^
    tests/test_defense.py::test_def_03_unhandled_exception_returns_generic_500 ^
    tests/test_g5_system.py::test_tc_def_04_admin_password_rotation
9 passed, 10 warnings in 6.86s
```

修复后 TC-DEF-04 已纳入 §7.1 批次并真实执行（轮换 → 旧密码 401 → 新密码 200 → bcrypt cost=10 → 静态检查 → finally 恢复原密码）。

### 2.3 前端质量门禁

```text
LINT_OK
Checking formatting...
All matched files use Prettier code style!
FORMAT_OK
TYPECHECK_OK
Test Files  4 passed (4)
     Tests  30 passed (30)
TEST_OK
✓ built in 12.21s
BUILD_OK
```

构建告警（非失败）：主 chunk `index-ChnUv3tI.js` 1,138.07 kB，Vite 提示可拆分。

### 2.4 静态检查

```text
> python scripts/check_all.py
OK: 已检查 205 条相对链接，全部有效。
OK: 常量一致 {'openapi_operations': 29, 'test_cases': 60, 'security_controls': 32, 'database_tables': 7}
OK: 五层检查通过（历史遗留 0 项，未新增违规）。
BASELINE: api/request.ts / main.ts / stores/toast.ts 直接使用 Element Plus（基线遗留）
OK: 前台 UI 检查通过（历史遗留 3 项）。
OK: build-log 顺序、ADR 索引与 PR 同步检查通过。
OK: 已扫描 153 个文本文件，未发现高置信度敏感信息。
OK: 全部静态检查通过。
```

### 2.5 后端 Ruff

```text
> python -m ruff check app tests
All checks passed!
> python -m ruff format --check app tests
55 files already formatted
```

---

## 3. 用例统计

| 模块 | 用例数 | 高 | 中 | 低 | 通过 | 失败 | 未执行 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 认证与会话 | 9 | 6 | 3 | 0 | 9 | 0 | 0 |
| 茶品录入与上下架 | 7 | 3 | 4 | 0 | 7 | 0 | 0 |
| 筛选、搜索与分页 | 9 | 2 | 5 | 2 | 9 | 0 | 0 |
| 收藏与取消收藏 | 7 | 4 | 2 | 1 | 7 | 0 | 0 |
| 品鉴笔记 | 5 | 3 | 2 | 0 | 5 | 0 | 0 |
| 分享链路 | 10 | 6 | 4 | 0 | 10 | 0 | 0 |
| 权限校验 | 4 | 3 | 1 | 0 | 4 | 0 | 0 |
| 文件上传 | 5 | 3 | 2 | 0 | 5 | 0 | 0 |
| 异常与防御 | 4 | 2 | 2 | 0 | 4 | 0 | 0 |
| **合计** | **60** | **32** | **25** | **3** | **60** | **0** | **0** |

高优先级门禁结果：**32 / 32 通过，无 skip**，满足放行条件。初测的 3 条失败（AUTH-07 / LIST-05 / DEF-02）与 1 条未执行（DEF-04）均已修复并复测通过。

---

## 4. 60 条用例逐条记录

> 说明：每条均核对 HTTP 状态码、业务 `code`、`data` 结构与数据库最终状态；“证据”列给出可复现测试函数或手工命令。

### 4.1 认证与会话（AUTH，9 条）

| 编号 | 优先级 | 输入 / 操作步骤 | 预期结果 | 实际结果与证据 | 结果 |
|---|---|---|---|---|---|
| TC-AUTH-01 | 高 | 注册 `newuser1/tea2026`，记录 Set-Cookie，查 users | 200/0；含 id/username/role=user/created_at；Cookie HttpOnly/SameSite=Lax/Path=/Max-Age=2592000；`$2b$` 哈希且无密码字段 | 注册 200/0，字段齐全；users 中 `$2b$10$...` 且不等于明文；Cookie 属性由同一 set_cookie 路径在 AUTH-08 复核通过。证据：`test_register_success_returns_user_and_cookie`、`test_password_is_bcrypt_hashed_in_db` | 通过 |
| TC-AUTH-02 | 高 | 已存在 `Casexxxx`，再用 `CASExxxx`、`casexxxx` 注册，查行数 | 409/40910；users 总数不变；无 500/账号泄露 | 两次变体均 409/40910，users 仅 +1。证据：`test_tc_auth_02_duplicate_username_is_case_insensitive` | 通过 |
| TC-AUTH-03 | 中 | 用户名 2/3/20/21 字符；密码 5/6/64/65/1000 字符；`"  ab  "` | 2/21/5/65/1000/空格 → 400/40000；3/20/6/64 → 200/0 | 10 组全部符合；成功组落库、失败组无新增；无 500/截断。证据：`test_tc_auth_03_username_password_boundaries` | 通过 |
| TC-AUTH-04 | 高 | `admin/admin123` 登录、普通用户登录，分别调 `/auth/me` | 均 200/0；role 为 admin/user；均下发 Cookie；me 同 id/username/role；无 password_hash | 两项均通过，响应无密码字段。证据：`test_tc_auth_04_admin_and_user_login_roles`、`test_login_success_returns_user_and_cookie` | 通过 |
| TC-AUTH-05 | 高 | 不存在用户登录 5 次；错误密码登录 5 次，比较响应与耗时 | 均 401/40110；message 相同“用户名或密码错误”；无 Cookie；耗时差 ≤100 ms | 均 401/40110；message 完全相同；无 tea_session；中位耗时 ghost 48.1 ms、wrong 48.8 ms，差 **0.7 ms**。证据：`test_tc_auth_05_login_failure_is_uniform_and_timed` + 计时脚本 | 通过 |
| TC-AUTH-06 | 高 | 无 Cookie 调 me/favorites/lists/title/notes/generate/copy/admin，查三表 | 全部 401/40100；DB 无新增；无业务数据 | 8 个端点全部 401/40100；favorite_items/collection_lists/share_tokens 计数不变。证据：`test_tc_auth_06_all_protected_endpoints_require_session` | 通过 |
| TC-AUTH-07 | 中 | 篡改 Cookie 末位；异 SECRET_KEY 签发；`max_age_days=0` 验证过期 | 三种均无效 401/40100 | 三种均无效并返回 401/40100；`max_age_days=0/-1` 均返回 None。修复 D-01 后复测通过。证据：`test_tc_auth_07_tampered_foreign_and_expired_session` | 通过 |
| TC-AUTH-08 | 中 | 登录后登出，记录 Set-Cookie，无 Cookie 调 me，重放旧 Cookie | 200/0/data=null；删 Cookie 属性正确；无 Cookie 401；旧 Cookie 仍有效仅记录风险 | 登出 200/0；`Max-Age=0/Path=//HttpOnly/SameSite=lax`；无 Cookie 401/40100；重放旧 Cookie 200（S-10 已知限制，不计失败）。证据：`test_tc_auth_08_logout_clears_cookie_and_replay_risk` | 通过 |
| TC-AUTH-09 | 高 | 注册/登录/me，递归遍历响应 JSON，检索日志 | 无 password/password_hash 字段或明文；日志无明文/Cookie；错误日志无请求体 | 响应 key/value 无密码字段；日志无密码明文、无 session 值。证据：`test_tc_auth_09_no_password_in_response_or_logs` | 通过 |

### 4.2 茶品录入与上下架（TEA，7 条）

| 编号 | 优先级 | 输入 / 操作步骤 | 预期结果 | 实际结果与证据 | 结果 |
|---|---|---|---|---|---|
| TC-TEA-01 | 高 | admin 提交完整合法 JSON；查 teas/tea_tips/operation_logs | 200/0，TeaDetail 完整；teas 1 行、tips 建行；日志 create_tea | 全部通过，含 tips 与 operation_log。证据：`test_admin_tea_04_create_writes_tea_tips_and_log` | 通过 |
| TC-TEA-02 | 中 | 缺 name；category=black；season=夏季；fermentation=后发酵；额外字段 | 前三 400/40000；后发酵 200；额外字段拒绝或忽略不写入 | 前三 400/40000；后发酵 200；is_active/favorite_count/未知字段均 400/40000。证据：`test_tc_tea_02_valid_fermentation_and_unknown_field_rejected`、`test_admin_tea_05...` | 通过 |
| TC-TEA-03 | 中 | 温度 69.9/70.0/100.0/100.1/85.55；投茶 0/999.9/1000；时间 -1 | 70.0/100.0/999.9 通过，其余 400/40000；无四舍五入错误 | 9 组全部符合。证据：`test_tc_tea_03_numeric_boundaries` | 通过 |
| TC-TEA-04 | 中 | name 101、origin 201、price_range 33、品种 101、图片 URL 501 字符 | 均 400/40000；无 DB 行；无 Data too long/列名泄露 | 5 组全部 400/40000；teas 计数不变。证据：`test_tc_tea_04_field_length_limits` | 通过 |
| TC-TEA-05 | 高 | PUT tea1，season=null、省略品种；注入 id/is_active/favorite_count；查日志 | 200/0，PUT 全量替换；托管字段不变；updated_at 更新；日志 update_tea | 全部通过。证据：`test_admin_tea_06_update_replaces_fields_and_keeps_managed_fields` | 通过 |
| TC-TEA-06 | 高 | admin 下架 tea7；查列表/搜索/热门/随机/详情/收藏；查行与计数 | 下架 200；前台全部不可见；详情/收藏 404/40401；行与计数保留 | 全部通过，重新上架后恢复。证据：`test_admin_tea_08_toggle_links_public_visibility_and_keeps_favorites` | 通过 |
| TC-TEA-07 | 中 | 下架后查 A 清单、游客分享、B copy，再上架复查 | 清单/分享 `is_available=false`；copy 计入 skipped；上架恢复 | 清单与分享均 false；copy 跳过下架茶；上架恢复。证据：`test_admin_tea_08...` + `test_tc_share_05...` + `test_tc_share_08...` | 通过 |

### 4.3 筛选、搜索与分页（LIST，9 条）

| 编号 | 优先级 | 输入 / 操作步骤 | 预期结果 | 实际结果与证据 | 结果 |
|---|---|---|---|---|---|
| TC-LIST-01 | 高 | 在架 13 条；请求默认页与 page=2，核对 items/total | page1=12；page2 剩余；排序稳定；两页无重复遗漏 | 临时构造 13 条：page1=12、page2=1、无重复、并集=total；新茶按 created_at/id 倒序。证据：`test_tc_list_01_pagination_with_13_plus_active_teas` | 通过 |
| TC-LIST-02 | 中 | `category=green`；`category=green,oolong` | 单类与多选 OR，total 与并集一致 | 通过。证据：`test_list_filter_category_single`、`test_list_filter_category_multi_or` | 通过 |
| TC-LIST-03 | 中 | green+浙江+明前；green+福建，核对交集 | 前者仅 tea1；后者空数组/total=0/200/0 | 通过。证据：`test_list_filter_cross_dimension_and`、`test_list_filter_origin_province_prefix` | 通过 |
| TC-LIST-04 | 高 | category=black；season=夏季；sort=price；格式错误 | 全部 400/40000，不静默忽略 | 通过。证据：`test_list_invalid_enum_returns_40000` | 通过 |
| TC-LIST-05 | 中 | keyword=龙井/福建/空串/`%`/`_` | 命中对应茶；空串忽略；通配符转义，不全表 | 龙井/福建/空串通过；`%`、`_`、`\` 均被转义，返回数小于全表；管理端列表同步修复。证据：`test_tc_list_05_wildcards_are_escaped`、`test_list_keyword_matches_name_and_origin` | 通过 |
| TC-LIST-06 | 中 | 50/51/1000 字符关键词 | 50 → 200；51/1000 → 400/40000；无截断/500 | 通过。证据：`test_tc_list_06_keyword_length_boundaries`、`test_list_keyword_too_long_returns_40000` | 通过 |
| TC-LIST-07 | 中 | page=0；page_size=0/51；page=999；page_size=abc | 夹取 1/1/50；越界空数组；abc → 400/40000 | 通过，响应返回实际生效值。证据：`test_list_pagination_page_size_and_clamping`、`test_list_page_beyond_last_returns_empty_items` | 通过 |
| TC-LIST-08 | 低 | 构造同计数茶；sort=favorite 两页核对 | `favorite_count DESC, created_at DESC, id DESC`；两页无重复遗漏 | 同计数按 id DESC；13 条下 page1=12、page2=1、无重复。证据：`test_tc_list_08_favorite_sort_secondary_id_desc` | 通过 |
| TC-LIST-09 | 低 | 临时下架 tea3；查 categories/origins；hot limit 0/21；random exclude_id=1 | 黄茶 count=0 仍保留；湖南移除；limit 夹 1/20；random 不含 1 | 全部通过，测试后恢复 tea3。证据：`test_tc_list_09_categories_origins_exclude_off_shelf_and_clamp` | 通过 |

### 4.4 收藏与取消收藏（FAV，7 条）

| 编号 | 优先级 | 输入 / 操作步骤 | 预期结果 | 实际结果与证据 | 结果 |
|---|---|---|---|---|---|
| TC-FAV-01 | 高 | A 收藏 tea2，查行、计数、状态 | 200/0，true，计数 +1；1 行；状态一致 | 通过。证据：`test_fav_01_add_favorite_updates_count_and_status` | 通过 |
| TC-FAV-02 | 高 | 同客户端连续 2 次；20 线程并发同一茶 | 均 200；仅 1 行；计数 +1 | 同客户端 2 次幂等；20 线程（ThreadPoolExecutor）全部 200；最终 1 行、+1。证据：`test_fav_02_add_is_idempotent_and_concurrent`、`test_fav_08_multi_user_concurrent_add` | 通过 |
| TC-FAV-03 | 高 | A 取消 tea1，查行、计数、清单、状态 | 200/0，false，计数 -1；行删除；清单移除 | 通过。证据：`test_fav_03_remove_favorite_decrements_count` | 通过 |
| TC-FAV-04 | 中 | 连续 DELETE 2 次；10 线程并发 DELETE | 均 200/0 幂等；计数只首次 -1，不为负 | 10 线程全部 200；最终 0 行、计数 0。证据：`test_fav_04_remove_is_idempotent_and_never_negative` | 通过 |
| TC-FAV-05 | 高 | 收藏不存在 tea99；收藏下架 tea7 | 404/40400；404/40401；无新增、计数不变 | 通过。证据：`test_fav_05_missing_and_off_shelf_tea` | 通过 |
| TC-FAV-06 | 中 | A/C 查 tea1 状态；A 查下架 tea7；查 tea99 | true/false；下架可查 true；99 → 404/40400 | 通过，无跨用户信息。证据：`test_fav_06_status_is_user_scoped_and_allows_off_shelf` | 通过 |
| TC-FAV-07 | 低 | 手工置计数 0 后取消收藏 | 200/0；计数保持 0，无负数；行删除 | 通过，计数不为负。证据：`test_fav_04_remove_is_idempotent_and_never_negative` | 通过 |

### 4.5 品鉴笔记（NOTE，5 条）

| 编号 | 优先级 | 输入 / 操作步骤 | 预期结果 | 实际结果与证据 | 结果 |
|---|---|---|---|---|---|
| TC-NOTE-01 | 高 | A 收藏 tea1 写笔记；查清单；游客/B 查分享 | 200/0 写入；清单含笔记；分享不含笔记与身份 | 通过；分享条目无 tasting_note。证据：`test_note_01_save_and_read_back`、`test_tc_share_05...` | 通过 |
| TC-NOTE-02 | 高 | A 对未收藏 tea2 写笔记 | 404/40430；不建收藏行、不落笔记 | 通过。证据：`test_note_02_cannot_write_note_for_unfavorited_tea` | 通过 |
| TC-NOTE-03 | 中 | 提交 null 与 `"   "` | 均 200/0，tasting_note=null；收藏行保留 | 通过。证据：`test_note_03_clear_note_keeps_favorite_item` | 通过 |
| TC-NOTE-04 | 中 | 20,000、20,001 字符、70,000 字节 | 20k → 200；20,001 与超 TEXT → 400/40000“笔记过长”；无 500/截断 | 通过；30,000 汉字（约 90,000 字节）被 400/40000 拒绝，原笔记未破坏。证据：`test_note_04_length_limit` | 通过 |
| TC-NOTE-05 | 高 | A/B 各自写 tea1 笔记，交叉查清单与分享 | 各自独立、互不覆盖；分享不含笔记 | 通过。证据：`test_note_05_notes_are_isolated_between_users` | 通过 |

### 4.6 分享链路（SHARE，10 条）

| 编号 | 优先级 | 输入 / 操作步骤 | 预期结果 | 实际结果与证据 | 结果 |
|---|---|---|---|---|---|
| TC-SHARE-01 | 高 | 连续两次生成，查 share_tokens 与 lists | 8 位 URL-safe；第二次同 token/is_new=false；仅 1 条 active | 通过。证据：`test_share_01_generate_reuses_active_token` | 通过 |
| TC-SHARE-02 | 高 | 20 线程并发生成 | 全部 200；恰好 1 条 active；同 token，仅 1 个 is_new=true | 真实 20 线程通过。证据：`test_share_02_concurrent_generate_only_one_active` | 通过 |
| TC-SHARE-03 | 中 | 撤销 TA，再次撤销，查表 | 200/0，is_active=false、revoked_at 非空；第二次 409/40900；行保留 | 通过。证据：`test_share_03_revoke_soft_and_idempotent_error` | 通过 |
| TC-SHARE-04 | 高 | 游客访问已撤销 TR；重新生成；再访旧/新 token | 旧 token revoked=true、空列表；新 token 正常；旧 token 不可复活 | 通过。证据：`test_share_04_revoked_cannot_revive_and_new_token_required` | 通过 |
| TC-SHARE-05 | 高 | 游客访问含 tea1/2/3/7 的分享，检查字段 | tea_count=4；仅 8 个公开字段；无笔记/用户身份；下架 tea7 is_available=false | 通过；精确字段集合校验、下架灰显。证据：`test_tc_share_05_public_fields_and_off_shelf_flag` | 通过 |
| TC-SHARE-06 | 中 | 访问 ZZZZZZZZ；大小写变体访问 TB | 均 404/40410，大小写敏感 | 通过。证据：`test_share_06_unknown_and_case_sensitive_token` | 通过 |
| TC-SHARE-07 | 高 | B 撤销 A 的 TA，查状态，游客访问 | 403/40300；TA 仍 active；分享仍可看 | 通过。证据：`test_share_07_other_user_cannot_revoke` | 通过 |
| TC-SHARE-08 | 高 | C 对 B 的 TB 一键收藏（含 4 款，其中 1 款下架） | added=3、skipped=1、total=4；计数 3+1；重复 added=0 | 通过；精确 3/1/4 与重复 0/4/4，DB 行数与计数核对。证据：`test_tc_share_08_copy_added_skipped_total` | 通过 |
| TC-SHARE-09 | 中 | A copy 自己 TA；游客 copy TB；B copy 已撤销 TR | 403/40300；401/40100；409/40900；无收藏/计数变化 | 通过。证据：`test_share_09_copy_permission_and_revoked_errors` | 通过 |
| TC-SHARE-10 | 中 | 20 线程并发 copy | 全部 200；各茶恰 1 行；added 合计 3；计数各 +1 | 真实 20 线程通过。证据：`test_share_10_concurrent_copy_adds_once` | 通过 |

### 4.7 权限校验（PERM，4 条）

| 编号 | 优先级 | 输入 / 操作步骤 | 预期结果 | 实际结果与证据 | 结果 |
|---|---|---|---|---|---|
| TC-PERM-01 | 高 | 普通用户调 8 个 admin 端点；查 teas/logs/uploads | 全部 403/40300；无数据/日志/文件副作用 | 8 个端点全部 403/40300；teas 数、tea1 状态、日志最大 id、上传文件数均不变。证据：`test_tc_perm_01_02_admin_endpoints_have_no_side_effects`、`test_admin_perm_02...` | 通过 |
| TC-PERM-02 | 高 | 无 Cookie 调 stats/teas/upload | 全部 401/40100；无副作用 | 8 个端点全部 401/40100；副作用快照不变。证据：`test_tc_perm_01_02...`、`test_admin_perm_01...` | 通过 |
| TC-PERM-03 | 高 | A 查清单；B 查清单；A 写 tea2 笔记；A 撤销 TB | 各自清单；A 404/40430；A 403/40300；TB 仍有效 | 通过。证据：`test_perm_03_lists_are_user_scoped`、`test_share_07...` | 通过 |
| TC-PERM-04 | 中 | admin 收藏；改库为 user；不重登调 stats；改回再调 | 200/0；403/40300；200/0；会话未退出 | 通过，角色实时读库。证据：`test_tc_perm_04_admin_role_is_read_live` | 通过 |

### 4.8 文件上传（UPLOAD，5 条）

| 编号 | 优先级 | 输入 / 操作步骤 | 预期结果 | 实际结果与证据 | 结果 |
|---|---|---|---|---|---|
| TC-UPLOAD-01 | 高 | 上传 JPEG/PNG/WebP；访问 URL；查日志与磁盘 | 均 200/0；UUID 路径；size/content_type 正确；可访问；日志 upload_image | 通过。证据：`test_admin_upload_01_supports_jpeg_png_webp_with_uuid_filename` | 通过 |
| TC-UPLOAD-02 | 高 | 上传 5MB+1 字节 JPEG | 413/41300；无落盘、无日志 | 通过。证据：`test_admin_upload_02_oversize_returns_413` | 通过 |
| TC-UPLOAD-03 | 高 | 文本改名 jpg、SVG、GIF、可执行改名 png | 全部 415/41500；无落盘；魔数校验 | 通过。证据：`test_admin_upload_03_rejects_non_image_by_magic_and_empty_file` | 通过 |
| TC-UPLOAD-04 | 中 | 文件名 `../../evil.jpg`、`..\..\evil.jpg` | 200 或安全拒绝；落盘在 uploads/YYYY/MM/UUID；URL 无 `..` | 通过。证据：`test_admin_upload_04_path_traversal_attempt_is_stored_safely` | 通过 |
| TC-UPLOAD-05 | 中 | 0 字节；不传 file；普通用户上传 | 400/40000；400/40000；403/40300；均无落盘 | 通过。证据：`test_admin_upload_03...`、`test_admin_perm_02...` | 通过 |

### 4.9 异常状态与防御（DEF，4 条）

| 编号 | 优先级 | 输入 / 操作步骤 | 预期结果 | 实际结果与证据 | 结果 |
|---|---|---|---|---|---|
| TC-DEF-01 | 中 | 畸形 JSON；注册附 role=admin；page_size=abc；text/plain 提交 JSON | 全部 400/40000；role 不落库；无堆栈/SQL/表名 | 通过；register 未知字段拒绝且无用户落库。证据：`test_def_01_illegal_requests_map_to_40000` | 通过 |
| TC-DEF-02 | 中 | admin 提交 10MB shape_desc；提交 70KB 超长字段；查 DB/日志 | 413/41300 或 400/40000，不得 500；无 DB 行 | 10MB → **413/41300**（6MB 中间件）；70KB 超 TEXT → **400/40000**（DataError 映射）；teas 行数不变，无堆栈/SQL 泄露。证据：`test_tc_def_02_oversize_body_is_rejected_without_500` | 通过 |
| TC-DEF-03 | 高 | 注入 RuntimeError 后调 /teas | 500/50000 通用错误；无堆栈/SQL；日志有堆栈；恢复后 200 | 通过，服务未崩溃。证据：`test_def_03_unhandled_exception_returns_generic_500` | 通过 |
| TC-DEF-04 | 高 | admin/admin123 登录；执行轮换脚本；旧/新密码验证 | 脚本成功；旧密码 401；新密码 200；`$2b$10$`；仓库配置无内置 admin123 | 轮换脚本退出码 0 且输出不含明文；旧密码 401/40110；新密码登录 200 且 `/auth/me` 为 admin；哈希 `$2b$10$`；`config.py`/`.env.example` 静态检查通过；finally 恢复原密码。证据：`test_tc_def_04_admin_password_rotation` | 通过 |

---

## 5. DEF-02 执行证据（初测与修复后）

初测使用真实 TestClient 分两支执行，记录缺陷：

```text
分支①：admin 登录 200/0
       POST /api/v1/admin/teas，shape_desc = "x" * (10 * 1024 * 1024)
       → HTTP 500 / code 50000
       → teas 行数 before=6 / after=6
       → 响应文本未包含 Traceback / SQL / 表名

分支②：注册用户 200/0 → 收藏临时茶 200/0
       PUT /api/v1/lists/notes/{tea_id}，content = "x" * (10 * 1024 * 1024)
       → HTTP 400 / code 40000 / message "笔记过长"
       → favorite_items.tasting_note 仍为 null
       → 临时茶与用户已清理
```

修复后由 `test_tc_def_02_oversize_body_is_rejected_without_500` 固化回归：

```text
1) 10MB shape_desc
   → HTTP 413 / code 41300（Content-Length > 6MB，中间件直接拒绝）
   → teas 行数前后不变
2) 70,000 字符 shape_desc（超过 MySQL TEXT 容量）
   → HTTP 400 / code 40000（SQLAlchemy DataError 映射为参数校验失败）
   → teas 行数前后不变
3) 响应体均不含 Traceback / SQL / 表名
```

结论：分支①、②均符合 TEST_PLAN 的“413/41300 或 400/40000，不得 500”预期，D-03 关闭。

---

## 6. 缺陷清单与修复记录

> 修复原则：先复现、再定位模块与根因、评估影响面、修复代码、补测试、重跑失败用例与回归；未删除用例、未放宽断言、未绕过权限、未修改已确认业务规则。四项产品缺陷均已关闭，另记录一项测试代码构造缺陷（D-05）。

### D-01（S2，中优先级，已修复）过期分支无法按 TEST_PLAN 方式验证

- 用例与错误：TC-AUTH-07；`AssertionError: assert 480 is None`，`verify_session_token(token, max_age_days=0)` 返回 uid。
- 模块：[security.py](file:///d:/项目二/backend/app/core/security.py#L43-L56)（`verify_session_token`）。
- 根因（两层）：
  1. 初测代码 `(max_age_days or settings.SESSION_EXPIRE_DAYS)` 把 `0` 当作假值，回落到 30 天；
  2. 改为 `is None` 判断后仍失败：itsdangerous 按整数秒比较 `age > max_age`，同秒签发的令牌 `age=0`，`0 > 0` 为假，`max_age=0` 不会立即过期。
- 影响面：`verify_session_token` 仅用于会话校验；默认 30 天逻辑不变；生产不传该参数，行为不变；测试与内部调用可用 0/负数模拟立即过期。
- 修复：解析前显式判断 `max_age_days is not None and max_age_days <= 0` → 直接返回 `None`；保留 `is None` 回落默认值。
- 测试：AUTH-07 增加 `max_age_days=0` 与 `-1` 均返回 None、默认参数仍返回 uid 的断言。
- 回归：单用例通过；后端全量 105 passed。

### D-02（S2，中优先级，已修复）搜索通配符未转义

- 用例与错误：TC-LIST-05；`AssertionError: %`、`assert 6 < 6`，`%`/`_` 返回全部 6 条。
- 模块：[tea_repo.py](file:///d:/项目二/backend/app/repositories/tea_repo.py#L16-L28)（公开列表）、[admin_repo.py](file:///d:/项目二/backend/app/repositories/admin_repo.py#L14-L25)（后台列表）。
- 根因：Repository 直接拼接 `%{keyword}%`，未转义 LIKE 元字符 `%`、`_`、`\`，生成 `LIKE '%%%'`。
- 影响面：仅关键词过滤；不影响分类/产地/季节筛选与排序；不是认证/权限绕过，但可让搜索返回全表，属 S-21 输入边界问题。
- 修复：两处新增 `_escape_like()`，按 `\` → `\\`、`%` → `\%`、`_` → `\_` 转义，并在 `like(..., escape="\\")` 显式指定转义符。
- 测试：LIST-05 覆盖 `%`、`_`、`\`，并补管理端 `/admin/teas` 的 `%`/`_` 断言；断言为“结果数小于全表”，与原用例口径一致。
- 回归：单用例通过；全量 105 passed。

### D-03（S2，中优先级，已修复）超大体量茶品字段返回 500

- 用例与错误：TC-DEF-02 分支①；10MB `shape_desc` 返回 **HTTP 500 / code 50000**。
- 模块：[main.py](file:///d:/项目二/backend/app/main.py)（请求入口）、[response.py](file:///d:/项目二/backend/app/core/response.py#L66-L77)（异常映射）、[config.py](file:///d:/项目二/backend/app/core/config.py)（上限配置）。
- 根因：无请求体大小限制；`shape_desc` 等自由文本在 API 契约中未规定长度，写入 MySQL TEXT（约 64KB）触发 SQLAlchemy `DataError`，未被业务异常处理器覆盖，退化为 500。
- 影响面：仅超限请求路径；正常茶品录入/编辑不受影响；未改 Schema 字段约束，避免触碰 API 契约（契约未定义上限，补 `max_length` 属 C 类）。
- 修复：
  1. `MAX_REQUEST_BODY_MB=6`，在 CORS 之前注册中间件，按 `Content-Length` 拒绝超限请求，返回 413/41300；后注册的 CORS 成为最外层，保证 413 也带跨域头；
  2. 注册 `DataError` 处理器，返回 400/40000，仅记录方法/路径/异常类型，不写超长参数与 SQL。
- 测试：新增 `test_tc_def_02_oversize_body_is_rejected_without_500`：10MB → 413/41300；70,000 字符 → 400/40000；两次均断言 `teas` 行数不变。
- 回归：单用例通过；全量 105 passed。网关层 `client_max_body_size` 仍建议生产配置（部署项，不在本次代码范围）。

### D-04（S1，高优先级，已修复）管理员密码轮换脚本缺失

- 用例与错误：TC-DEF-04 未执行；全仓无 `app.scripts.rotate_admin_password`；`config.py` 内置 `admin123`。
- 模块：[config.py](file:///d:/项目二/backend/app/core/config.py)（默认密码）、[.env.example](file:///d:/项目二/backend/.env.example)（示例配置）、新增 [rotate_admin_password.py](file:///d:/项目二/backend/app/scripts/rotate_admin_password.py)（轮换 CLI）。
- 根因：缺少管理员密码轮换能力；生产配置内置默认密码，违反 SECURITY S-31；同时导致高优先级用例无法执行。
- 影响面：仅管理员初始密码来源与运维脚本；不影响登录/会话/权限逻辑；`database/init.sql` 的开发/演示例外保持 `admin123`（S-31 允许范围），未修改。
- 修复：
  1. 新增 `python -m app.scripts.rotate_admin_password --password ...` 或 `NEW_ADMIN_PASSWORD` 环境变量；复用 `user_repo` 与 `hash_password`（bcrypt cost=10）；输出不含明文；
  2. `config.py` 默认 `ADMIN_PASSWORD=""`，`.env.example` 清空并补充轮换命令；本地 `backend/.env` 仍由开发者注入，未纳入版本控制。
- 测试：新增 `test_tc_def_04_admin_password_rotation`：轮换成功 → 旧密码 401/40110 → 新密码登录 200 且 role=admin → 哈希 `$2b$10$` → `config.py`/`.env.example` 不含 `admin123` → `finally` 恢复原密码。
- 回归：纳入 §7.1 门禁批次，9 passed；全量 105 passed。

### D-05（测试代码缺陷，已修复）AUTH-07 末位篡改构造不可靠

- 用例：TC-AUTH-07 步骤①。
- 现象：`token[:-1] + ("A" if token[-1] != "A" else "B")` 偶发被服务端接受并返回 200。
- 根因：itsdangerous 签名为 32 字节 HMAC 的 base64url 编码（43 字符），末位字符只有高位有效，低位未参与解码；`A/B/C/D` 共享同一高位，互换后解码字节完全相同，签名仍然有效。因此“末位换成 A/B”并不保证篡改生效。
- 修复：仍按 TEST_PLAN“篡改最后一个字符”执行，但改为翻转该 base64url 索引的高位（`index ^ 32`），确保解码结果必然不同；断言仍为 401/40100，未放宽。
- 影响面：仅测试构造，生产代码无需修改；该结论已写入 build-log 问题复发台账。

### 修复影响与边界确认

- 未修改 PRD、API_CONTRACT、openapi.yaml、DATA_MODEL、init.sql、SECURITY 规则口径；未新增/删除端点或字段。
- 未修改认证/权限机制，未绕过任何权限校验；未删除测试，未放宽断言。
- 唯一配置行为变化：`ADMIN_PASSWORD` 默认值改为空，属向 SECURITY S-31 对齐；本地/测试需通过 `.env` 注入。

---

## 7. 并发证据留痕

4 条并发用例均使用 `ThreadPoolExecutor` 真实并发，不是顺序调用：

| 用例 | 线程数 | 测试函数 | 最终数据库断言 | 结果 |
|---|---:|---|---|---|
| TC-FAV-02 | 20 | `test_fav_02_add_is_idempotent_and_concurrent`、`test_fav_08_multi_user_concurrent_add` | favorite_items 仅 1 行；favorite_count 只 +1；无 409/500 | 通过 |
| TC-FAV-04 | 10 | `test_fav_04_remove_is_idempotent_and_never_negative` | 全部 200/0；最终 0 行；计数 0，不为负 | 通过 |
| TC-SHARE-02 | 20 | `test_share_02_concurrent_generate_only_one_active` | 全部 200/0；active token 恰好 1 条；token 相同，仅 1 个 is_new=true | 通过 |
| TC-SHARE-10 | 20 | `test_share_10_concurrent_copy_adds_once` | 全部 200/0；每款茶恰好 1 行；added 合计 3；计数各 +1 | 通过 |

---

## 8. 端到端闭环证据

### 8.1 接口级 8 步闭环（真实 DB）

测试函数：`backend/tests/test_g5_system.py::test_tc_e2e_mvp_closure`

| 步骤 | 操作 | 实际结果 |
|---|---|---|
| 1 | 游客浏览列表/详情/分类 | 200/0 |
| 2 | 注册用户 A | 200/0，Cookie 下发 |
| 3 | A 收藏临时茶 | 200/0，is_favorited=true |
| 4 | A 写笔记 | 200/0，tasting_note="闭环笔记" |
| 5 | A 生成分享 | 200/0，8 位 URL-safe token，is_new=true |
| 6 | A 登出 | 200/0 |
| 7 | 游客打开分享 | 200/0，tea_count=1，条目无笔记 |
| 8 | 用户 B 登录并一键收藏 | 200/0，added=1；DB 中 A 笔记保留、B 新增收藏、计数=2 |

说明：分享所有者不能 copy 自己的清单（业务规则），因此第 8 步由第二个用户 B 执行，符合 MVP 闭环语义。

### 8.2 浏览器真实操作（3 组）

| 场景 | 操作与观察 | 结果 | 截图 |
|---|---|---|---|
| 登录与首页 | `/login` 用测试账号登录，跳转首页；可见 6 款种子茶卡片（白毫银针在收藏区重复出现一次），无错误 toast | PASS | `file:///C:/Users/yuan/.trae-cn/trae-browser-screenshots/6af03ab937064e39234fb80d/shot-20261108-091012-416203100-91b04c60-be06-48f2-b0bf-40ea330f04b7.jpg` |
| 收藏与我的收藏 | `/teas/1` 点击“加入我的清单”→ 变为“已在我的清单”，计数 2480→2481；`/my` 显示 6 款（含西湖龙井），无错误 toast | PASS | `file:///C:/Users/yuan/.trae-cn/trae-browser-screenshots/6af03ab937064e39234fb80d/shot-20261108-091044-556571300-4c611052-d377-4dc2-bf37-7823e7535b70.jpg` |
| 管理员后台 | `/admin/login` 用 admin/admin123 登录，跳转 `/admin`，统计：总数 6、上架 6、下架 0、六类各 1 | PASS | `file:///C:/Users/yuan/.trae-cn/trae-browser-screenshots/6af03ab937064e39234fb80d/shot-20261108-091130-102893200-a72ae818-7943-46b4-b617-874dfd1f2ed0.jpg` |

浏览器测试账号 `ui01290` 及其收藏数据已在测试后清理，种子 `favorite_count` 已回滚；管理后台登录使用开发种子密码。

---

## 9. 未执行项

| 编号 | 优先级 | 原因 | 结论 |
|---|---|---|---|
| GitHub Actions CI | - | 本次未在 GitHub Actions 实际运行 | **未运行**，不标记通过 |
| 生产网关请求体限制 | - | `client_max_body_size` 属部署配置，本次仅完成应用层 6MB 兜底 | 部署时需配置并复测 |

TC-DEF-04 修复后已真实执行并通过，不再列为未执行项。

---

## 10. 发布判定与后续建议

### 10.1 判定

- **高优先级门禁：通过**（32/32，无 skip）。
- 60 条用例全部通过；D-01～D-05 均已关闭。
- 后端全量：105 passed；前端 lint/format/typecheck/30 单测/构建全部通过；Ruff 与 `check_all.py` 全部通过。
- **测试范围内具备发布条件**；CI 尚未在 GitHub Actions 实跑，上线前需补跑。

### 10.2 遗留与发布建议

1. 在 GitHub Actions 实际运行 CI，确认与本机结果一致；未运行前不宣称 CI 通过。
2. 生产 Nginx 配置 `client_max_body_size 6m`，与应用层中间件形成双层防护，并复测 413 响应。
3. 部署时通过环境变量注入 `ADMIN_PASSWORD` 与强随机 `SECRET_KEY`，随后执行 `python -m app.scripts.rotate_admin_password` 轮换种子密码。
4. `ADMIN_PASSWORD` 默认值已为空的变更需同步到部署文档/运维说明，避免新环境无法初始化管理员。
5. 继续保留 `backend/.env` 与 `database/init.sql` 的开发/演练种子，不纳入生产部署。

### 10.3 复现命令

```powershell
cd d:\项目二\backend
python -m ruff check app tests
python -m ruff format --check app tests
python -m pytest -q
python -m pytest -q tests/test_g5_system.py::test_tc_auth_07_tampered_foreign_and_expired_session tests/test_g5_system.py::test_tc_list_05_wildcards_are_escaped tests/test_g5_system.py::test_tc_def_02_oversize_body_is_rejected_without_500 tests/test_g5_system.py::test_tc_def_04_admin_password_rotation

cd d:\项目二\frontend
npm run lint; npm run format:check; npm run typecheck; npm run test:run; npm run build

cd d:\项目二
python scripts/check_all.py
```

---

## 11. 变更与执行留痕

- 初测新增 `backend/tests/test_g5_system.py` 21 条补充用例；修复阶段新增 DEF-02/DEF-04 两条并强化 AUTH-07，共 23 条，函数名含 TC 编号。
- 修复涉及生产代码：
  - [security.py](file:///d:/项目二/backend/app/core/security.py)：`max_age_days <= 0` 显式立即过期；
  - [tea_repo.py](file:///d:/项目二/backend/app/repositories/tea_repo.py) / [admin_repo.py](file:///d:/项目二/backend/app/repositories/admin_repo.py)：LIKE 通配符转义；
  - [main.py](file:///d:/项目二/backend/app/main.py)：6MB 请求体中间件；
  - [response.py](file:///d:/项目二/backend/app/core/response.py)：`DataError → 400/40000`；
  - [config.py](file:///d:/项目二/backend/app/core/config.py) / [.env.example](file:///d:/项目二/backend/.env.example)：管理员默认密码置空、新增请求体上限；
  - 新增 [rotate_admin_password.py](file:///d:/项目二/backend/app/scripts/rotate_admin_password.py) 与 `app/scripts/__init__.py`。
- 未修改 `TEST_PLAN.md` 用例口径、未删除测试、未放宽断言、未绕过权限、未修改已确认业务规则/API 契约/表结构。
- 临时测试数据（用户、茶品、收藏、分享、上传文件）均在用例 `finally` 中清理；浏览器测试账号已清理；DEF-04 轮换后已在 `finally` 恢复原密码。
- 本次测试未在 GitHub Actions 实际运行，CI 标记为「未运行」。
