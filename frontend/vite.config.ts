import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  server: {
    port: 5173,
    // —— 关键：把 /api 和 /uploads 代理到 FastAPI ——
    // 开发期前后端同源，CORS 配置仅为兜底
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/uploads': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },

  build: {
    rollupOptions: {
      output: {
        // 把稳定依赖拆到独立 vendor chunk，避免业务代码变更导致整包缓存失效
        // Vite 8（Rolldown）的 manualChunks 只接受函数形式
        manualChunks(id: string) {
          if (!id.includes('node_modules')) return
          if (id.includes('/qrcode/')) return 'vendor-qrcode'
          // Element Plus 仅后台使用，单独成块，避免混入前台 vendor
          if (id.includes('/element-plus/') || id.includes('/@element-plus/')) {
            return 'vendor-element-plus'
          }
          if (
            id.includes('/vue/') ||
            id.includes('/@vue/') ||
            id.includes('/vue-router/') ||
            id.includes('/pinia/')
          ) {
            return 'vendor-vue'
          }
        },
      },
    },
  },
})
