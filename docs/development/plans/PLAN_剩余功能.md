# 剩余功能实施总方案（已确认）

> 状态：**已确认**（2026-11-09 用户确认，实施后由 build-log 引用）
> 日期：2026-11-09
> 范围：**批次一~四**（S1/S2/S3/S6/S7/S17 + S8/S14/S15/S16 + S9 + S10–S13）
> 本期不做：批次五（R1–R5 五大内容板块），另开一期
> 不在范围：PRD X1–X13（明确暂不实现）
>
> 确认结论：
> 1. 实施范围：批次一~四，R1–R5 延后
> 2. S15 等级：4 档（茶客 0–4 / 茶友 5–19 / 茶人 20–49 / 茶师 ≥50），实时计算不改表
> 3. S9 删除清单：条目**迁移到默认清单**，不丢数据
> 4. 交付节奏：**先都不提交**，全部留在工作区等用户指令
> 5. S14：按「用户名 + IP」双维度锁定（推荐值）
> 6. S8：允许引入纯前端 `qrcode` 依赖生成二维码（推荐值）

---

## 1. 总览

当前基线：MVP（M1–M7）全部完成；S4/S5 已完成；后端 33 端点、8 张表、119 条测试通过。

剩余工作按「风险 + 依赖」分 5 批，每批可独立交付与回归：

| 批次 | 内容 | 分级 | 表结构变更 | 契约变更 |
|---|---|---|---|---|
| 一 | S1、S2、S3、S6、S7、S17 | B（含 1 处表字段新增） | S2、S17 | 是（新增参数/端点） |
| 二 | S14、S15、S16、S8 | C | S14 新表 | 是 |
| 三 | S9 多收藏清单 | C | 是（改造 2 表） | 大范围 |
| 四 | S10–S13 用户贡献 + 审核 | C | 2 张新表 | 是 |
| 五 | R1–R5 五大内容板块 | C | 2 张新表 | 是 |

**统一约束**（每批都适用）：
- 五层架构：Router 只收参 → Service 业务 → Repository 查询 → Schema 序列化
- 统一响应体 `{code, message, data}`，新增错误码必须登记到 `core/response.py` 与 API_CONTRACT
- 每个功能同步更新：`API_CONTRACT.md` + `openapi.yaml` + 前端 `types/`
- 表结构变更一律 Alembic 迁移，禁止手工 ALTER
- 每批交付前：`pytest` 全量 + `npm run lint/typecheck/test:run` + `check_all.py`
- 每批回填 `harness/build-log.md`

---

## 2. 批次一：体验增强（低风险，建议先做）

### S2 筛选扩展至 5 档（含表字段）
- **表变更**：`teas` 新增 `price_min INT UNSIGNED NULL`、`price_max INT UNSIGNED NULL`（单位：元/斤）
  - 原因：现 `price_range` 是「500-3000元/斤」字符串，无法范围查询
  - 迁移 0003 + `init.sql` + `DATA_MODEL.md`
  - 后台编辑页新增两个数值输入；种子 36 款茶按 `price_range` 回填
- **API**：`GET /teas` 新增可选参数 `fermentation`、`price_min`、`price_max`
- **前端**：筛选栏新增「发酵程度」单选、「价格区间」双下拉
- **测试**：新增 4 条（发酵筛选、价格区间、区间边界、与 AND 叠加）

### S1 列表页 AND/OR 切换
- **API**：`GET /teas` 新增 `filter_mode=and|or`（默认 `and`，向后兼容）
- **逻辑**：`or` 时 category/origin/season 用 `or_()` 组合；分页与排序不变
- **前端**：筛选栏加分段控件「同时满足 / 任一满足」
- **测试**：新增 3 条

### S6 详情页相关推荐
- **API**：新增 `GET /teas/{id}/related?limit=4`
- **规则**：同茶类优先 → 同产地补足 → 热门兜底；排除自身与下架
- **前端**：详情页底部「你可能还喜欢」卡片行
- **测试**：新增 3 条（同茶类、排除自身、下架不出现）

### S7 首页小贴士预览
- **API**：新增 `GET /tips/latest?limit=3`，返回 `tea_id/tea_name/category/summary`
- **排序**：`tea_tips.updated_at DESC`（无则该字段补迁移）
- **前端**：首页新增「茶知识 · 小贴士」区块，点击进详情
- **测试**：新增 2 条

### S3 六大摘要对比
- **纯前端**：新页面 `/compare`，复用 `GET /teas?category=x&page_size=1` 六次
- **展示**：六列对比表（茶类/代表茶/外形/汤色/香气/滋味/水温/投茶量）
- **无后端变更**；入口放列表页顶部
- **测试**：Vitest 纯函数（对比数据组装）+ 浏览器冒烟

### S17 热门 7 天权重
- **不改表结构**，只改查询：`hot_score = 7天收藏数 × 3 + favorite_count`
- **迁移**：`favorite_items` 新增索引 `(created_at, tea_id)`
- **API 行为变化**：`GET /teas/hot` 排序口径变更（响应字段不变）
- **测试**：新增 2 条（权重排序、无 7 天数据回退总量）

---

## 3. 批次二：账号与个性化

