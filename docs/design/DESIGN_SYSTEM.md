# 茶·图鉴 — 设计规范系统

> **设计方向**：方案一「清新水墨」—— 新中式极简 × 东方留白  
> **适用范围**：学生端全部页面 + 管理员后台  
> **实现依据**：PRD v1.1 定稿 + Tailwind CSS v4 (`@theme` 指令)  
> **更新日期**：2026-11-04  
> **后续所有页面必须遵守本规范**

---

## 0. 技术映射说明

本规范中的所有颜色值、尺寸值均对应 Tailwind v4 的 CSS 变量实现。  
在 `src/app/globals.css` 的 `@theme { ... }` 块中定义变量后，组件中可直接使用 `bg-primary`、`text-muted` 等工具类。

---

## 1. 颜色系统

### 1.1 品牌主色

| 名称 | CSS 变量 | Tailwind 类 | HEX | RGB | 用途 |
|---|---|---|---|---|---|
| 茶褐（主色） | `--color-primary` | `bg-primary` / `text-primary` | `#8B7355` | 139, 115, 85 | 主按钮、品牌 Logo 色、链接高亮、筛选选中态 |
| 茶褐-悬浮 | `--color-primary-hover` | `hover:bg-primary-hover` | `#7A6548` | 122, 101, 72 | 主按钮 hover 背景 |
| 茶褐-深 | `--color-primary-dark` | `text-primary-dark` | `#6B5740` | 107, 87, 64 | 强调文字、重要标题 |

### 1.2 七大茶类标签色（核心识别体系）

| 茶类 | CSS 变量 | Tailwind 类 | HEX | 使用场景 |
|---|---|---|---|---|
| 绿茶 | `--color-tea-green` | `bg-tea-green` / `text-tea-green` | `#5CB85C` | 茶类标签、筛选选中态、详情页标签 |
| 白茶 | `--color-tea-white` | `bg-tea-white` / `text-tea-white` | `#D4D0C8` | 同上（注意浅背景上需深色文字） |
| 黄茶 | `--color-tea-yellow` | `bg-tea-yellow` / `text-tea-yellow` | `#E6C25B` | 同上 |
| 红茶 | `--color-tea-red` | `bg-tea-red` / `text-tea-red` | `#C0392B` | 同上 |
| 乌龙茶 | `--color-tea-oolong` | `bg-tea-oolong` / `text-tea-oolong` | `#D35400` | 同上 |
| 黑茶 | `--color-tea-dark` | `bg-tea-dark` / `text-tea-dark` | `#4A3728` | 同上 |
| 再加工茶 | `--color-tea-reprocessed` | `bg-tea-reprocessed` / `text-tea-reprocessed` | `#B98A9B` | 同上（柔和玫瑰色，与六类基础茶色区分） |

**标签使用规则**：
- 未选中态：`border` 1px solid 对应茶类色，`text` 对应茶类色，`bg-transparent`
- 选中态：`bg` 对应茶类色，`text-white`，无边框
- 白茶特例：选中态 `bg-tea-white`，`text-primary-dark`（因为 #D4D0C8 偏浅，白字对比度不够）

### 1.3 背景色

| 名称 | CSS 变量 | Tailwind 类 | HEX | 用途 |
|---|---|---|---|---|
| 页面主背景 | `--color-bg-page` | `bg-bg-page` | `#FAF8F5` | 全站 body 背景，暖米白，替代纯白避免刺眼 |
| 卡片/面板背景 | `--color-bg-surface` | `bg-bg-surface` | `#FFFFFF` | 茶品卡片、筛选面板、表单、弹窗 |
| 次级分区背景 | `--color-bg-muted` | `bg-bg-muted` | `#F5F1EC` | 详情页 tag 区底色、列表页分区背景 |
| 深色区块（Hero） | `--color-bg-hero` | `bg-bg-hero` | `#2C2418` | 首页 Hero 背景（茶褐深色调） |

### 1.4 文字颜色

