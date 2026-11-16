<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useToastStore } from '@/stores/toast'

const router = useRouter()
const userStore = useUserStore()
const toast = useToastStore()

const keyword = ref('')

/** 「茶文化」下拉：hover 之外的触屏/键盘开启通道（点击切换，Esc/点击外部/路由跳转关闭） */
const dropdownOpen = ref(false)
const navGroupRef = ref<HTMLElement | null>(null)

function toggleDropdown() {
  dropdownOpen.value = !dropdownOpen.value
}

function closeDropdown() {
  dropdownOpen.value = false
}

function onDocumentClick(event: MouseEvent) {
  if (dropdownOpen.value && !navGroupRef.value?.contains(event.target as Node)) {
    closeDropdown()
  }
}

function onDocumentKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && dropdownOpen.value) {
    closeDropdown()
    navGroupRef.value?.querySelector('button')?.focus()
  }
}

/** 首页首屏：页头以透明态浮在 Hero 背景上，滚过 Hero 后转实底 */
const overHero = ref(false)
let heroEl: HTMLElement | null = null

function updateHeaderTone() {
  heroEl = router.currentRoute.value.name === 'home' ? document.querySelector('.hero') : null
  overHero.value = !!heroEl && window.scrollY < heroEl.offsetHeight - 80
}

onMounted(() => {
  document.addEventListener('click', onDocumentClick)
  document.addEventListener('keydown', onDocumentKeydown)
  window.addEventListener('scroll', updateHeaderTone, { passive: true })
  void nextTick(updateHeaderTone)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
  document.removeEventListener('keydown', onDocumentKeydown)
  window.removeEventListener('scroll', updateHeaderTone)
})

watch(
  () => router.currentRoute.value.fullPath,
  () => {
    closeDropdown()
    void nextTick(updateHeaderTone)
  },
)

/** 无头像时的首字母占位（取用户名首字符） */
const initial = computed(() => (userStore.user?.username ?? '').slice(0, 1).toUpperCase())

function onSearch() {
  const q = keyword.value.trim()
  router.push({ name: 'tea-list', query: q ? { q } : {} })
}

async function onLogout() {
  await userStore.logout()
  toast.info('已退出登录')
  if (router.currentRoute.value.meta.requiresAuth) {
    router.push('/')
  }
}
</script>

<template>
  <header class="app-header" :class="{ 'app-header--over-hero': overHero }">
    <div class="app-header__inner">
      <RouterLink to="/" class="app-header__brand" aria-label="返回首页">
        <svg class="app-header__logo" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path
            d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19.2 2.5c1 1.66.6 6-2 9-2 2.4-6.2 3-6.2 3zM2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"
          />
        </svg>
        <span class="app-header__brand-text">茶·图鉴</span>
      </RouterLink>

      <nav class="app-header__links" aria-label="主导航">
        <RouterLink to="/" class="app-header__link">首页</RouterLink>
        <RouterLink to="/teas" class="app-header__link">茶品列表</RouterLink>
        <div ref="navGroupRef" class="app-header__nav-group">
          <button
            type="button"
            class="app-header__link app-header__link--trigger"
            aria-haspopup="menu"
            :aria-expanded="dropdownOpen"
            @click="toggleDropdown"
          >
            茶文化 ▾
          </button>
          <div
            class="app-header__dropdown"
            :class="{ 'app-header__dropdown--open': dropdownOpen }"
            role="menu"
          >
            <RouterLink to="/contents/teaware" class="app-header__dropdown-item" role="menuitem"
              >🫖 茶具茶器</RouterLink
            >
            <RouterLink to="/contents/origin" class="app-header__dropdown-item" role="menuitem"
              >🗺️ 茶叶产地</RouterLink
            >
            <RouterLink to="/contents/culture" class="app-header__dropdown-item" role="menuitem"
              >📜 茶叶文化</RouterLink
            >
            <RouterLink to="/contents/brand" class="app-header__dropdown-item" role="menuitem"
              >🏷️ 茶叶品牌</RouterLink
            >
            <RouterLink to="/contents/knowledge" class="app-header__dropdown-item" role="menuitem"
              >📚 茶叶知识</RouterLink
            >
          </div>
        </div>
      </nav>

      <div class="app-header__right">
        <form class="app-header__search" role="search" @submit.prevent="onSearch">
          <input
            v-model="keyword"
            class="app-header__search-input"
            type="search"
            placeholder="搜索茶名或产地"
            aria-label="搜索茶品"
          />
          <button class="app-header__search-btn" type="submit" aria-label="搜索">
            <svg
              viewBox="0 0 24 24"
              width="16"
              height="16"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              aria-hidden="true"
            >
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" />
            </svg>
          </button>
        </form>

        <template v-if="userStore.isLoggedIn">
          <RouterLink to="/profile" class="app-header__profile" :title="userStore.user?.username">
            <img
              v-if="userStore.user?.avatar_url"
              class="app-header__avatar"
              :src="userStore.user.avatar_url"
              :alt="`${userStore.user.username} 的头像`"
            />
            <span
              v-else
              class="app-header__avatar app-header__avatar--placeholder"
              aria-hidden="true"
            >
              {{ initial }}
            </span>
            <span class="app-header__user">{{ userStore.user?.username }}</span>
          </RouterLink>
          <button class="app-header__logout" type="button" @click="onLogout">退出</button>
        </template>
        <RouterLink v-else to="/login" class="app-header__login">登录</RouterLink>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 50;
  height: 64px;
  background: var(--color-bg-surface);
  border-bottom: 1px solid var(--color-border);
  transition:
    background-color var(--motion-duration-base) var(--motion-ease),
    border-color var(--motion-duration-base) var(--motion-ease);
}