### S14 登录失败锁定
- **新表**：`login_attempts(id, username, ip, failed_at)`，索引 `(username, failed_at)`、`(ip, failed_at)`
- **规则**：15 分钟内同一用户名 **或** 同一 IP 失败 ≥ 5 次 → 锁定 15 分钟
- **响应**：`42900` / HTTP 429「尝试过于频繁，请 15 分钟后再试」
- **清理**：每次登录顺带删除 24 小时前记录
- **安全**：SECURITY.md 新增 S-33；不记录密码明文
- **迁移**：0004
- **测试**：新增 4 条（第 5 次失败锁定、锁定期内拒绝、到期解锁、不泄露账号是否存在）

### S15 用户等级展示
- **不改表**：实时聚合 `favorite_items` 数量 + 非空 `tasting_note` 数量
- **建议档位**（**需确认**）：
  | 等级 | 条件 |
  |---|---|
  | 茶客 | 0–4 收藏 |
  | 茶友 | 5–19 收藏 |
  | 茶人 | 20–49 收藏 |
  | 茶师 | ≥ 50 收藏 |
- **API**：`GET /me/stats` 返回收藏数、笔记数、等级名、下一级差距
- **前端**：我的清单页展示等级徽章
- **测试**：新增 3 条（边界 0/4/5/49/50）

### S16 个性化推荐
- **API**：新增 `GET /teas/recommended?limit=1`
- **规则**：登录用户按收藏的茶类分布加权随机；无收藏/未登录回退现有随机
- **前端**：首页「随机发现」登录后标题改为「为你推荐」
- **测试**：新增 3 条

### S8 分享海报
- **纯前端**：canvas 绘制（站点底纹 + 茶图 + 清单名 + 前 6 款茶名 + 二维码 + 域名），导出 PNG
- **依赖**：引入 `qrcode`（仅前端，约 20KB）——**需确认**
- **不落服务端存储**，无 API 变更
- **测试**：浏览器冒烟（生成可下载、二维码可扫）

---

## 4. 批次三：多收藏清单（S9）

- **表变更**：
  - `collection_lists`：移除 `uk_list_user(user_id)`，新增 `idx_list_user(user_id)`、`is_default TINYINT`、保留 `title`
  - `favorite_items`：新增 `list_id`，唯一键改为 `uk_favorite_list_tea(list_id, tea_id)`；按用户默认清单回填
  - 迁移 0005（含数据回填脚本）
- **API 重构**（契约大改）：
  - `GET /lists` 改为清单数组
  - `POST /lists` 创建（上限 10 个）
  - `PUT /lists/{id}` 改名
  - `DELETE /lists/{id}`：默认清单不可删；**条目迁移到默认清单 或 一并删除 —— 需确认**
  - 收藏接口新增 `list_id`
  - 分享支持指定清单
- **前端**：我的清单页改为「清单侧栏 + 条目区」
- **测试**：重写 lists/favorites 相关用例，新增 8 条

---

## 5. 批次四：用户贡献 + 审核（S10–S13）

- **新表**：
  - `contributions(id, user_id, type ENUM('new_tea','article'), payload JSON, status ENUM('pending','approved','rejected'), reject_reason, reviewer_id, reviewed_at, created_at)`
  - `tea_name_category_map(name, category)`（名品-茶类映射，做第一层校验）
- **API**：
  - 用户：`POST /contributions`、`GET /contributions/mine`、`DELETE /contributions/{id}`（仅 pending）
  - 管理员：`GET /admin/contributions?status=`、`POST /admin/contributions/{id}/approve`、`POST /admin/contributions/{id}/reject`
- **双层校验**：① 茶名与茶类必须在映射表匹配；② 管理员人工审核
- **前端**：投稿页、我的提交记录页、管理员审核页（Element Plus）
- **明确不做**：富文本与图片投稿（X7）
- **测试**：新增 8 条

---

## 6. 批次五：R1–R5 五大内容板块

- **新表**：
  - `content_types(id, code ENUM('teaware','origin','culture','brand','knowledge'), name)`
  - `content_items(id, type_id, title, summary, body TEXT, cover_image, sort_order, is_active, created_at, updated_at)`
- **API**：`GET /contents?type=`、`GET /contents/{id}`、`GET /content-types`、管理员 CRUD（4 个）
- **前端**：导航新增「茶文化」下拉，5 个列表页 + 通用详情页；管理后台「内容管理」
- **素材**：沿用 CC0 图库 + 统一占位兜底
- **测试**：新增 6 条

---

## 7. 需要你拍板的 6 个决策点

1. **S15 等级档位**：是否采用上表 4 档（茶客/茶友/茶人/茶师），阈值 5/20/50？
2. **S9 删除清单**：其中条目「迁移到默认清单」还是「一并删除」？
3. **S8 二维码**：是否允许引入前端依赖 `qrcode`？
4. **S14 锁定维度**：仅按用户名，还是「用户名 + IP」双维度（推荐双维度）？
5. **R1–R5 是否本期做**：工作量最大（等于再做一个模块）；可选「先做批次一~四，R1–R5 另开一期」。
6. **交付节奏**：每批完成即可提交，还是全部做完一次性提交？

---

## 8. 建议实施顺序

批次一 → 批次二 → 批次三 → 批次四 → （视决策）批次五。

理由：批次一不改核心结构、风险最低且能立刻看到效果；批次三是结构性改造，放在单清单功能稳定后；批次四依赖审核流程；批次五与现有茶品模块耦合最低，可最后独立推进。