| 名称 | CSS 变量 | Tailwind 类 | HEX | 对比度 | 用途 |
|---|---|---|---|---|---|
| 主文字 | `--color-text-primary` | `text-text-primary` | `#2C2C2C` | 高 | 页面标题、卡片标题、正文 |
| 次文字 | `--color-text-secondary` | `text-text-secondary` | `#6B6560` | 中 | 列表副标题、描述性文字、面包屑 |
| 辅助文字 | `--color-text-muted` | `text-text-muted` | `#9A9590` | 低 | 时间戳、次要标签、空状态提示 |
| 反白文字 | `--color-text-inverse` | `text-text-inverse` | `#FFFFFF` | — | Hero 区、深背景上的文字 |
| 链接文字 | `--color-text-link` | `text-text-link` | `#8B7355` | — | 可点击链接，hover 加深为 `#7A6548` |

### 1.5 语义色（反馈/状态）

| 名称 | CSS 变量 | Tailwind 类 | HEX | 用途 |
|---|---|---|---|---|
| 成功 | `--color-success` | `text-success` / `bg-success` | `#2E7D32` | 操作成功提示、已收藏状态 |
| 警告 | `--color-warning` | `text-warning` / `bg-warning` | `#E68A00` | 筛选无结果提醒、下架茶品提示 |
| 错误 | `--color-error` | `text-error` / `bg-error` | `#C62828` | 表单校验失败、操作错误 |
| 信息 | `--color-info` | `text-info` / `bg-info` | `#1565C0` | 系统通知、帮助提示 |

### 1.6 边框色

| 名称 | CSS 变量 | Tailwind 类 | HEX | 用途 |
|---|---|---|---|---|
| 主边框 | `--color-border` | `border-border` | `#EDEBE8` | 卡片边框、分割线、输入框边框 |
| 次级边框 | `--color-border-light` | `border-border-light` | `#F5F1EC` | 卡片内部分割、列表 item 分割 |
| 深色边框 | `--color-border-dark` | `border-border-dark` | `#D5D0CA` | hover 边框、选中态轮廓 |

---

## 2. 字体系统

### 2.1 字体家族

| 角色 | CSS 变量 | Tailwind 类 | 字体栈 |
|---|---|---|---|
| 正文 | `--font-sans` | `font-sans` | `"PingFang SC", "Noto Sans SC", "Microsoft YaHei", system-ui, sans-serif` |
| 标题 | `--font-display` | `font-display` | `"Noto Serif SC", "Source Han Serif SC", Georgia, serif` |
| 数字/代码 | `--font-mono` | `font-mono` | `"SF Mono", "JetBrains Mono", Consolas, monospace` |

### 2.2 字号、字重、行高

| 名称 | 字号 | 字重 | 行高 | Tailwind 类 | 使用场景 |
|---|---|---|---|---|---|
| Display (超大标题) | 48px / 3rem | 700 | 1.2 | `text-display` | 首页 Hero 主标题 |
| H1 (页面大标题) | 32px / 2rem | 600 | 1.3 | `text-h1` | 页面标题、详情页茶品名 |
| H2 (区块标题) | 24px / 1.5rem | 600 | 1.4 | `text-h2` | 首页"热门推荐"、详情页"小贴士区" |
| H3 (卡片标题) | 18px / 1.125rem | 500 | 1.4 | `text-h3` | 列表卡片标题、管理员后台表格标题 |
| Body (正文) | 16px / 1rem | 400 | 1.6 | `text-body` | 详情页四大感官描述、表单 label |
| Small (次要文字) | 14px / 0.875rem | 400 | 1.5 | `text-small` | 面包屑、收藏数、时间戳 |
| Caption (说明文字) | 12px / 0.75rem | 400 | 1.5 | `text-caption` | 表单校验提示、版权信息 |

---

## 3. 空间与布局系统

### 3.1 内容区域宽度

| 断点 | 宽度 | 容器 class | 说明 |
|---|---|---|---|
| 移动端 (< 640px) | 100% - 32px 内边距 | `max-w-full px-4` | 单列布局 |
| 平板 (640px - 1023px) | 100% - 48px 内边距 | `max-w-4xl px-6` | 2-3 列布局 |
| 桌面 (≥ 1024px) | 1200px（居中） | `max-w-6xl mx-auto px-8` | 3-4 列布局 |
| 管理员后台 | 100% - 侧边栏 | 全宽 | 左侧边栏 240px + 右侧主内容区 |

