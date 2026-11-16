import type { Router } from 'vue-router'

/** 仅依赖 use()，便于单测用假对象验证调用顺序。 */
export interface BootstrapApp {
  use: (plugin: unknown) => unknown
}

export interface BootstrapDeps {
  app: BootstrapApp
  router: Router
  /** 恢复 Cookie 登录态（失败也应继续挂载，由页面按未登录处理）。 */
  hydrate: () => Promise<void>
  mount: () => void
}

/**
 * 应用启动顺序：先恢复登录态，再安装 router（会触发首次导航），最后挂载。
 *
 * 若先 app.use(router)，vue-router 会在 install 时立即解析当前地址，
 * 此时守卫读到的 isLoggedIn 仍为 false，硬刷新 /my、/admin 会被误踢到登录页。
 */
export async function bootstrap({ app, router, hydrate, mount }: BootstrapDeps): Promise<void> {
  try {
    await hydrate()
  } catch {
    // 未登录或网络失败：按游客继续启动，避免白屏
  } finally {
    app.use(router)
    mount()
  }
}
