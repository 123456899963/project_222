# 中华茶产业全链路数字科普与实践辅助平台 - 技术规格说明书 (SDD)

> ⚠️ **历史草稿，非权威**：与 [docs/](../docs/) 冲突时一律以 `docs/` 为准；当前工程统一使用 npm。
>
> 版本: v0.1.0  
> 日期: 2026-11-03  
> 状态: 初稿

---

## 1. 技术选型

### 1.1 前端技术栈

| 类别 | 技术 | 版本 | 说明 |
|-----|------|------|-----|
| 框架 | Next.js | 14.x | React SSR框架，支持SDD开发 |
| 语言 | TypeScript | 5.x | 类型安全，提升代码质量 |
| 样式 | Tailwind CSS | 3.x | 原子化CSS，快速开发 |
| UI组件 | shadcn/ui | latest | 基于Radix的无样式组件 |
| 状态管理 | Zustand | 4.x | 轻量级状态管理 |
| 数据可视化 | ECharts | 5.x | 图表与地图 |
| 表单 | React Hook Form + Zod | latest | 类型安全的表单验证 |

### 1.2 后端技术栈 (Serverless优先)

| 类别 | 技术 | 版本 | 说明 |
|-----|------|------|-----|
| API | Next.js Route Handlers | - | 内置API路由 |
| 数据库 | PostgreSQL | 15.x | 关系型数据存储 |
| ORM | Drizzle ORM | latest | TypeScript-first ORM |
| 缓存 | Redis | 7.x | 会话与热点数据缓存 |
| 认证 | NextAuth.js | latest | 多种登录方式 |
| 存储 | Vercel Blob / S3 | - | 图片与文件存储 |

### 1.3 开发与测试工具链 (Harness)

| 类别 | 工具 | 说明 |
|-----|------|-----|
| 包管理 | npm（当前口径；历史草稿原为 pnpm） | 唯一 lockfile：`package-lock.json` |
| 构建 | Turbopack | 快速增量编译 |
| Lint | ESLint + Prettier | 代码规范 |
| 单元测试 | Vitest | Vite原生，极速测试 |
| 组件测试 | React Testing Library | 组件行为测试 |
| E2E测试 | Playwright | 端到端测试harness |
| API测试 | Hoppscotch | API接口测试 |
| Mock | MSW | Service Worker级Mock |
| 类型检查 | tsc --noEmit | CI中强制类型检查 |

### 1.4 CI/CD

| 类别 | 工具 | 说明 |
|-----|------|-----|
| 版本控制 | Git + GitHub | 代码管理 |
| CI | GitHub Actions | 自动化构建测试 |
| CD | Vercel | 自动部署 |
| 监控 | Vercel Analytics | 性能监控 |

---

## 2. 项目结构

```
tea-industry-platform/
├── .github/
│   └── workflows/
│       ├── ci.yml              # CI流水线
│       └── deploy.yml          # 部署流水线
├── specs/
│   ├── requirements.md         # 需求规格
│   └── technical.md            # 技术规格（本文件）
├── docs/
│   ├── architecture.md         # 架构文档
│   └── api-reference.md        # API文档
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── (marketing)/        # 营销页面组
│   │   ├── (dashboard)/        # 仪表盘页面组
│   │   ├── api/                # API路由
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── ui/                 # shadcn/ui组件
│   │   ├── layout/             # 布局组件
│   │   ├── data-viz/           # 数据可视化组件
│   │   └── features/           # 功能模块组件
│   ├── lib/
│   │   ├── db/                 # 数据库相关
│   │   │   ├── schema.ts
│   │   │   └── client.ts
│   │   ├── utils/              # 工具函数
│   │   ├── auth/               # 认证配置
│   │   └── validations/        # Zod验证schema
│   ├── server/
│   │   ├── services/          # 业务逻辑
│   │   └── repositories/      # 数据访问层
│   ├── types/                  # TypeScript类型定义
│   └── hooks/                  # 自定义Hooks
├── public/                      # 静态资源
├── tests/
│   ├── unit/                   # 单元测试
│   ├── integration/            # 集成测试
│   ├── e2e/                    # E2E测试
│   └── fixtures/               # 测试数据
├── drizzle/                    # 数据库迁移
├── .env.example
├── .eslintrc.json
├── .prettierrc
├── tsconfig.json
├── tailwind.config.ts
├── next.config.ts
├── vitest.config.ts
├── playwright.config.ts
├── drizzle.config.ts
├── package.json
├── package-lock.json           # npm 唯一 lockfile
└── README.md
```

---