### 3.2 间距（4px 基准网格）

| 名称 | 值 | Tailwind 类 | 使用场景 |
|---|---|---|---|
| xs | 4px | `gap-1` / `p-1` | 图标与文字间距、tag 内边距 |
| sm | 8px | `gap-2` / `p-2` | 按钮内边距、卡片内紧凑元素间距 |
| md | 16px | `gap-4` / `p-4` | 卡片内元素、列表 item、表单控件间距 |
| lg | 24px | `gap-6` / `p-6` | 卡片外边距、区块间距、表单 group 间距 |
| xl | 32px | `gap-8` / `p-8` | 大区块间距、弹窗内边距 |
| 2xl | 48px | `gap-12` / `p-12` | Hero 底部 padding、section 间距 |
| 3xl | 64px | `gap-16` / `p-16` | 首页大 section 间距 |

### 3.3 圆角

| 名称 | 值 | Tailwind 类 | 使用场景 |
|---|---|---|---|
| sm | 4px | `rounded-sm` | 小 tag、紧凑的输入框 |
| md | 8px | `rounded-md` | 按钮、输入框、表格单元格 |
| lg | 12px | `rounded-lg` | 筛选 chips、标签徽章 |
| xl | 16px | `rounded-xl` | 茶品卡片、面板、弹窗（**主要圆角**） |
| 2xl | 20px | `rounded-2xl` | Hero 内容容器、大幅装饰块 |
| full | 9999px | `rounded-full` | 头像、胶囊按钮 |

---

## 4. 通用组件规范

### 4.1 按钮

#### 主按钮（Primary Button）

```
尺寸: 高度 44px（桌面） / 40px（移动），padding 0 24px
圆角: rounded-full（胶囊形）
背景: bg-primary (#8B7355)
文字: text-white, font-medium
边框: 无
hover: bg-primary-hover (#7A6548)，translateY(-1px) 微抬升
active: scale(0.98)
disabled: opacity-40，cursor-not-allowed
```

#### 次按钮（Secondary Button）

```
尺寸: 同主按钮
圆角: rounded-full
背景: bg-transparent
边框: 1px solid primary (#8B7355)
文字: text-primary, font-medium
hover: bg-primary/5（极淡填充）
active: scale(0.98)
```

#### 幽灵按钮（Ghost Button）

```
尺寸: 高度 36px，padding 0 16px
圆角: rounded-md
背景: bg-transparent
文字: text-text-secondary, font-normal
hover: bg-bg-muted (#F5F1EC)
```

#### 图标按钮（Icon Button）

```
尺寸: 40px × 40px
圆角: rounded-full
背景: bg-bg-surface
边框: 1px solid border (#EDEBE8)
hover: bg-bg-muted
适用: 收藏、分享、笔记等圆形操作按钮
```

### 4.2 输入框

#### 标准输入框

```
高度: 44px
圆角: rounded-md (8px)
背景: bg-bg-surface
边框: 1px solid border (#EDEBE8)
内边距: 0 16px
文字: text-body (16px), text-text-primary
placeholder: text-text-muted (#9A9590)
focus: border-primary (#8B7355), box-shadow 0 0 0 3px rgba(139,115,85,0.12)
error: border-error (#C62828), box-shadow 0 0 0 3px rgba(198,40,40,0.12)
disabled: bg-bg-muted, text-text-muted, cursor-not-allowed
```

#### 搜索框（首页 Hero 版）

```
高度: 56px
圆角: rounded-full (28px)
背景: bg-bg-surface + 轻微阴影 box-shadow 0 2px 12px rgba(0,0,0,0.08)
内边距: 左 56px (图标位)，右 24px
focus: 阴影加深为 0 4px 20px rgba(0,0,0,0.12)
```

#### 文本域（多行）

```
最小高度: 120px
圆角: rounded-md
其余同标准输入框
```

### 4.3 茶品图鉴卡片（核心组件）

#### 列表页卡片（Grid Card）

