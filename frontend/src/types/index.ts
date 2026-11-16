/**
 * 共享 TS 类型定义
 * —— 与后端 Pydantic 模型一一对应
 * —— 集中放在这里，禁止到处散落 any
 */

// ===== 通用 =====
/** 后端统一响应体（成功/失败共用） */
export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
}

/** 数据可为空的响应（如 logout） */
export type ApiResponse<T = unknown> = ApiEnvelope<T | null>

export interface PaginationParams {
  page?: number
  page_size?: number
}

// ===== 认证 =====
export interface User {
  id: number
  username: string
  role: 'user' | 'admin'
  avatar_url: string | null // /uploads/... 或预置 /avatars/tea-0X.svg
  created_at: string // ISO8601 UTC
}

export interface LoginPayload {
  username: string
  password: string
}

export interface RegisterPayload {
  username: string
  password: string
}

/** 修改密码（API_CONTRACT §4.1.6） */
export interface ChangePasswordPayload {
  old_password: string
  new_password: string
}

/** 用户等级（S15 / API_CONTRACT §4.7.1）：四档，按收藏数实时计算 */
export interface UserLevel {
  name: '茶客' | '茶友' | '茶人' | '茶师'
  index: number // 1-4
  next_name: string | null
  next_threshold: number | null
  remaining: number
}

/** 当前用户统计（S15） */
export interface UserStats {
  favorite_count: number
  note_count: number
  share_count: number
  level: UserLevel
}

// ===== 茶品 =====
export type TeaCategory = 'green' | 'white' | 'yellow' | 'red' | 'oolong' | 'dark' | 'reprocessed'

/** 冲泡教程单步（ADR-0005）：标题 + 动作说明 + 可选提示 */
export interface BrewingStep {
  title: string
  detail: string
  tip?: string | null
}

/** 冲泡教程（ADR-0005）：逐茶独立维护，3–8 步 */
export interface BrewingGuide {
  intro?: string | null
  steps: BrewingStep[]
  caution?: string | null
}

/** 茶品详情（API_CONTRACT §2.3 TeaDetail） */
export interface Tea {
  id: number
  name: string
  category: TeaCategory
  origin: string
  season?: string | null
  fermentation?: string | null
  price_range?: string | null
  /** 价格区间数值（S2 五档筛选）：元/斤，null 表示未维护 */
  price_min?: number | null
  price_max?: number | null
  representative_variety?: string | null

  shape_desc: string
  soup_desc: string
  aroma_desc: string
  taste_desc: string

  water_temp?: number | null
  tea_amount?: number | null
  brew_time?: number | null

  main_image_url?: string | null
  /** 视频介绍（ADR-0003 S5）：null 时详情页隐藏视频区 */
  video_url?: string | null
  /** 视频时长（秒，≤180） */
  video_duration?: number | null
  /** 图片集（ADR-0003 S4）：按 sort_order 升序，最多 9 条 */
  image_set?: string[]
  is_active: boolean
  favorite_count: number

  tips_history?: string | null
  tips_suitable?: string | null
  tips_misconception?: string | null
  tips_official_note?: string | null

  /** 分步冲泡教程（ADR-0005）：null 时详情页退回三格速查卡 */
  brewing_guide?: BrewingGuide | null

  /** 已通过审核的用户科普投稿（S11 / S12），空数组由前端隐藏 */
  contributed_articles?: TeaArticle[]

  created_at: string // ISO8601 UTC 带 Z
  updated_at: string
}

/** 用户科普投稿（茶品详情内展示） */
export interface TeaArticle {
  id: number
  title: string | null
  content: string
  contributor: string
  created_at: string
}

/** 公开列表卡片（API_CONTRACT §2.2 TeaListItem） */
export interface TeaListItem {
  id: number
  name: string
  category: TeaCategory
  origin: string
  season?: string | null
  main_image_url?: string | null
  favorite_count: number
}

/** 茶品列表分页结构（API_CONTRACT §1.6） */
export interface TeaListData {
  items: TeaListItem[]
  total: number
  page: number
  page_size: number
}

/** 七大茶类计数（API_CONTRACT §2.3.1） */
export interface CategoryCount {
  category: TeaCategory
  count: number
}

/** 产地（省级）计数（API_CONTRACT §2.3.1） */
export interface OriginCount {
  origin: string
  count: number
}

export type TeaSort = 'newest' | 'favorite'

export interface TeaListParams {
  category?: string // 逗号分隔多选
  origin?: string
  season?: string
  /** 发酵程度（S2）：逗号分隔多选，枚举与后端一致 */
  fermentation?: string
  /** 价格下限 / 上限（元/斤，S2）：区间交集匹配 */
  price_min?: number
  price_max?: number
  /** 跨维度组合方式（S1）：默认 and */
  filter_mode?: 'and' | 'or'
  sort?: TeaSort
  keyword?: string
  page?: number
  page_size?: number
}