## 3. 架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                      Client Layer                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ Next.js  │  │ React    │  │ ECharts  │  │ Tailwind│ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                      API Layer                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Next.js Route Handlers               │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │NextAuth  │  │  Zod     │  │ RateLimit│             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    Business Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Tea Service │  │ Market Svc   │  │ Practice Svc │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ User Service │  │ Data Repo    │  │ Cache Layer  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   Data Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │PostgreSQL│  │  Redis   │  │  S3/Blob │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
```

### 3.2 设计原则
- **规格驱动 (SDD)**: 所有功能开发基于规格文档
- **类型安全**: 端到端TypeScript
- **组件化**: 高内聚低耦合
- **可测试**: 业务逻辑与UI分离，易于单元测试
- **渐进增强**: 先MVP后迭代

---

## 4. 数据库Schema (Drizzle)

```typescript
// src/lib/db/schema.ts 预览

// 茶叶表
export const teas = pgTable('teas', {
  id: serial('id').primaryKey(),
  name: varchar('name', { length: 100 }).notNull(),
  category: text('category').notNull(), // green, black, oolong, white, yellow, dark
  origin: varchar('origin', { length: 200 }),
  description: text('description'),
  imageUrl: varchar('image_url', { length: 500 }),
  createdAt: timestamp('created_at').defaultNow(),
});

// 产区表
export const regions = pgTable('regions', {
  id: serial('id').primaryKey(),
  name: varchar('name', { length: 100 }).notNull(),
  province: varchar('province', { length: 50 }),
  coordinates: point('coordinates'), // PostGIS或自定义
  climate: varchar('climate', { length: 100 }),
});

// 市场数据表
export const marketData = pgTable('market_data', {
  id: serial('id').primaryKey(),
  teaId: integer('tea_id').references(() => teas.id),
  date: date('date').notNull(),
  price: decimal('price'),
  volume: integer('volume'),
  source: varchar('source', { length: 200 }),
});

// 用户表
export const users = pgTable('users', {
  id: varchar('id').primaryKey(),
  username: varchar('username', { length: 50 }).unique(),
  email: varchar('email', { length: 100 }).unique(),
  role: text('role').default('user'), // user, admin, expert
  createdAt: timestamp('created_at').defaultNow(),
});
```

---

## 5. API设计规范

### 5.1 RESTful API 约定
- 基础路径: `/api/v1`
- 使用 HTTP 方法: GET, POST, PUT, PATCH, DELETE
- 返回格式: `{ success: boolean, data?: T, error?: string }`
- 分页: `?page=1&limit=20`
- 过滤: `?filter[category]=green`

### 5.2 API示例
```
GET    /api/v1/teas              # 茶叶列表
GET    /api/v1/teas/:id          # 茶叶详情
POST   /api/v1/teas              # 创建茶叶
PUT    /api/v1/teas/:id          # 更新茶叶
DELETE /api/v1/teas/:id          # 删除茶叶
GET    /api/v1/teas/search?q=    # 搜索茶叶

GET    /api/v1/regions           # 产区列表
GET    /api/v1/regions/:id       # 产区详情

GET    /api/v1/market-data       # 市场数据
GET    /api/v1/market-data/trend # 价格趋势
```

---

## 6. 测试策略 (Harness)

### 6.1 测试金字塔
```
        /  E2E Tests  \          ← Playwright (10%)
       / Integration   \         ← Vitest + API Test (30%)
      /  Unit Tests     \        ← Vitest (60%)
```

### 6.2 测试配置
```typescript
// vitest.config.ts 预览
export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['tests/**/*.test.ts', 'tests/**/*.test.tsx'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
    },
  },
});

// playwright.config.ts 预览
export default defineConfig({
  testDir: './tests/e2e',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
});
```

### 6.3 CI检查项
- ✅ TypeScript 类型检查通过
- ✅ ESLint 无错误
- ✅ 单元测试通过 (覆盖率 > 80%)
- ✅ 构建成功
- ✅ E2E 测试通过

---

## 7. 开发规范

### 7.1 Git 分支策略
```
main      → 生产环境
develop   → 开发集成分支
feature/* → 功能分支
fix/*     → 修复分支
release/* → 发布准备分支
```

### 7.2 Commit Message 格式
```
<type>(<scope>): <subject>

feat:     新功能
fix:      修复
docs:     文档
style:    格式调整
refactor: 重构
test:     测试
chore:    构建/工具
```

### 7.3 代码规范
- 使用 TypeScript 严格模式
- 组件使用 PascalCase
- 函数/变量使用 camelCase
- 常量使用 UPPER_SNAKE_CASE
- 文件一个主要导出
- 所有函数有 JSDoc 注释

---

## 8. 环境配置

### 8.1 环境变量 (.env.example)
```bash
# 数据库
DATABASE_URL=postgresql://user:pass@localhost:5432/tea_platform
REDIS_URL=redis://localhost:6379

# 认证
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-here

# 存储
BLOB_STORAGE_URL=your-storage-url
```