```
尺寸: 响应式网格 — 桌面 3 列 / 平板 2 列 / 移动 1 列
内边距: p-0（图片无内边距），信息区 padding 12px 2px 0（无白底）
圆角: rounded-lg (12px) —— 仅图片区圆角，信息区不建容器
背景: transparent（直接落在 bg-bg-page 上）
边框: 无（去框化，靠图片圆角与留白分隔）
图片区: 顶部 16:10 比例，object-cover，四角圆角
信息区: 图片下方两行，含以下内容：
  - 第一行 茶品名称: text-h3 (18px)，font-semibold，text-text-primary，单行溢出省略
  - 第二行 元信息（一行收口）: text-small (14px)，text-text-muted
    `● 茶类色圆点 · 产地 · ♡ 收藏数`，产地可省略号截断，收藏数右对齐
  - 不再单独展示茶类徽章与季节，避免信息分散

hover 状态:
  - 图片 scale(1.04)，过渡使用 --motion-duration-slow / --motion-ease
  - 茶名变为 text-primary (#8B7355)
  - 无阴影、无 translateY
```

#### 首页热门推荐卡（横向滚动）

```
尺寸: 宽度 200px，同列表卡结构，但高度压缩
内边距: 信息区 p-3
圆角: rounded-xl
图片区: 16:11 比例
信息区:
  - 茶品名称: text-h3 (16px)
  - 产地: text-small
```

#### 首页随机发现卡（单张大卡）

```
尺寸: 单张宽度 320px
内边距: p-0
圆角: rounded-2xl (20px)
图片区: 16:9 大图，带极细边框
信息区:
  - 茶品名称: text-h2 (20px)
  - 茶类 + 产地: text-small + 茶类大徽章
  - 冲泡参考（亮点）: text-small text-text-secondary
```

### 4.4 标签 / Badge / Chip

#### 七大茶类筛选 Chip（未选中）

```
高度: 36px
圆角: rounded-lg (12px)
背景: bg-transparent
边框: 1px solid 对应茶类色
文字: text-small (14px)，对应茶类色，font-medium
内边距: 0 16px
hover: bg-对应茶类色/10（极淡）
```

#### 七大茶类筛选 Chip（选中）

```
高度: 36px
圆角: rounded-lg
背景: 对应茶类色（白茶除外，见 1.2 节规则）
文字: text-white，font-medium
边框: 无
hover: 同色，opacity 保持 1
```

#### 茶类小徽章（详情页 tag 区）

```
高度: 28px
圆角: rounded-md (8px)
背景: bg-bg-muted (#F5F1EC)
文字: text-caption (12px)，text-text-secondary
内边距: 0 12px
可点击: 可跳转回列表页并带上筛选参数
```

#### 状态徽章（管理员后台）

| 状态 | 背景 | 文字 | 圆角 |
|---|---|---|---|
| 已上架 | `bg-success/10` | `text-success` | rounded-md |
| 已下架 | `bg-text-muted/10` | `text-text-muted` | rounded-md |
| 已收藏 | `bg-primary/10` | `text-primary` | rounded-md |

### 4.5 导航栏

#### 公共导航栏（桌面端）

```
高度: 64px
背景: 
  - 首页 Hero 区域：bg-transparent + backdrop-blur
  - 其他页面：bg-bg-surface (#FFFFFF)
底部边框: 1px solid border (#EDEBE8)
z-index: 50
布局: 左 Logo（40px 高度）+ 中间导航链接 + 右搜索框(可选) + 用户操作区

导航链接:
  - 文字: text-text-secondary, text-body, font-medium
  - hover / active: text-primary
  - 底部 2px 指示线（当前激活项）

Logo:
  - 单线条茶叶图标（SVG），40px 高度
  - 旁边"茶·图鉴"文字: text-h3, text-primary-dark
```

#### 公共导航栏（移动端）

```
高度: 56px
布局: 左 Logo + 右汉堡菜单图标
抽屉展开: 从右侧滑入，背景 bg-bg-surface
```

#### 管理员后台侧边栏