/** 首页最新小贴士（S7 / API_CONTRACT §4.2.9） */
export interface LatestTipItem {
  tea_id: number
  tea_name: string
  category: TeaCategory
  summary: string
  updated_at: string // ISO8601 UTC 带 Z
}

// ===== 收藏 =====
/** 收藏状态（API_CONTRACT §4.3） */
export interface FavoriteState {
  tea_id: number
  is_favorited: boolean
  favorite_count: number
  /** S9 多清单：该茶所在清单 ID 列表 */
  list_ids: number[]
}

// ===== 清单与笔记 =====
/** 当前生效分享摘要（API_CONTRACT §2.5） */
export interface ListShareBrief {
  token: string
  url: string
  created_at: string
}

/** 清单条目（含私有笔记） */
export interface ListItem {
  tea_id: number
  name: string
  category: TeaCategory
  origin: string
  season?: string | null
  main_image_url?: string | null
  favorite_count: number
  is_available: boolean
  tasting_note?: string | null
  favorited_at: string
}

/** 清单摘要（API_CONTRACT §4.4.1） */
export interface ListSummary {
  id: number
  title: string
  is_default: boolean
  tea_count: number
  created_at: string
  updated_at: string
  share?: ListShareBrief | null
}

/** 清单详情（API_CONTRACT §4.4.2） */
export interface ListData {
  id: number
  title: string
  is_default: boolean
  tea_count: number
  created_at: string
  updated_at: string
  share?: ListShareBrief | null
  items: ListItem[]
}

export interface TitleUpdateData {
  id: number
  title: string
  is_default: boolean
  updated_at: string
}

export interface NoteUpdateData {
  tea_id: number
  list_id: number
  tasting_note: string | null
}

// ===== 分享 =====
export interface ShareGenerateData {
  token: string
  url: string
  created_at: string
  is_new: boolean
}

export interface ShareRevokeData {
  token: string
  is_active: boolean
  revoked_at: string
}

/** 公开分享条目（绝不含 tasting_note） */
export interface ShareViewItem {
  tea_id: number
  name: string
  category: TeaCategory
  origin: string
  season?: string | null
  main_image_url?: string | null
  favorite_count: number
  is_available: boolean
}

export interface ShareViewData {
  token: string
  title: string
  tea_count: number
  created_at: string
  revoked: boolean
  is_owner: boolean
  items: ShareViewItem[]
}

export interface CopyResult {
  added: number
  skipped: number
  total: number
}

// ===== 管理员后台（API_CONTRACT §4.6） =====
/** 后台列表条目：含下架茶品与 is_active */
export interface AdminTeaListItem {
  id: number
  name: string
  category: TeaCategory
  origin: string
  season?: string | null
  main_image_url?: string | null
  is_active: boolean
  favorite_count: number
  created_at: string
  updated_at: string
}

export interface AdminTeaListData {
  items: AdminTeaListItem[]
  total: number
  page: number
  page_size: number
}

export interface AdminTeaListParams {
  category?: string
  keyword?: string
  is_active?: boolean
  sort?: TeaSort
  page?: number
  page_size?: number
}

/** 茶品主体字段（新增/编辑共用；不含 id/is_active/favorite_count） */
export interface AdminTeaPayload {
  name: string
  category: TeaCategory
  origin: string
  season: string | null
  fermentation: string | null
  price_range: string | null
  representative_variety: string | null
  shape_desc: string
  soup_desc: string
  aroma_desc: string
  taste_desc: string
  water_temp: number
  tea_amount: number
  brew_time: number
  main_image_url: string
  /** 视频（ADR-0003 S5）：仅本站 /uploads/ 路径 */
  video_url?: string | null
  video_duration?: number | null
}

export interface AdminTeaCreatePayload extends AdminTeaPayload {
  tips_history: string | null
  tips_suitable: string | null
  tips_misconception: string | null
  tips_official_note: string | null
}

export interface AdminTipsPayload {
  tips_history?: string | null
  tips_suitable?: string | null
  tips_misconception?: string | null
  tips_official_note?: string | null
}

export interface AdminTipsData {
  tea_id: number
  tips_history: string | null
  tips_suitable: string | null
  tips_misconception: string | null
  tips_official_note: string | null
}

export interface AdminToggleData {
  id: number
  is_active: boolean
  updated_at: string
}

/** 管理员整篇保存冲泡教程（ADR-0005） */
export interface AdminBrewingGuidePayload {
  intro?: string | null
  steps: BrewingStep[]
  caution?: string | null
}

