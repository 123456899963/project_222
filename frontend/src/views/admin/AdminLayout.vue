<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const router = useRouter()

const username = computed(() => userStore.user?.username ?? '管理员')

async function handleLogout() {
  await userStore.logout()
  router.push({ name: 'admin-login' })
}
</script>

<template>
  <div class="admin-layout">
    <aside class="admin-sidebar">
      <div class="admin-brand">
        <strong class="font-display">茶 · 图鉴</strong>
        <span class="text-caption text-muted">管理后台</span>
      </div>

      <el-menu :default-active="$route.path" router class="admin-menu">
        <el-menu-item index="/admin">数据概览</el-menu-item>
        <el-menu-item index="/admin/teas">茶品管理</el-menu-item>
        <el-menu-item index="/admin/teas/new">新增茶品</el-menu-item>
        <el-menu-item index="/admin/contributions">投稿审核</el-menu-item>
        <el-menu-item index="/admin/operation-logs">操作日志</el-menu-item>
        <el-divider class="admin-menu__divider" />
        <el-menu-item index="/admin/contents">内容管理</el-menu-item>
      </el-menu>

      <div class="admin-sidebar-footer">
        <router-link class="text-small" to="/">← 返回前台</router-link>
      </div>
    </aside>

    <main class="admin-main">
      <header class="admin-topbar">
        <span class="text-small text-secondary">
          当前账号：<strong class="text-primary">{{ username }}</strong>
          <span class="role-tag">管理员</span>
        </span>
        <el-button size="small" @click="handleLogout">退出登录</el-button>
      </header>
      <div class="admin-content">
        <RouterView />
      </div>
    </main>
  </div>
</template>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100svh;
}
.admin-sidebar {
  width: 240px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--color-border);
  background: var(--color-bg-surface);
}
.admin-brand {
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.admin-brand strong {
  font-size: var(--text-h2);
  color: var(--color-primary-dark);
}
.admin-menu {
  border-right: none;
}
.admin-sidebar-footer {
  margin-top: auto;
  padding: 20px;
  border-top: 1px solid var(--color-border-light);
}
.admin-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-page);
}
.admin-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 32px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-surface);
}
.role-tag {
  display: inline-block;
  margin-left: 8px;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  font-size: var(--text-caption);
  color: var(--color-primary);
  background: var(--color-bg-muted);
}
.admin-content {
  padding: 24px 32px 40px;
}
</style>