```
宽度: 240px（桌面固定）/ 可折叠
背景: bg-bg-surface
右侧边框: 1px solid border
高度: 100vh（sticky）
菜单项高度: 44px
菜单项: icon (20px) + label，左内边距 20px
选中态: bg-primary/5，左侧 3px bg-primary 指示条
hover: bg-bg-muted
底部: 管理员信息卡片（头像 + 名称 + 退出按钮）
```

### 4.6 筛选面板

```
位置: 列表页顶部，紧贴面包屑下方的工具条
布局: 单行工具条 —— 左侧七大茶类 chips，右侧「筛选」按钮 + 排序下拉；产地 / 季节 / 发酵 / 价格折叠进展开面板（默认收起，有高级筛选时自动展开）
筛选按钮: 高 36px，rounded-md，1px border-dark；带高级筛选数量角标（pill，bg-primary）与展开箭头
展开面板: bg-bg-surface + 1px border + rounded-lg，内边距 20px，内部维度横向排列
每个维度标签: text-caption + 对应维度枚举 chips
已选条件区:
  - 位置: 筛选面板下方或右侧
  - 样式: 小尺寸 pill（rounded-full, h-28px），带 × 移除按钮
  - "清除全部"按钮: 最右侧，text-small text-text-link
```

### 4.7 区块标题（Section Kicker）

```
结构: 英文小标（kicker） + 中文标题（衬线） + 可选一行说明
kicker: text-caption，letter-spacing 0.24em，text-transform uppercase，text-text-muted
居中区块: kicker 两侧各 32px × 1px 发丝线（border-dark），与文字间距 12px
左对齐区块: kicker 左对齐、不带发丝线，标题右侧保留动作链接（查看全部 / 探索更多）
间距: kicker 与中文标题 6–12px，标题与说明 8px
禁止: 在中文标题中使用 emoji 前缀（表情符号不参与新中式视觉体系）
```

### 4.8 双行主标题

```
用途: 首页 Hero 等强视觉区块
规则: 第一行 text-primary，第二行落 color-primary-dark，两行各自成块（display:block）
行高: 1.2；字号沿用 text-display（移动端 28px）
说明: 第二行为语义延伸而非新信息，不得拆成两个语义层级（整体仍是一个 h1）
```

### 4.9 沉浸式首屏（Hero Scene）

```
结构: 背景图层 / 暗色压边层 / 内容层 三层，内容层 z-index 最高
背景: 铺满视口（min-height: max(560px, 100vh - 64px)），超出层高 20% 供视差下移
压边: 竖向渐变，顶部 0.62 → 中段 0.18 → 72% 处 0.52 → 底部 0.86（茶褐黑 #201a14）
      —— 中段必须留亮，避免整片压暗让照片发灰；不做斜向渐变，防止出现可见分界
文字: 标题 text-inverse、第二行 tea-yellow；副标题 rgba(255,255,255,0.9)
      —— 深色压边上不再使用白色描边光晕，改用暗色投影
页头: 首屏透明态（背景透明、文字与控件转白），滚过 Hero 后转纯白态
视差: 背景 translateY(scroll × 0.28)，内容 translateY(scroll × -0.06) 并按 scroll/360 淡出
滚动提示: 底部居中小字 + 44px 竖线呼吸动画，滚动 160px 内淡出
降级: prefers-reduced-motion 下关闭视差与呼吸动画，仅保留静态排版
```

### 4.10 一级页面标题区（Page Header）

```
适用范围: 首页之外的前台一级页面（列表 / 对比 / 详情 / 我的 / 分享 / 投稿）
顶部留白: 固定页头 64px 之下再留 24px，即 padding-top 88px；≤767px 为 76px（页头 56px + 20px）
         —— 全站一级页面统一，禁止再回落到 64px（紧贴页头）或 32px（被页头遮挡）
结构: 英文小标（kicker） + 中文标题（衬线 font-display）+ 可选一行说明
kicker: 全局类 .page-kicker（text-caption / letter-spacing 0.24em / uppercase / text-muted）
居中区块: 追加 .page-kicker--center，两侧各 32px × 1px 发丝线，与文字间距 12px
已有自带眉标或徽章的页面（我的清单 eyebrow、分享页 badges）不再叠加 kicker，避免双层小标
面包屑: 统一使用「›」分隔，位于标题区之上
```

---