export interface AdminBrewingGuideData extends BrewingGuide {
  tea_id: number
}

export interface AdminStatsData {
  total_count: number
  active_count: number
  inactive_count: number
  category_distribution: CategoryCount[]
}

/** 操作日志条目（API_CONTRACT §4.6.12）：admin_id 对应 operation_logs.user_id */
export interface AdminOperationLogItem {
  id: number
  admin_id: number | null
  admin_username: string | null
  action: string
  target_type: string
  target_id: number | null
  detail: string | null
  ip_address: string | null
  created_at: string
}

export interface AdminOperationLogListData {
  items: AdminOperationLogItem[]
  total: number
  page: number
  page_size: number
}

export interface AdminOperationLogListParams {
  action?: string
  target_type?: string
  admin_id?: number
  /** YYYY-MM-DD（含边界） */
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}

export interface AdminUploadData {
  url: string
  original_filename: string
  size: number
  content_type: string
}

/** 视频上传结果（ADR-0003 S5）：duration 为服务端解析秒数 */
export interface AdminVideoUploadData extends AdminUploadData {
  duration: number
}

/** 茶品图片集条目（ADR-0003 S4） */
export interface TeaMediaItem {
  id: number
  image_url: string
  sort_order: number
}

// ===== 用户贡献（S10–S13 / API_CONTRACT §4.8） =====
export type ContributionType = 'new_tea' | 'article'
export type ContributionStatus = 'pending' | 'approved' | 'rejected'

/** 用户提交的新茶字段（主图选填，X7 不开放图片投稿） */
export interface ContributionTeaPayload {
  name: string
  category: TeaCategory
  origin: string
  season: string | null
  fermentation: string | null
  price_range: string | null
  representative_variety: string | null
  shape_desc: string
  soup_desc: string
  aroma_desc: string
  taste_desc: string
  water_temp: number
  tea_amount: number
  brew_time: number
  main_image_url: string | null
  tips_history: string | null
  tips_suitable: string | null
  tips_misconception: string | null
  tips_official_note: string | null
}

export interface ContributionCreatePayload {
  type: ContributionType
  tea?: ContributionTeaPayload
  target_tea_id?: number
  title?: string | null
  content?: string
}

export interface ContributionItem {
  id: number
  type: ContributionType
  status: ContributionStatus
  target_tea_id: number | null
  target_tea_name: string | null
  payload: Record<string, unknown>
  reject_reason: string | null
  reviewer_id: number | null
  reviewed_at: string | null
  created_at: string
  username?: string | null
}

export interface ContributionListData {
  items: ContributionItem[]
  total: number
  page: number
  page_size: number
}

export interface ContributionListParams {
  status?: ContributionStatus
  type?: ContributionType
  page?: number
  page_size?: number
}

// ===== 内容板块（批次五 R1–R5 / API_CONTRACT §4.2.10–11） =====
export type ContentTypeCode = 'teaware' | 'origin' | 'culture' | 'brand' | 'knowledge'

/** 板块分类（API_CONTRACT §4.2.10） */
export interface ContentTypeItem {
  id: number
  code: ContentTypeCode
  name: string
  icon: string | null
  description: string | null
  sort_order: number
}

/** 内容条目（前台列表/详情共用） */
export interface ContentItem {
  id: number
  type_id: number
  type_code: ContentTypeCode
  title: string
  summary: string | null
  body: string | null
  cover_image: string | null
  meta: Record<string, unknown> | null
  sort_order: number
  is_active?: boolean | null // 后台返回（前台详情不含）
  created_at: string
  updated_at: string
}

export interface ContentListParams {
  type?: ContentTypeCode
  keyword?: string
  page?: number
  page_size?: number
}

export interface ContentListData {
  items: ContentItem[]
  total: number
  page: number
  page_size: number
}

/** 后台列表条目（含下架） */
export interface AdminContentListItem {
  id: number
  type_code: ContentTypeCode
  title: string
  summary: string | null
  is_active: boolean
  sort_order: number
  created_at: string
  updated_at: string
}

export interface AdminContentListData {
  items: AdminContentListItem[]
  total: number
  page: number
  page_size: number
}

export interface AdminContentListParams {
  type?: ContentTypeCode
  is_active?: boolean
  page?: number
  page_size?: number
}

export interface AdminContentCreatePayload {
  type_code: ContentTypeCode
  title: string
  summary?: string | null
  body?: string | null
  cover_image?: string | null
  meta?: Record<string, unknown> | null
  sort_order?: number
}

export interface AdminContentUpdatePayload {
  title?: string
  summary?: string | null
  body?: string | null
  cover_image?: string | null
  meta?: Record<string, unknown> | null
  sort_order?: number
  is_active?: boolean
}
