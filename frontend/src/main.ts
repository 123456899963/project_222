import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import { bootstrap } from './bootstrap'
import router from './router'
import { useUserStore } from './stores/user'
import './style.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

// 后台按需加载 Element Plus：前台保持自研组件 + 设计 Token（AGENTS.md §4）
let adminUiInstalled = false
router.beforeEach(async (to) => {
  if (adminUiInstalled || !to.path.startsWith('/admin')) {
    return true
  }
  adminUiInstalled = true
  const [{ default: ElementPlus }] = await Promise.all([
    import('element-plus'),
    import('element-plus/dist/index.css'),
  ])
  app.use(ElementPlus)
  return true
})

// 启动时先恢复登录态，再安装 router（首次导航的守卫才能读到正确状态）
const userStore = useUserStore()
void bootstrap({
  app,
  router,
  hydrate: () => userStore.hydrate(),
  mount: () => app.mount('#app'),
})