## 5. 状态组件

### 5.1 加载状态

#### 页面级加载

```
背景: bg-bg-page
内容: 居中 spinner + "加载中..."
Spinner: 24px, border 2px, border-primary, 旋转动画 1s linear infinite
文字: text-text-muted, text-small
```

#### 卡片骨架屏

```
高度: 与实际卡片相同（约 280px）
背景: bg-bg-surface
内容区: 顶部图片占位（bg-bg-muted, 16:10 比例）+ 下方 3 行文字占位（bg-bg-muted, height 14/12/12px）
动画: shimmer 1.5s infinite
```

### 5.2 空数据状态

```
内边距: py-16 px-6
内容:
  - 图标: 64px, text-text-muted
  - 主文案: text-h3, text-text-secondary，如"暂无符合条件的茶品"
  - 副文案: text-small, text-text-muted，如"试试调整筛选条件"
  - 引导按钮（可选）: 次按钮，如"清除全部筛选"
布局: 居中对齐
```

### 5.3 错误状态

#### 表单校验错误

```
位置: 输入框下方 4px
文案: text-caption, text-error
输入框边框: 变红（见 4.2 节 error 态）
```

#### 页面级错误

```
内边距: py-24 px-6
内容:
  - 图标: 64px, text-error
  - 主文案: text-h2, text-text-primary
  - 副文案: text-body, text-text-secondary
  - 按钮: 主按钮"重新加载" / 次按钮"返回首页"
布局: 居中对齐
```

#### Toast 提示（轻量反馈）

```
位置: 视窗底部居中，距底 24px
内边距: px-5 py-3
圆角: rounded-lg
背景: 
  - 成功: bg-success, text-white
  - 警告: bg-warning, text-white
  - 错误: bg-error, text-white
  - 信息: bg-bg-surface + border 1px border, text-text-primary
圆角: rounded-lg
动画: slideUp 0.3s
自动消失: 3s
```

---

## 6. 响应式规则

### 6.1 断点定义（沿用 Tailwind 默认，不自定义）

| 名称 | 最小宽度 | CSS 媒体查询 | 使用场景 |
|---|---|---|---|
| 默认（移动优先） | — | — | 单列布局，汉堡菜单导航 |
| sm | ≥ 640px | `@media (min-width: 640px)` | 筛选面板横向排列 |
| md | ≥ 768px | `@media (min-width: 768px)` | 卡片 2 列网格，管理员侧边栏展开 |
| lg | ≥ 1024px | `@media (min-width: 1024px)` | 卡片 3-4 列网格，完整导航栏 |
| xl | ≥ 1280px | `@media (min-width: 1280px)` | 内容容器达到最大 1200px，完全居中 |

### 6.2 组件级响应式规则

| 组件 | 桌面 (≥ 1024px) | 平板 (640-1023px) | 移动 (< 640px) |
|---|---|---|---|
| 列表页卡片网格 | 3 列 grid，gap-6 | 2 列 grid，gap-4 | 单列，gap-4 |
| 导航栏 | 完整导航链接 + 搜索框 | 完整导航 | 汉堡抽屉 |
| 筛选面板 | 横向展开 | 横向展开 | 折叠抽屉，点击展开 |
| 详情页布局 | 左右分栏（图片 + 信息） | 左右分栏 | 上下堆叠 |
| 搜索框高度 | 56px | 52px | 48px |
| Hero 标题字号 | text-display (48px) | text-h1 (32px) | text-h1 (28px) |
| 首页热门推荐卡 | 宽度 200px，横向滚动 | 宽度 180px | 宽度 160px |
| 按钮高度 | 44px | 44px | 40px |
| 管理员侧边栏 | 展开 240px | 展开 200px | 隐藏 + 抽屉 |
| 表格 | 完整表格显示 | 完整表格 | 卡片式列表（每条一行） |

### 6.3 安全区与最小触达尺寸

| 规则 | 值 | 说明 |
|---|---|---|
| 最小可点击区域 | 44px × 44px | 移动端所有可点击元素（按钮、链接、卡片） |
| 移动安全区 | 顶部 16px / 底部 24px | 避开刘海屏和底部手势条 |
| 触控目标间距 | ≥ 8px | 相邻按钮间至少 8px 间距，防误触 |