/* 首页首屏透明态：页头浮在 Hero 背景上，文字与控件转白 */
.app-header--over-hero {
  background: transparent;
  border-bottom-color: transparent;
}

.app-header--over-hero .app-header__logo,
.app-header--over-hero .app-header__brand-text,
.app-header--over-hero .app-header__login {
  color: var(--color-text-inverse);
}

.app-header--over-hero .app-header__link,
.app-header--over-hero .app-header__user,
.app-header--over-hero .app-header__logout {
  color: rgba(255, 255, 255, 0.88);
}

.app-header--over-hero .app-header__link:hover,
.app-header--over-hero .app-header__link.router-link-active {
  color: var(--color-text-inverse);
}

.app-header--over-hero .app-header__link.router-link-active::after {
  background: var(--color-text-inverse);
}

.app-header--over-hero .app-header__search {
  border-color: rgba(255, 255, 255, 0.42);
  background: rgba(255, 255, 255, 0.14);
}

.app-header--over-hero .app-header__search-input,
.app-header--over-hero .app-header__search-btn {
  color: var(--color-text-inverse);
}

.app-header--over-hero .app-header__search-input::placeholder {
  color: rgba(255, 255, 255, 0.66);
}

.app-header--over-hero .app-header__avatar--placeholder {
  background: rgba(255, 255, 255, 0.18);
  color: var(--color-text-inverse);
  border-color: rgba(255, 255, 255, 0.35);
}

.app-header__inner {
  max-width: 1200px;
  height: 100%;
  margin: 0 auto;
  padding: 0 32px;
  display: flex;
  align-items: center;
  gap: 32px;
}

.app-header__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.app-header__logo {
  width: 32px;
  height: 32px;
  color: var(--color-primary);
}

.app-header__brand-text {
  font-family: var(--font-display);
  font-size: var(--text-h3);
  font-weight: 600;
  color: var(--color-primary-dark);
}

.app-header__links {
  display: flex;
  align-items: center;
  gap: 24px;
}

.app-header__link {
  position: relative;
  font-size: var(--text-small);
  font-weight: 500;
  color: var(--color-text-secondary);
  padding: 4px 0;
}

.app-header__link:hover,
.app-header__link.router-link-active {
  color: var(--color-primary);
}

.app-header__link.router-link-active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 2px;
  border-radius: 1px;
  background: var(--color-primary);
}

/* —— 茶文化下拉（批次五 R1–R5）—— */
.app-header__nav-group {
  position: relative;
}
.app-header__link--trigger {
  cursor: pointer;
  background: none;
  border: none;
  font-family: inherit;
}
.app-header__dropdown {
  position: absolute;
  top: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  min-width: 180px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: 0 8px 24px rgba(139, 115, 85, 0.12);
  padding: 8px;
  opacity: 0;
  visibility: hidden;
  transform: translateX(-50%) translateY(-4px);
  transition:
    opacity 0.15s,
    visibility 0.15s,
    transform 0.15s;
  z-index: 60;
}
/* hover 仅在支持 hover 的指针设备生效，触屏/键盘依赖点击开启（is-open） */
@media (hover: hover) {
  .app-header__nav-group:hover .app-header__dropdown,
  .app-header__link--trigger:hover + .app-header__dropdown {
    opacity: 1;
    visibility: visible;
    transform: translateX(-50%) translateY(0);
  }
}
.app-header__dropdown--open {
  opacity: 1;
  visibility: visible;
  transform: translateX(-50%) translateY(0);
}
.app-header__dropdown-item {
  display: block;
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  font-size: var(--text-small);
  color: var(--color-text-secondary);
  text-decoration: none;
  line-height: 1.5;
  transition:
    background 0.15s,
    color 0.15s;
}
.app-header__dropdown-item:hover {
  background: var(--color-bg-muted);
  color: var(--color-primary);
}

.app-header__right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.app-header__search {
  display: flex;
  align-items: center;
  height: 36px;
  border: 1px solid var(--color-border-dark);
  border-radius: var(--radius-full);
  background: var(--color-bg-surface);
  overflow: hidden;
}

.app-header__search-input {
  width: 160px;
  height: 100%;
  padding: 0 12px;
  border: none;
  outline: none;
  background: transparent;
  font-size: var(--text-small);
  color: var(--color-text-primary);
}

.app-header__search-btn {
  width: 36px;
  height: 100%;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.app-header__search-btn:hover {
  color: var(--color-primary);
}

.app-header__profile {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px 4px 4px;
  border-radius: var(--radius-full);
  transition: background 0.15s;
}

.app-header__profile:hover {
  background: var(--color-bg-muted);
}

.app-header__avatar {
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  border-radius: var(--radius-full);
  object-fit: cover;
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border);
}

.app-header__avatar--placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-small);
  font-weight: 600;
  color: var(--color-primary-dark);
}

.app-header__user {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--text-small);
  color: var(--color-text-secondary);
}

.app-header__logout {
  border: none;
  background: transparent;
  font-size: var(--text-small);
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 4px;
}

.app-header__logout:hover {
  color: var(--color-primary);
}

.app-header__login {
  font-size: var(--text-small);
  color: var(--color-primary);
  white-space: nowrap;
}

@media (max-width: 767px) {
  .app-header {
    height: 56px;
  }

  .app-header__inner {
    padding: 0 16px;
    gap: 16px;
  }

  .app-header__links,
  .app-header__search {
    display: none;
  }

  .app-header__brand-text {
    font-size: var(--text-body);
  }
}
</style>
