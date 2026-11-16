-- ============================================================
-- 茶·图鉴 —— 数据库初始化脚本（MySQL 5.7.19+）
-- 依据：docs/architecture/DATA_MODEL.md v1.0
-- 范围：MVP 9 张表 + 贡献 2 张表 + 内容平台 2 张表 + 冲泡教程 1 张表（共 14 张）
-- 编码：UTF-8（无 BOM） / 字符集 utf8mb4 / 排序规则 utf8mb4_unicode_ci
--
-- 使用方式（在 MySQL 客户端中执行）：
--   mysql -u root -p < database/init.sql
--
-- 注意：
--   1. 脚本不包含 DROP TABLE，重复执行会在建表阶段报错，避免误删已有数据。
--      如需重建，请手动删除数据库后再执行。
--   2. 种子数据中的 favorite_count 为演示热度值，并非由 favorite_items 推导，
--      正式运营数据以收藏操作维护（详见 DATA_MODEL.md §6）。
--   3. 管理员初始账号：admin / admin123（bcrypt cost=10），上线前必须修改密码。
-- ============================================================

SET NAMES utf8mb4;
SET time_zone = '+00:00';

CREATE DATABASE IF NOT EXISTS tea_guide
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE tea_guide;

-- ------------------------------------------------------------
-- 1. users —— 用户账号（PRD §4.3 / FR-4.1 / FR-4.2）
-- ------------------------------------------------------------
CREATE TABLE users (
  id            INT UNSIGNED      NOT NULL AUTO_INCREMENT,
  username      VARCHAR(32)       NOT NULL                COMMENT '用户名，3-20 字符，中文/英文/数字',
  password_hash VARCHAR(255)      NOT NULL                COMMENT 'bcrypt 哈希（60 字符）',
  role          ENUM('user','admin') NOT NULL DEFAULT 'user' COMMENT '角色：user 注册用户 / admin 管理员',
  avatar_url    VARCHAR(255)      NULL                    COMMENT '头像地址：/uploads/... 或预置 /avatars/tea-0X.svg',
  session_version INT UNSIGNED    NOT NULL DEFAULT 0      COMMENT '会话版本号：改密后 +1，旧 Cookie 立即失效',
  created_at    DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_users_username (username)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci
  COMMENT = '用户账号与角色（PRD §3.1 / §4.3）';

-- ------------------------------------------------------------
-- 2. teas —— 茶品图鉴卡片（PRD §4.1 / FR-1.x / FR-2.x / FR-6.x）
-- 索引说明：不建 name 单列索引（关键词为 LIKE '%词%' 前置通配，无法命中 B-tree）
-- ------------------------------------------------------------
CREATE TABLE teas (
  id                     INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  name                   VARCHAR(100)  NOT NULL               COMMENT '茶品名称',
  category               ENUM('green','white','yellow','red','oolong','dark','reprocessed') NOT NULL
                                                               COMMENT '七大茶类',
  origin                 VARCHAR(200)  NOT NULL               COMMENT '产地：省级 + 产区，如 浙江 杭州 西湖狮峰',
  season                 ENUM('明前','雨前','春茶','夏茶','秋茶','冬茶') DEFAULT NULL
                                                               COMMENT '采摘季节（选填）',
  fermentation           ENUM('不发酵','微发酵','半发酵','全发酵','后发酵') DEFAULT NULL
                                                               COMMENT '发酵程度（选填）',
  price_range            VARCHAR(32)   DEFAULT NULL           COMMENT '价格区间（选填，文案未定稿，应用层校验）',
  price_min              INT UNSIGNED  DEFAULT NULL           COMMENT '价格下限（元/斤，S2 五档筛选）',
  price_max              INT UNSIGNED  DEFAULT NULL           COMMENT '价格上限（元/斤，S2 五档筛选）',
  representative_variety VARCHAR(100)  DEFAULT NULL           COMMENT '代表品类（选填）',
  shape_desc             TEXT          NOT NULL               COMMENT '外形描述（必填）',
  soup_desc              TEXT          NOT NULL               COMMENT '汤色描述（必填）',
  aroma_desc             TEXT          NOT NULL               COMMENT '香气描述（必填）',
  taste_desc             TEXT          NOT NULL               COMMENT '滋味描述（必填）',
  water_temp             DECIMAL(4,1)  DEFAULT NULL           COMMENT '冲泡水温（摄氏度，70-100）',
  tea_amount             DECIMAL(4,1)  DEFAULT NULL           COMMENT '投茶量（克）',
  brew_time              DECIMAL(4,1)  DEFAULT NULL           COMMENT '浸泡时间（秒）',
  main_image_url         VARCHAR(500)  DEFAULT NULL           COMMENT '主图 URL（PRD 必填，应用层强制）',
  video_url              VARCHAR(500)  DEFAULT NULL           COMMENT '视频介绍 mp4 同源 URL（S5，ADR-0003；≤3 分钟 ≤50MB，应用层校验）',
  video_duration         INT UNSIGNED  DEFAULT NULL           COMMENT '视频时长（秒，≤180，应用层校验）',
  is_active              TINYINT(1)    NOT NULL DEFAULT 1     COMMENT '1 上架 / 0 下架（FR-6.3）',
  favorite_count         INT UNSIGNED  NOT NULL DEFAULT 0     COMMENT '冗余收藏计数（排序与卡片展示）',
  created_at             DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at             DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_teas_active_category (is_active, category),
  KEY idx_teas_active_created  (is_active, created_at),
  KEY idx_teas_active_favorite (is_active, favorite_count)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci
  COMMENT = '茶品图鉴卡片（PRD §4.1）';

-- ------------------------------------------------------------
-- 3. tea_tips —— 官方小贴士（PRD §4.1 小贴士区 / FR-6.4）
-- ------------------------------------------------------------
CREATE TABLE tea_tips (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  tea_id         INT UNSIGNED NOT NULL,
  history        TEXT         DEFAULT NULL COMMENT '历史典故（空则前端隐藏）',
  suitable       TEXT         DEFAULT NULL COMMENT '适合人群（空则前端隐藏）',
  misconception  TEXT         DEFAULT NULL COMMENT '冲泡误区（空则前端隐藏）',
  official_note  TEXT         DEFAULT NULL COMMENT '品鉴笔记（官方，空则前端隐藏）',
  created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_tea_tips_tea_id (tea_id),
  CONSTRAINT fk_tea_tips_tea FOREIGN KEY (tea_id) REFERENCES teas (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci
  COMMENT = '官方小贴士，与茶品 1:1（FR-6.4）';

-- ------------------------------------------------------------
-- 3.1 tea_media —— 茶品图片集（PRD S4 / ADR-0003）
-- 1:N 关联；物理删除（不做软失效），随茶品级联；上限 9 张由应用层校验
-- ------------------------------------------------------------
CREATE TABLE tea_media (
  id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
  tea_id      INT UNSIGNED NOT NULL,
  image_url   VARCHAR(500) NOT NULL                COMMENT '图片 URL（同源 /uploads/...）',
  sort_order  INT          NOT NULL DEFAULT 0      COMMENT '展示顺序，ASC',
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_tea_media_tea (tea_id, sort_order),
  CONSTRAINT fk_tea_media_tea FOREIGN KEY (tea_id) REFERENCES teas (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci
  COMMENT = '茶品图片集（PRD S4，ADR-0003；物理删除，上限 9 张由应用层校验）';

-- ------------------------------------------------------------
-- 3.2 tea_brewing_guides —— 分步冲泡教程（ADR-0005，与茶品 1:1）
-- steps 为 JSON 数组：[{"title","detail","tip"}]；3–8 步与字段长度由应用层校验
-- ------------------------------------------------------------
CREATE TABLE tea_brewing_guides (
  id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  tea_id     INT UNSIGNED NOT NULL,
  intro      VARCHAR(200) DEFAULT NULL COMMENT '一句话总览',
  steps      JSON         NOT NULL     COMMENT '步骤数组：[{title,detail,tip}]',
  caution    TEXT         DEFAULT NULL COMMENT '新手易错/注意事项',
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_tea_brewing_guides_tea_id (tea_id),
  CONSTRAINT fk_tea_brewing_guides_tea FOREIGN KEY (tea_id) REFERENCES teas (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci
  COMMENT = '茶品分步冲泡教程，与茶品 1:1（ADR-0005）';

-- ------------------------------------------------------------
-- 4. collection_lists —— 用户收藏清单（PRD §4.2 / FR-5.1 / FR-5.2，S9 多清单）
-- 每用户仅一个默认清单：默认行 is_default=1，普通行 is_default=NULL
-- UNIQUE(user_id, is_default) 依赖 MySQL 唯一索引允许多个 NULL
-- 可见性不落列，由 share_tokens.is_active 派生
-- ------------------------------------------------------------
CREATE TABLE collection_lists (
  id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id     INT UNSIGNED NOT NULL,
  title       VARCHAR(50)  NOT NULL DEFAULT '我的收藏' COMMENT '清单标题，可编辑（FR-5.2）',
  is_default  TINYINT(1)   DEFAULT NULL COMMENT '1=默认清单；NULL=普通清单（S9）',
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_list_user_default (user_id, is_default),
  KEY idx_list_user (user_id),
  CONSTRAINT fk_list_user FOREIGN KEY (user_id) REFERENCES users (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci
  COMMENT = '用户收藏清单，每用户一个默认 + 最多 9 个普通（PRD §4.2 / S9）';

-- ------------------------------------------------------------
-- 5. favorite_items —— 收藏条目 + 品鉴笔记（PRD §4.2 / FR-5.1/5.2/5.3/5.6）
-- 清单归属以 list_id 为准；user_id 冗余用于跨清单去重与统计（S9）
-- 同一茶品可存在于多个清单，但 teas.favorite_count 只计 1 次
-- ------------------------------------------------------------
CREATE TABLE favorite_items (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  list_id       INT UNSIGNED NOT NULL COMMENT '所属清单（S9）',
  user_id       INT UNSIGNED NOT NULL,
  tea_id        INT UNSIGNED NOT NULL,
  tasting_note  TEXT         DEFAULT NULL COMMENT '品鉴笔记（私有，PRD FR-5.3）',
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '收藏时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_favorite_list_tea (list_id, tea_id),
  KEY idx_favorite_list_created (list_id, created_at),
  KEY idx_favorite_user_created (user_id, created_at),
  KEY idx_favorite_tea (tea_id),
  KEY idx_favorite_created_tea (created_at, tea_id),
  CONSTRAINT fk_favorite_list FOREIGN KEY (list_id) REFERENCES collection_lists (id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_favorite_user FOREIGN KEY (user_id) REFERENCES users (id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_favorite_tea FOREIGN KEY (tea_id) REFERENCES teas (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci
  COMMENT = '收藏条目：清单-茶关联 + 私有品鉴笔记（PRD §4.2）';

-- ------------------------------------------------------------
-- 6. share_tokens —— 分享令牌（PRD FR-5.4 / FR-5.5）
-- 撤销为软失效：is_active = 0 + revoked_at，行永久保留
-- token 使用 utf8mb4_bin：大小写敏感，防止 k7X9m2 / K7X9M2 被视为同一令牌
-- ------------------------------------------------------------
CREATE TABLE share_tokens (
  id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
  list_id     INT UNSIGNED NOT NULL,
  token       VARCHAR(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL
                                                COMMENT '短码，大小写敏感',
  is_active   TINYINT(1)   NOT NULL DEFAULT 1   COMMENT '1 有效 / 0 已撤销',
  revoked_at  DATETIME     DEFAULT NULL         COMMENT '撤销时间（撤销不可逆）',
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_share_token (token),
  KEY idx_share_list_active (list_id, is_active),
  CONSTRAINT fk_share_list FOREIGN KEY (list_id) REFERENCES collection_lists (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci
  COMMENT = '清单分享令牌，撤销后永久保留（FR-5.4 / FR-5.5）';

-- ------------------------------------------------------------
-- 7. operation_logs —— 管理员写操作留痕（模块 6，最小字段集）
-- user_id 采用 SET NULL：审计记录不随账号删除而消失
-- 不建 target_id 外键：删茶不应抹掉历史日志
-- ------------------------------------------------------------
CREATE TABLE operation_logs (
  id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id      INT UNSIGNED DEFAULT NULL COMMENT '操作人（账号删除后置空）',
  action       VARCHAR(32)  NOT NULL     COMMENT 'create_tea / update_tea / toggle_tea / upload_image',
  target_type  VARCHAR(32)  NOT NULL DEFAULT 'tea' COMMENT '目标类型，MVP 仅 tea',
  target_id    INT UNSIGNED DEFAULT NULL COMMENT '目标主键（弱引用，不建外键）',
  detail       VARCHAR(500) DEFAULT NULL COMMENT '操作摘要（可选，不存 JSON diff）',
  created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_oplog_created (created_at),
  KEY idx_oplog_user (user_id),
  CONSTRAINT fk_oplog_user FOREIGN KEY (user_id) REFERENCES users (id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci
  COMMENT = '管理员写操作审计日志（MVP 最小留痕）';

-- ------------------------------------------------------------
-- 8. login_attempts —— 登录失败记录（S14，批次二 / 迁移 0004）
-- 只记录失败事件，不记录密码明文；24 小时后由登录流程清理
-- 用户名与 IP 双维度窗口计数，任一达到阈值即锁定
-- ------------------------------------------------------------
CREATE TABLE login_attempts (
  id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  username   VARCHAR(32)  NOT NULL COMMENT '失败尝试的用户名（含不存在的用户名）',
  ip         VARCHAR(45)  NOT NULL COMMENT '客户端 IP（兼容 IPv6）',
  failed_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '失败时间',
  PRIMARY KEY (id),
  KEY idx_login_attempt_username (username, failed_at),
  KEY idx_login_attempt_ip (ip, failed_at)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci
  COMMENT = '登录失败尝试（S14 锁定依据）';

-- ------------------------------------------------------------
-- 9. tea_name_category_map —— 名品-茶类映射（S10 第一层校验 / 迁移 0006）
-- 命中名称时强校验用户提交的茶类；未命中由管理员人工审核
-- ------------------------------------------------------------
CREATE TABLE tea_name_category_map (
  id        INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name      VARCHAR(100) NOT NULL COMMENT '名品名称',
  category  ENUM('green','white','yellow','red','oolong','dark','reprocessed') NOT NULL COMMENT '应有茶类',
  PRIMARY KEY (id),
  UNIQUE KEY uk_name_category_name (name)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci
  COMMENT = '名品-茶类映射（S10 第一层校验）';

-- ------------------------------------------------------------
-- 10. contributions —— 用户贡献提交与审核状态（S10–S13 / 迁移 0006）
-- payload 为 JSON：new_tea 存茶品字段，article 存 {title, content}
-- 状态单向流转 pending → approved / rejected；记录不物理删除
-- ------------------------------------------------------------
CREATE TABLE contributions (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id        INT UNSIGNED NOT NULL,
  type           ENUM('new_tea','article') NOT NULL COMMENT '提交类型',
  target_tea_id  INT UNSIGNED DEFAULT NULL COMMENT '科普投稿目标茶品（new_tea 为 NULL）',
  payload        JSON         NOT NULL COMMENT '结构化提交内容',
  status         ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending',
  reject_reason  VARCHAR(200) DEFAULT NULL COMMENT '拒绝理由（仅 rejected）',
  reviewer_id    INT UNSIGNED DEFAULT NULL COMMENT '审核管理员',
  reviewed_at    DATETIME     DEFAULT NULL COMMENT '审核时间',
  created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_contrib_user_status (user_id, status),
  KEY idx_contrib_status_created (status, created_at),
  CONSTRAINT fk_contrib_user FOREIGN KEY (user_id) REFERENCES users (id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_contrib_reviewer FOREIGN KEY (reviewer_id) REFERENCES users (id)
    ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT fk_contrib_tea FOREIGN KEY (target_tea_id) REFERENCES teas (id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci
  COMMENT = '用户贡献提交与审核状态（S10–S13）';

-- ============================================================
-- 种子数据
-- ============================================================

-- 管理员初始账号（admin / admin123，bcrypt cost=10）
INSERT INTO users (id, username, password_hash, role, created_at) VALUES
  (1, 'admin', '$2b$10$h5mOeEvNxv9pWjkpSkGHheXyDQ9pHPtsjT.nsYjjnk.QKukuo9EH.', 'admin', UTC_TIMESTAMP());

-- 六款示例茶品：覆盖六大茶类各一款（数据取自原型 mock，主图使用外链 CDN）
INSERT INTO teas
  (id, name, category, origin, season, fermentation, price_range, representative_variety,
   shape_desc, soup_desc, aroma_desc, taste_desc,
   water_temp, tea_amount, brew_time, main_image_url, is_active, favorite_count)
VALUES
  (1, '西湖龙井', 'green', '浙江 杭州 西湖狮峰', '明前', '不发酵', NULL, '群体种',
   '扁平光滑，色翠略黄，形似雀舌',
   '嫩绿明亮，清澈见底',
   '豆香清雅，热香馥郁，冷香幽兰',
   '鲜爽甘醇，回甘明显，有淡淡的板栗香',
   85, 3, 90,
   'https://images.unsplash.com/photo-1563822249366-3efb23b8e0c9?w=600&h=400&fit=crop', 1, 2480),

  (2, '白毫银针', 'white', '福建 福鼎', '明前', '微发酵', NULL, '福鼎大白茶',
   '芽头肥壮，满披白毫，色白如银',
   '浅杏黄色，清澈透亮',
   '毫香显著，有清甜味',
   '清淡回甘，毫味足，有特殊的"香韵"',
   90, 3, 120,
   'https://images.unsplash.com/photo-1594631252845-29fc4cc8cde9?w=600&h=400&fit=crop', 1, 1280),

  (3, '君山银针', 'yellow', '湖南 岳阳 君山', '春茶', '微发酵', NULL, NULL,
   '芽头肥壮，紧实挺直，芽尖金黄',
   '杏黄明亮，冲泡后芽尖竖立',
   '清香高长',
   '鲜爽甘醇',
   90, 3, 120,
   'https://images.unsplash.com/photo-1627435360136-ec5c3c36e4a0?w=600&h=400&fit=crop', 1, 890),

  (4, '正山小种', 'red', '福建 武夷山 桐木关', '春茶', '全发酵', NULL, NULL,
   '条索紧结，乌黑油润',
   '红艳明亮',
   '松烟香 + 桂圆香（传统工艺）',
   '醇厚甘爽，有独特的松烟味',
   100, 5, 180,
   'https://images.unsplash.com/photo-1558160074-4d7d8bdf4256?w=600&h=400&fit=crop', 1, 1980),

  (5, '大红袍', 'oolong', '福建 武夷山 九龙窠', '春茶', '半发酵', NULL, NULL,
   '条索紧结，色泽绿褐鲜润',
   '橙黄明亮',
   '馥郁兰花香 + 岩骨花香',
   '醇厚回甘，有明显的"岩韵"，七泡有余香',
   100, 7, 30,
   'https://images.unsplash.com/photo-1597481499750-3e6b22637e12?w=600&h=400&fit=crop', 1, 3120),

  (6, '普洱熟茶', 'dark', '云南 昆明', NULL, '后发酵', NULL, NULL,
   '条索紧结，色泽红褐',
   '红浓明亮，有"金圈"',
   '陈香、枣香、木香',
   '醇厚顺滑，几乎无苦涩，回甘明显',
   100, 8, 30,
   'https://images.unsplash.com/photo-1571346451091-e8c524a1b998?w=600&h=400&fit=crop', 1, 2180);

-- 官方小贴士：未写的区块留 NULL（前端按 FR-6.4 隐藏）
INSERT INTO tea_tips (tea_id, history, suitable, misconception, official_note) VALUES
  (1,
   '西湖龙井始于唐代，是中国十大名茶之首，狮峰产区为核心原产地。',
   '适合脾胃强健、喜鲜爽口感的茶友；春季饮用尤佳。',
   '水温不宜过高，85℃即可，沸水会烫熟嫩芽导致苦涩。',
   '采摘标准为一芽一叶或一芽二叶初展，炒制工艺独特，有"抖、挺、扣、抓、压、磨"十大手法。'),

  (2,
   '白毫银针是白茶中的极品，全部由芽头制成，每公斤约需 2.5 万个芽头。',
   '适合胃寒人群，白茶性温，有养胃之效。',
   NULL,
   '白茶是"一年茶，三年药，七年宝"，陈化后价值倍增。'),

  (3,
   '君山银针与白毫银针齐名，但属于黄茶类，核心区别是黄茶经过焖黄工艺。',
   NULL, NULL, NULL),

  (4,
   '正山小种是世界红茶的鼻祖，由福建武夷山桐木关茶农发明，17 世纪传入欧洲。',
   '适合冬日暖饮，也适合调饮奶茶。',
   '正山小种的松烟香是传统工艺特征，不是"烟味"或品质问题。',
   NULL),

  (5,
   '大红袍是武夷山岩茶之王，母树仅存 6 株，已有 350 多年历史。',
   '适合有一定品茶经验的茶友，岩韵需要细细品味。',
   NULL,
   '岩茶讲究"岩韵"——岩骨花香，醇厚回甘，是乌龙茶中最有"风骨"的品类。'),

  (6,
   NULL,
   '熟茶性温，适合大多数人群，尤其是胃寒或晚上想喝茶的茶友。',
   '熟茶发酵工艺 1973 年才发明，历史远短于生茶，但因其温和的口感迅速流行。',
   NULL);

-- 名品-茶类映射（S10 第一层校验）：用户提交新茶时命中名称须与茶类一致
INSERT INTO tea_name_category_map (name, category) VALUES
  ('西湖龙井', 'green'), ('碧螺春', 'green'), ('黄山毛峰', 'green'),
  ('六安瓜片', 'green'), ('信阳毛尖', 'green'),
  ('白毫银针', 'white'), ('白牡丹', 'white'), ('寿眉', 'white'),
  ('君山银针', 'yellow'), ('蒙顶黄芽', 'yellow'),
  ('正山小种', 'red'), ('金骏眉', 'red'), ('祁门红茶', 'red'), ('滇红', 'red'),
  ('大红袍', 'oolong'), ('铁观音', 'oolong'), ('武夷岩茶', 'oolong'), ('凤凰单丛', 'oolong'),
  ('普洱熟茶', 'dark'), ('普洱生茶', 'dark'), ('安化黑茶', 'dark'), ('六堡茶', 'dark'),
  ('茉莉花茶', 'reprocessed'), ('茉莉毛尖', 'reprocessed'), ('茉莉银针', 'reprocessed'),
  ('桂花乌龙', 'reprocessed'), ('白桃乌龙', 'reprocessed'), ('玫瑰花茶', 'reprocessed'),
  ('杭白菊', 'reprocessed'), ('陈皮普洱', 'reprocessed');

-- ------------------------------------------------------------
-- 11. content_types —— 内容板块分类（批次五 R1–R5 / 迁移 0007）
-- ------------------------------------------------------------
CREATE TABLE content_types (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  code          VARCHAR(32)  NOT NULL,
  name          VARCHAR(50)  NOT NULL,
  icon          VARCHAR(32)  NULL,
  description   VARCHAR(200) NULL,
  sort_order    INT          NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uk_content_types_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='内容板块分类（批次五 R1–R5）';

-- 12. content_items —— 统一内容条目（批次五 R1–R5 / 迁移 0007）
--     meta JSON 承载各板块特有字段：
--       teaware:   material / volume / category
--       origin:    province / region
--       culture:   era / tags
--       brand:     founded / brand_origin / website
--       knowledge: subtype / difficulty
-- ------------------------------------------------------------
CREATE TABLE content_items (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  type_id       INT UNSIGNED NOT NULL,
  title         VARCHAR(200) NOT NULL,
  summary       VARCHAR(500) NULL,
  body          TEXT         NULL,
  cover_image   VARCHAR(500) NULL,
  meta          JSON         NULL,
  sort_order    INT          NOT NULL DEFAULT 0,
  is_active     TINYINT(1)   NOT NULL DEFAULT 1,
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_content_items_type FOREIGN KEY (type_id) REFERENCES content_types(id) ON DELETE CASCADE,
  KEY idx_content_items_type_active_sort (type_id, is_active, sort_order),
  KEY idx_content_items_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='统一内容条目（批次五 R1–R5；meta 为各板块特有 JSON 字段）';

-- ------------------------------------------------------------
-- 批次五种子数据
-- ------------------------------------------------------------

-- 5 个板块分类
INSERT INTO content_types (code, name, icon, description, sort_order) VALUES
  ('teaware',  '茶具茶器', '🫖', '盖碗、茶壶、品茗杯、公道杯等茶器文化与选择指南', 1),
  ('origin',   '茶叶产地', '🗺️', '中国主要产茶区地理环境、风土特色与名茶产地溯源', 2),
  ('culture',  '茶叶文化', '📜', '茶的历史演变、文人茶事、茶道精神与传统礼仪', 3),
  ('brand',    '茶叶品牌', '🏷️', '中华老字号茶企与现代茶品牌故事', 4),
  ('knowledge','茶叶知识', '📚', '茶叶标准、分类原理、冲泡技巧与品鉴知识', 5);

-- 各板块示例条目（每个板块 2-3 条）
INSERT INTO content_items (type_id, title, summary, body, cover_image, meta, sort_order, is_active) VALUES
  -- 茶具
  ((SELECT id FROM content_types WHERE code='teaware'), '盖碗：茶席上最常见的泡茶器具', '上盖、中碗、下托三件一套，又称三才碗，明代以后流行。', '盖碗，也称三才碗、三才杯，是一种古老的泡茶器具。碗盖、碗身、碗托三件一套，分别寓意天、人、地三才。

盖碗的优势在于不吸味、散热快、可直视汤色，适合冲泡绿茶、花茶与功夫茶。器型多为敞口浅腹，容量从 100ml 到 200ml 不等。

选盖碗时注意胎质细腻、碗口外撇防烫手、碗盖与碗身密封性适中。', NULL, '{"material":"白瓷","volume":"150ml","category":"盖碗"}', 1, 1),
  ((SELECT id FROM content_types WHERE code='teaware'), '紫砂壶：茶器之王的秘密', '宜兴紫砂陶土制成，气孔结构使茶香久蕴不散，茶汤越用越润。', '紫砂壶源于宋代，盛于明清，以江苏宜兴为核心产地。紫砂陶土含铁、硅、铝等矿物，经 1200℃ 高温烧制后形成独特的双气孔结构。

这种结构使紫砂壶透气性好、保温性适中、不吸茶香却能缓慢释放茶中物质，长期使用内壁形成的茶山使茶汤更加醇厚。

新壶开壶需清水煮沸 30 分钟，倒去水后用茶叶反复擦拭内壁。', NULL, '{"material":"紫砂","volume":"200ml","category":"茶壶"}', 2, 1),
  -- 产地
  ((SELECT id FROM content_types WHERE code='origin'), '西湖：龙井茶的故乡', '浙江杭州西湖周边群山，茶园沿湖分布，山色湖光与茶香相映成趣。', '西湖产茶历史可追溯至唐代，陆羽《茶经》有载。宋代以后西湖龙井渐成名品，明清两度列为贡茶。

西湖核心产茶区位于狮峰、龙井村、五云山、虎跑一带。年均气温 16℃ 左右，年降水量 1500mm，土壤微酸性红壤，昼夜温差适中，造就了龙井色翠、香郁、味甘、形美四绝。

明前龙井特指清明节前采摘的头春茶，通常一芽一叶或一芽两叶，干茶扁平匀整。', NULL, '{"province":"浙江","region":"杭州西湖"}', 1, 1),
  ((SELECT id FROM content_types WHERE code='origin'), '武夷山：乌龙茶与红茶的发源地', '福建武夷山脉，丹霞地貌造就岩骨花香，大红袍名品即出此地。', '武夷山位于福建省北部，海拔 400–1000m，属典型丹霞地貌——红色砂砾岩经亿万年风化形成奇峰峭壁。

茶园多分布在岩峰之间的坑、涧、窠中，土层薄而矿物质丰富，茶树因此吸收独特的岩韵。

武夷山是世界文化与自然双重遗产，也是乌龙茶（大红袍、肉桂、水仙）与正山小种红茶的发源地。', NULL, '{"province":"福建","region":"南平武夷山"}', 2, 1),
  -- 文化
  ((SELECT id FROM content_types WHERE code='culture'), '陆羽与《茶经》：茶学的开山之作', '唐代陆羽著《茶经》三卷十章，是世界上第一部系统性茶文化专著。', '陆羽（733–804），字鸿渐，号茶山御史，唐代竟陵（今湖北天门）人。他自幼被弃于茶园，后被僧人收养，一生嗜茶。

《茶经》成书于公元 780 年前后，系统论述了茶的起源、种类、采制、器具、煮茶、饮用、产地、传说等，共三卷十章。陆羽因此被尊为茶圣。

《茶经》不仅是技术手册，更奠定了中华茶文化的精神内核——茶需俭、茶具需雅、饮茶需敬。', NULL, '{"era":"唐代","tags":["陆羽","茶经","茶圣"]}', 1, 1),
  ((SELECT id FROM content_types WHERE code='culture'), '宋代点茶与斗茶之风', '宋代茶事鼎盛，点茶法取代煮茶成为主流，文人斗茶蔚然成风。', '宋代（960–1279）是中华茶文化的黄金时代。茶从煎茶（煮）变为点茶：先将茶饼研磨成细粉，注水后用茶筅击打至泛起细密泡沫（称为汤花）。

斗茶又称茗战，以汤花持久度和汤色白者为胜。宋徽宗赵佶著《大观茶论》，系统阐述点茶技艺，自称斗茶十中八九。

建盏（兔毫盏、油滴盏）因适配点茶汤花观察而风靡，成为宋代最具代表性的茶器。', NULL, '{"era":"宋代","tags":["点茶","斗茶","宋徽宗","建盏"]}', 2, 1),
  -- 品牌
  ((SELECT id FROM content_types WHERE code='brand'), '吴裕泰：百年老字号的茉莉花茶', '1887 年创立于北京，以茉莉花茶闻名，百年传统工艺双瓣茉莉花窨制。', '吴裕泰茶庄由徽州歙县人吴锡卿于清光绪十三年（1887）在北京崇文门外开办，至今已超 130 年。

品牌坚持制之得其法、藏之得其宜的古训，茉莉花茶采用春季采制的春茶坯，与伏天采摘的茉莉花反复窨制，每窨一次需花一天一夜。

2011 年，吴裕泰茉莉花茶制作技艺被列入国家级非物质文化遗产名录。', NULL, '{"founded":1887,"brand_origin":"北京","website":"https://www.wuyutai.com"}', 1, 1),
  -- 知识
  ((SELECT id FROM content_types WHERE code='knowledge'), '六大茶类分类原理：发酵度是核心', '绿茶、白茶、黄茶、乌龙茶、红茶、黑茶，以发酵程度为唯一分类标准。', '中华六大茶类由安徽农业大学陈椽教授于 1979 年正式提出，分类依据为发酵程度（茶叶内含物质氧化程度）：

• 绿茶（不发酵 0%）：杀青抑制酶活性，干绿汤绿，如龙井、碧螺春
• 白茶（微发酵 5–10%）：自然萎凋，不炒不揉，如白毫银针、白牡丹
• 黄茶（轻发酵 10–20%）：闷黄工艺，黄汤黄叶，如蒙顶黄芽
• 乌龙茶（半发酵 30–60%）：摇青做青，绿叶红镶边，如铁观音、大红袍
• 红茶（全发酵 80–95%）：酶促氧化彻底，红叶红汤，如祁门红茶、正山小种
• 黑茶（后发酵 100%）：微生物参与的后发酵，需陈化，如安化黑茶、六堡茶', NULL, '{"subtype":"standard","difficulty":"beginner"}', 1, 1),
  ((SELECT id FROM content_types WHERE code='knowledge'), '水温与投茶量：泡茶两要素', '不同茶类适用不同水温与投茶比例，掌握这两点日常泡茶基本不会出错。', '水温：
• 绿茶、黄茶：80–85℃（避免高温破坏鲜爽味与维生素）
• 白茶：85–95℃（视茶叶老嫩调整）
• 乌龙茶：95–100℃（沸水充分激发岩韵与香气）
• 红茶：85–95℃
• 黑茶：100℃ 沸水（后发酵茶需高温唤醒活性）

投茶量：
• 盖碗：茶量约为盖碗容量的 1/5（茶水比 1:50）
• 紫砂壶：茶量约为壶容量的 1/3（随壶型调整）
• 玻璃杯（绿茶）：茶量约为杯容量的 1/6', NULL, '{"subtype":"brewing","difficulty":"beginner"}', 2, 1),

-- 0009 批次：各板块内容扩充（每板块补至 6-8 条）
-- 茶具
  ((SELECT id FROM content_types WHERE code='teaware'), '公道杯：均匀茶汤的分配者', '又称茶海、匀杯，承接壶中茶汤再分斟各杯，保证每杯浓淡一致。', '公道杯的作用是「匀汤」：壶中茶汤先注入公道杯，使上下层茶汤混合均匀，再分斟品茗杯，确保每位客人杯中滋味一致。

材质以玻璃、白瓷为主，便于观察汤色与茶渣沉淀。使用要点有二：出汤要尽，壶中不留余汤以免下一泡过浓；分茶七分满，留下三分是人情。', NULL, '{"material":"耐热玻璃","volume":"200ml","category":"公道杯"}', 3, 1),
  ((SELECT id FROM content_types WHERE code='teaware'), '品茗杯：茶汤的最后一站', '直接入口的小杯，白瓷最通用——不夺茶香、可观汤色。', '品茗杯是喝茶人手中最后一件器具。白瓷小杯之所以成为主流，因其釉面致密不吸味，白色内壁又能真实呈现汤色深浅。

杯型影响体验：敞口杯散热快，适合绿茶即泡即饮；敛口杯聚香保温，适合乌龙细品慢啜。工夫茶席上的「温杯洁具」既是卫生需要，也是待客之礼。', NULL, '{"material":"白瓷","volume":"50ml","category":"品茗杯"}', 4, 1),
  ((SELECT id FROM content_types WHERE code='teaware'), '建盏：宋代点茶第一盏', '福建建阳铁胎黑釉，兔毫、油滴、曜变为名贵釉色，黑釉衬白汤最宜观沫。', '建盏产于福建建阳水吉镇，胎体含铁量高（故称铁胎），经 1300℃ 以上烧制，釉色自然窑变。名贵品类有兔毫（丝缕如兔毛）、油滴（斑点如油花）、曜变（光晕变幻，存世仅三件，均藏日本）。

宋代点茶尚白，黑釉盏正衬白色汤花，蔡襄《茶录》称其「茶色白，宜黑盏」。今日建盏多用于品饮普洱、岩茶，厚胎保温，越养越润。', NULL, '{"material":"铁胎黑釉瓷","volume":"120ml","category":"品茗杯"}', 5, 1),
  ((SELECT id FROM content_types WHERE code='teaware'), '茶则与茶匙：量茶有则', '茶则量茶、茶匙拨茶，茶道六君子之一，体现节制之美。', '茶则用于从茶罐中量取茶叶，茶匙则将则中茶叶拨入壶内。二者配合，手不触茶，既保持茶叶干燥洁净，也增添行茶的仪式感。

材质以竹制最雅、铜制沉稳、瓷制温润。作为「茶道六君子」（则、匙、夹、针、漏、筒）之首，茶则提醒泡茶人：投茶有度，过犹不及。', NULL, '{"material":"竹","volume":"","category":"茶道配件"}', 6, 1),
  ((SELECT id FROM content_types WHERE code='teaware'), '玻璃茶壶：看茶叶跳舞', '高硼硅耐热玻璃，透明壶身可观茶叶舒展，最宜绿茶与花草茶。', '玻璃茶壶采用高硼硅耐热玻璃，可承受瞬间温差，部分款式可明火或电陶炉直烧。

它最大的优势是「看得见」：绿茶芽叶在水中直立沉浮、徐徐舒展，是泡茶过程的一部分。短板也明显——不保温、不聚香，因此宜即泡即饮，不适合需要高温逼香的乌龙与黑茶。', NULL, '{"material":"高硼硅玻璃","volume":"600ml","category":"茶壶"}', 7, 1),
  ((SELECT id FROM content_types WHERE code='teaware'), '朱泥小壶：工夫茶的灵魂', '宜兴朱泥细腻如膏，聚香性极佳，小壶小杯逼出乌龙高香。', '朱泥是宜兴紫砂中的特殊矿料，矿层薄、含铁高，泥质细腻如膏。烧成后密度高于紫泥，敲击声清脆，聚香效果极佳，最能激发铁观音、凤凰单丛等高香乌龙的兰花香韵。

朱泥收缩率约两成，成品率低，故朱泥壶多做小品（100–150ml）。工夫茶讲究「小壶小杯」，一壶三杯，循环快冲，茶汤始终滚烫浓香。', NULL, '{"material":"朱泥","volume":"120ml","category":"茶壶"}', 8, 1),
-- 产地
  ((SELECT id FROM content_types WHERE code='origin'), '西双版纳：普洱茶的核心腹地', '云南勐海、勐腊两大茶区，古六大茶山所在地，大叶种古树资源冠绝全国。', '西双版纳位于北回归线以南，热带季风气候终年温暖湿润。境内勐海（布朗山、巴达山）与勐腊（易武）两大茶区，分布着举世罕见的百年以上古茶树群落。

清代「古六大茶山」——易武、倚邦、蛮砖、莽枝、革登、攸乐——均在其境，是普洱茶「越陈越香」传奇的起点。大叶种晒青毛茶内含物质丰厚，为后期陈化提供了充足底物。', NULL, '{"province":"云南","region":"西双版纳"}', 3, 1),
  ((SELECT id FROM content_types WHERE code='origin'), '安溪：铁观音的故乡', '福建泉州乌龙第一县，海拔 700–1000 米云雾带，孕育「观音韵」兰花香。', '安溪县地处戴云山脉东南坡，峰峦叠翠、云雾缭绕。铁观音茶树于清雍正年间在此发现（一说乾隆），因「美如观音重如铁」得名。

铁观音属半发酵乌龙，以「观音韵」与天然兰花香著称，制作工艺含晒青、摇青、炒青、包揉、烘焙十余道工序。全县茶园逾 60 万亩，是中国乌龙茶产量第一县，也是闽南乌龙的核心地标。', NULL, '{"province":"福建","region":"泉州安溪"}', 4, 1),
  ((SELECT id FROM content_types WHERE code='origin'), '祁门：世界高香红茶之源', '安徽黄山西麓槠叶种茶区，「祁门香」似花似果似蜜，1915 年巴拿马金奖。', '祁门县位于黄山西麓，山高林密、雨量充沛。当地槠叶种茶树内含物丰富，1875 年创制工夫红茶后迅速扬名海外。

「祁门香」是祁红的灵魂——一种难以定义的复合香气，被形容为似花、似果、似蜜。祁门红茶与印度大吉岭、锡兰乌瓦并称世界三大高香红茶，1915 年获巴拿马万国博览会金奖，至今仍是英式下午茶的高端之选。', NULL, '{"province":"安徽","region":"黄山祁门"}', 5, 1),
  ((SELECT id FROM content_types WHERE code='origin'), '福鼎：中国白茶之乡', '福建宁德太姥山麓，大白茶、大毫茶芽头肥壮多毫，白毫银针原产地。', '福鼎地处闽东沿海，太姥山矗立于东海之滨。相传尧时太姥娘娘曾以「绿雪芽」救治麻疹患儿，被视为白茶始祖传说。

福鼎大白茶、福鼎大毫茶两个国家级良种芽头肥壮、满披白毫，是制作白毫银针、白牡丹的上好原料。当地民谚「世界白茶在中国，中国白茶在福鼎」，白茶「一年茶、三年药、七年宝」的陈化理念也由此发端。', NULL, '{"province":"福建","region":"宁德福鼎"}', 6, 1),
  ((SELECT id FROM content_types WHERE code='origin'), '蒙顶山：人工种茶发源地', '四川雅安雨雾蒙沫，西汉吴理真手植七株茶树，开世界人工种茶先河。', '蒙顶山位于四川雅安，年均降雨量超过 2000 毫米，「西蜀漏天」自古多雾。西汉甘露年间（公元前 53 年），吴理真在蒙顶五峰间手植七株茶树，被后世尊为「植茶始祖」，蒙顶山也因此成为世界有记载最早的人工种茶地。

蒙顶甘露（卷曲形绿茶）自唐至清入贡千余年；蒙顶黄芽则是黄茶「闷黄」工艺的代表。「扬子江心水，蒙山顶上茶」的对联，道尽了它在茶史上的地位。', NULL, '{"province":"四川","region":"雅安蒙顶山"}', 7, 1),
  ((SELECT id FROM content_types WHERE code='origin'), '凤凰山：单丛香型的博物馆', '广东潮州乌岽山，一株一香的凤凰单丛原产地，宋种古茶树已逾七百年。', '凤凰山位于广东潮州，主峰乌岽山海拔 1498 米，常年云雾弥漫。凤凰单丛属乌龙茶，因「单株采摘、单株制作」得名——每株茶树香气各异，遂有蜜兰香、黄栀香、芝兰香、杏仁香、姜花香等十大香型之说。

山中有南宋末年遗留的「宋种」古茶树，树龄逾七百年。凤凰单丛以「山韵」「蜜韵」著称，是潮汕工夫茶席上当之无愧的主角。', NULL, '{"province":"广东","region":"潮州凤凰山"}', 8, 1),
-- 文化
  ((SELECT id FROM content_types WHERE code='culture'), '唐代煎茶：一碗茶的仪式感', '饼茶炙烤碾末，一沸调盐、二沸投茶、三沸育华，陆羽二十四器成就盛唐茶事。', '唐代主流饮茶方式为煎茶：饼茶先炙烤提香，再碾成细末、罗筛分级。煮水三沸——一沸如鱼目时调盐，二沸涌泉连珠时投茶末，三沸腾波鼓浪时点茶入碗，谓之「育华」。

陆羽《茶经》详载二十四件煎茶器具，从风炉到水方皆有规制。煎茶使饮茶超越解渴，成为文人雅集的主角，时人所谓「自从陆羽生人间，人间相学事春茶」。', NULL, '{"era":"唐代","tags":["煎茶","陆羽","茶经"]}', 3, 1),
  ((SELECT id FROM content_types WHERE code='culture'), '明代瀹饮革命：从点茶到冲泡', '1391 年朱元璋废团改散，散茶壶泡取代团饼点茶，饮茶方式由此定型至今。', '明洪武二十四年（1391 年），太祖朱元璋下诏「罢造龙团，惟采芽茶以进」，废止唐宋以来进贡的龙凤团饼。这道诏令意外推动了中国饮茶史上最大的变革——散茶瀹（yuè）饮法兴起。

茶叶直接投壶冲泡，省去炙、碾、罗、点的繁琐。壶泡风行催生了紫砂艺术的黄金时代，茶事美学从繁复转向清简，「开千古茗饮之宗」。', NULL, '{"era":"明代","tags":["瀹饮","朱元璋","散茶"]}', 4, 1),
  ((SELECT id FROM content_types WHERE code='culture'), '潮汕工夫茶：活着的茶道', '孟臣壶、若琛杯、橄榄炭、玉书煨——关公巡城、韩信点兵，程式即美学。', '潮汕工夫茶是中国现存最完整的传统茶艺，2008 年列入国家级非物质文化遗产。器具讲究「四宝」：孟臣壶（小朱泥壶）、若琛杯、砂铫（玉书煨）、橄榄炭。

冲泡程式繁复而优雅：纳茶、高冲、刮沫、淋罐，分茶时「关公巡城」（循环斟茶使每杯均匀）、「韩信点兵」（余沥滴尽）。三杯成品字，一杯为饮、三口为品，工夫二字，尽在毫厘之间。', NULL, '{"era":"清代至今","tags":["工夫茶","潮汕","非遗"]}', 5, 1),
  ((SELECT id FROM content_types WHERE code='culture'), '茶马古道：马蹄踏出的贸易史诗', '唐宋至民国，滇茶、川茶经马帮入藏易马，世界上海拔最高的商贸通道。', '茶马古道源于唐宋「茶马互市」：中原以茶叶换取边疆马匹。川藏道、滇藏道、青藏道三大主线横贯横断山脉，翻越海拔四五千米的雪山垭口。

云南普洱茶、四川边茶（康砖、金尖）经马帮驮运，数十日乃至数月抵达拉萨，再转尼泊尔、印度。马蹄声虽已远去，古道上的集市、锅庄与茶号遗址，仍诉说着这条「天路」的千年回响。', NULL, '{"era":"唐宋至民国","tags":["茶马古道","马帮","边茶"]}', 6, 1),
  ((SELECT id FROM content_types WHERE code='culture'), '禅茶一味：赵州一句「吃茶去」', '从谂禅师以茶接引学人，茶成为禅修的一部分——于饮茶中体会当下。', '唐代赵州从谂禅师，凡有僧来，无论新旧，皆言「吃茶去」。院主不解，禅师亦唤「吃茶去」。三句吃茶去，打破分别心，成为禅宗最著名的公案之一。

宋代圆悟克勤禅师手书「茶禅一味」，后传入日本，深刻影响日本茶道。寺院种茶、普茶仪式、茶宴清规，茶与禅相互成就：以茶提神摄心助禅定，以禅心饮茶见自性。', NULL, '{"era":"唐宋","tags":["禅茶","赵州","公案"]}', 7, 1),
  ((SELECT id FROM content_types WHERE code='culture'), '茶与诗词：中国人的精神知己', '卢仝七碗清风生，苏轼佳茗似佳人——上千首茶诗构筑的东方生活美学。', '中国是诗的国度，也是茶的国度，二者相遇已有千年。唐代卢仝《走笔谢孟谏议寄新茶》写下「七碗吃不得也，唯觉两腋习习清风生」，后世称「七碗茶歌」，成为茶诗巅峰。

苏轼以「从来佳茗似佳人」喻茶之清雅；白居易「无由持一碗，寄与爱茶人」道出茶谊；李清照与赵明诚「赌书消得泼茶香」，以茶佐读。茶诗逾千首，茶早已超越饮品，成为中国人安顿心灵的意象。', NULL, '{"era":"唐宋","tags":["茶诗","卢仝","苏轼"]}', 8, 1),
-- 品牌
  ((SELECT id FROM content_types WHERE code='brand'), '张一元：京城茉莉花茶老字号', '1900 年创办，「一元复始，万象更新」，以汤清味浓的茉莉花茶立店百年。', '张一元茶庄由安徽歙县人张文卿于清光绪二十六年（1900 年）在北京花市创办，店名取「一元复始，万象更新」之意。1910 年迁址大栅栏，逐渐成为京城茉莉花茶的代名词。

张一元茉莉花茶以「汤清、味浓、入口芳香、回味无穷」著称，其窨制技艺列入国家级非物质文化遗产。至今大栅栏总店仍是北京茶文化的地标。', NULL, '{"founded":1900,"brand_origin":"北京","website":""}', 2, 1),
  ((SELECT id FROM content_types WHERE code='brand'), '大益：普洱茶行业的标杆', '源于 1940 年勐海茶厂，7542 生茶与 7572 熟茶是普洱评判的行业基准。', '大益源于 1940 年建成的佛海实验茶厂（今勐海茶厂），是云南历史最悠久的现代化茶厂之一。1975 年创制的 7542（生茶）与 7572（熟茶）配方，至今被视为评判普洱茶品质的标杆。

2004 年改制为大益集团，「大益茶制作技艺」入选国家级非物质文化遗产。其生肖纪念茶、轩辕号等产品在收藏市场颇具影响力，「益友会」体系也开创了茶企会员运营的先河。', NULL, '{"founded":1940,"brand_origin":"云南勐海","website":"https://www.taetea.com"}', 3, 1),
  ((SELECT id FROM content_types WHERE code='brand'), '八马茶业：百年世家的铁观音', '源自 1736 年铁观音发现者王氏家族，赛珍珠系列闻名，门店逾三千家。', '八马茶业源于福建安溪王氏制茶世家——清乾隆元年（1736 年），先祖王士让在安溪发现铁观音茶树。1997 年品牌正式创立，承续百年家传技艺。

其「赛珍珠」浓香型铁观音是拳头产品，以传统炭焙工艺造就独特炒米香。如今八马已发展为门店超三千家的全茶类连锁品牌，并多次服务国事茶叙，推动中国茶走向世界。', NULL, '{"founded":1997,"brand_origin":"福建安溪","website":"https://www.bama.cn"}', 4, 1),
  ((SELECT id FROM content_types WHERE code='brand'), '正山堂：金骏眉的创始者', '2005 年于武夷山桐木关创制金骏眉，正山小种四百余年传承的当代延续。', '正山堂坐落于武夷山国家级自然保护区桐木关，这里是世界红茶鼻祖正山小种的发源地，江氏家族制茶已历四百余年。

2005 年，江元勋团队在传统正山小种工艺基础上，以纯芽头创制金骏眉——汤色金黄、蜜香馥郁，一举打开高端红茶市场，引发全国「金骏眉热」。「正山堂」之名，寓意正山小种传承之堂。', NULL, '{"founded":2005,"brand_origin":"福建武夷山","website":""}', 5, 1),
  ((SELECT id FROM content_types WHERE code='brand'), '品品香：福鼎白茶领军者', '1992 年林振传创立于福鼎，「晒白金」老白茶系列树立品类标杆。', '品品香由林振传于 1992 年在福建福鼎创立，是集种植、加工、科研、出口于一体的白茶龙头企业，拥有数千亩有机茶园基地。

其「晒白金」系列以「一粒一泡」的小砖形态和年份标识，让老白茶消费透明化、标准化，成为市场标杆。企业还建有中国白茶体验馆，持续推动白茶品类教育与「一年茶、三年药、七年宝」的理念普及。', NULL, '{"founded":1992,"brand_origin":"福建福鼎","website":""}', 6, 1),
  ((SELECT id FROM content_types WHERE code='brand'), '凤牌：滇红工夫的创始品牌', '1939 年冯绍裘于凤庆创制滇红，经典 58 纪念伦敦拍卖夺魁之岁。', '1938 年，茶叶专家冯绍裘辗转抵达云南凤庆（时称顺宁），以当地大叶种鲜叶成功试制工夫红茶——滇红由此诞生，1939 年顺宁实验茶厂建成投产。

凤牌「经典 58」红茶为纪念 1958 年滇红在伦敦拍卖市场拍出最高价而命名，干茶金毫显露、汤色红艳、蜜香浓郁，是无数茶客的滇红入门第一课。', NULL, '{"founded":1939,"brand_origin":"云南凤庆","website":""}', 7, 1),
-- 知识
  ((SELECT id FROM content_types WHERE code='knowledge'), '品鉴三步法：观色、闻香、品味', '先看汤色清浊，再闻香型高低，后啜茶汤滋味——系统品鉴一杯茶。', '观色：好茶汤色透亮不浑浊。绿茶黄绿明亮，红茶红艳带金圈，乌龙金黄通透。叶底（泡开的茶叶）要柔软有活性，忌暗沉僵硬。

闻香：干茶香、盖香、水香、杯底香层层递进。香要「入水」——闻得到也喝得到；冷杯留香持久者更佳。

品味：小口啜吸，让茶汤在口腔翻滚。关注四感——鲜（氨基酸）、苦（咖啡碱）、涩（茶多酚）、甜（可溶性糖与回甘）。好茶苦涩能化、回甘生津、喉韵绵长。', NULL, '{"subtype":"standard","difficulty":"intermediate"}', 3, 1),
  ((SELECT id FROM content_types WHERE code='knowledge'), '家庭存茶四原则', '密封、避光、防潮、防异味——多数茶坏在存放，而非品质。', '密封：茶叶吸附性极强，开封后务必封口。绿茶、清香乌龙建议铝箔袋加密封罐；普洱、黑茶需适度透气，可用棉纸包裹入紫砂罐。

避光防潮：光线与水分是茶叶氧化变质的两大推手，存于阴凉干燥处，远离灶台与窗台。

防异味：茶叶是最强的「除味剂」，也因此极易串味。切勿与香料、调味品同柜，更不要放冰箱（绿茶例外，需密封冷藏）。

分类存放：绿茶当年喝鲜；白茶、普洱、黑茶在清洁环境下可长期陈放，定期检查有无受潮霉变。', NULL, '{"subtype":"standard","difficulty":"beginner"}', 4, 1),
  ((SELECT id FROM content_types WHERE code='knowledge'), '醒茶与洗茶：第一泡喝不喝？', '绿茶白茶不洗，乌龙黑茶必醒——第一泡去留背后的逻辑。', '洗茶（醒茶）有两个目的：温润茶叶使其舒展（醒），以及冲去表面浮尘（洗）。

建议不洗的茶：绿茶、黄茶、白毫银针等细嫩茶——第一泡正是氨基酸最丰富的精华，倒掉可惜。现代正规茶园出品，卫生大可放心。

建议醒的茶：紧压的普洱、黑茶，以及焙火较重的岩茶、老茶——沸水快速过一遍（5–10 秒出汤），既唤醒沉睡的香气，也让后续茶汤更纯净。老茶客称之为「温润泡」。', NULL, '{"subtype":"brewing","difficulty":"beginner"}', 5, 1),
  ((SELECT id FROM content_types WHERE code='knowledge'), '春茶、夏茶、秋茶的差异', '春茶鲜、夏茶苦、秋茶香——季节如何塑造一杯茶的个性。', '春茶（3–5 月）：历经一冬休养，芽叶肥壮、氨基酸含量高，滋味鲜爽醇厚。「明前茶贵如金」指的就是清明前的头采春茶。

夏茶（6–7 月）：气温高、生长快，茶多酚与咖啡碱累积，滋味偏苦涩。多制红茶（利于转化）或大宗茶。

秋茶（8–10 月）：昼夜温差大，芳香物质累积，香气高扬但汤感稍薄。铁观音讲究「春水秋香」，正是此意。

选购提示：名优绿茶认准春茶；高香乌龙可选秋茶；口粮红茶夏茶性价比往往不错。', NULL, '{"subtype":"standard","difficulty":"beginner"}', 6, 1),
  ((SELECT id FROM content_types WHERE code='knowledge'), '泡茶用水：山水上，江水中，井水下', '陆羽的择水标准放到今天：低矿化度软水泡什么茶都不会错。', '《茶经》有云：「其水，用山水上，江水中，井水下。」古人择水，本质是追求低矿化度、无异味、含氧充足的「活水」。

现代科学视角：水的总溶解固体（TDS）越低，越能还原茶的本味。硬水中的钙镁离子会与茶多酚络合，使汤色发暗、滋味变闷。

实操建议：家用首选纯净水或低矿化度天然水（TDS < 100mg/L）；自来水氯气重，静置或煮沸开盖散气后再用；山泉水虽好，未经检测慎用。好水不必贵，稳定即可。', NULL, '{"subtype":"brewing","difficulty":"intermediate"}', 7, 1),
  ((SELECT id FROM content_types WHERE code='knowledge'), '新手泡茶五大误区', '沸水泡绿茶、投茶凭感觉、久泡不出汤——最常见的五个坑一次讲清。', '误区一：沸水泡一切。绿茶芽叶细嫩，沸水直冲会烫熟出「闷熟味」，85℃ 上下才显鲜爽。

误区二：投茶凭手感。茶叶膨胀系数差异大（条索茶与球茶差一倍），备一只小秤，按 1:50 茶水比起步最稳。

误区三：一杯泡半天。茶叶久浸则茶多酚咖啡碱过量析出，又苦又涩。多泡快出汤，胜过一泡焖到底。

误区四：保温杯焖茶。持续高温使茶汤氧化变味，营养也打折扣。

误区五：饭后立即饮茶。茶多酚影响铁吸收，建议餐后半小时再喝。', NULL, '{"subtype":"brewing","difficulty":"beginner"}', 8, 1);