---

## 7. Tailwind v4 配置映射

以下变量需在 `src/app/globals.css` 的 `@theme { ... }` 块中定义：

```css
@theme {
  /* === 品牌主色 === */
  --color-primary: #8B7355;
  --color-primary-hover: #7A6548;
  --color-primary-dark: #6B5740;

  /* === 七大茶类标签色 === */
  --color-tea-green: #5CB85C;
  --color-tea-white: #D4D0C8;
  --color-tea-yellow: #E6C25B;
  --color-tea-red: #C0392B;
  --color-tea-oolong: #D35400;
  --color-tea-dark: #4A3728;
  --color-tea-reprocessed: #B98A9B;

  /* === 背景色 === */
  --color-bg-page: #FAF8F5;
  --color-bg-surface: #FFFFFF;
  --color-bg-muted: #F5F1EC;
  --color-bg-hero: #2C2418;

  /* === 文字颜色 === */
  --color-text-primary: #2C2C2C;
  --color-text-secondary: #6B6560;
  --color-text-muted: #9A9590;
  --color-text-inverse: #FFFFFF;
  --color-text-link: #8B7355;

  /* === 语义色 === */
  --color-success: #2E7D32;
  --color-warning: #E68A00;
  --color-error: #C62828;
  --color-info: #1565C0;

  /* === 边框色 === */
  --color-border: #EDEBE8;
  --color-border-light: #F5F1EC;
  --color-border-dark: #D5D0CA;

  /* === 字体 === */
  --font-sans: "PingFang SC", "Noto Sans SC", "Microsoft YaHei", system-ui, sans-serif;
  --font-display: "Noto Serif SC", "Source Han Serif SC", Georgia, serif;
  --font-mono: "SF Mono", "JetBrains Mono", Consolas, monospace;

  /* === 字号 === */
  --text-display: 3rem;         /* 48px */
  --text-h1: 2rem;              /* 32px */
  --text-h2: 1.5rem;            /* 24px */
  --text-h3: 1.125rem;          /* 18px */
  --text-body: 1rem;            /* 16px */
  --text-small: 0.875rem;       /* 14px */
  --text-caption: 0.75rem;      /* 12px */

  /* === 圆角 === */
  --radius-xs: 4px;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --radius-full: 9999px;

  /* === 阴影 === */
  --shadow-card: 0 8px 24px rgba(0, 0, 0, 0.06);
  --shadow-card-hover: 0 12px 32px rgba(0, 0, 0, 0.10);
  --shadow-hero: 0 2px 12px rgba(0, 0, 0, 0.08);
  --shadow-dropdown: 0 4px 20px rgba(0, 0, 0, 0.12);
  --shadow-modal: 0 20px 60px rgba(0, 0, 0, 0.20);
}
```

---

## 8. 设计规范检查清单

每次提交页面代码前，自检以下项目：

- [ ] **颜色使用**：所有颜色来自 `@theme` 变量定义，不出现硬编码 HEX 值
- [ ] **字体使用**：字号从规范中选取，不使用 `text-[22px]` 这类任意值
- [ ] **圆角**：从 6 个预设值中选择
- [ ] **间距**：遵循 4px 基准网格（4/8/16/24/32/48/64）
- [ ] **茶品卡片**：图片 16:10、圆角 16px、hover translateY(-2px) + 阴影、七大茶类标签色正确
- [ ] **按钮**：圆角胶囊、主/次/幽灵/图标四种不混用
- [ ] **输入框**：focus 态有 3px primary 环、error 态有 3px error 环
- [ ] **茶类筛选 Chip**：未选中 outline + 选中实心，白茶例外处理
- [ ] **响应式**：移动端单列、平板 2 列、桌面 3+ 列，导航栏折叠正确
- [ ] **安全区**：移动端所有按钮 ≥ 44px 可点击，触控间距 ≥ 8px
- [ ] **空状态**：筛选无结果/列表为空都有友好文案 + 引导按钮
- [ ] **管理员后台**：侧边栏 240px、菜单项选中指示条 3px primary
