<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { generateShare, revokeShare } from '@/api/shares'
import { buildShareUrl } from '@/utils/favorite'
import { downloadSharePoster } from '@/utils/poster'
import type { ListShareBrief } from '@/types'
import { useToastStore } from '@/stores/toast'

const visible = defineModel<boolean>({ required: true })

const props = withDefaults(
  defineProps<{
    share: ListShareBrief | null
    listId?: number | null
    title?: string
    teaNames?: string[]
    teaCount?: number
    createdAt?: string
  }>(),
  {
    listId: null,
    title: '我的茶单',
    teaNames: () => [],
    teaCount: 0,
    createdAt: '',
  },
)

const emit = defineEmits<{ 'update:share': [share: ListShareBrief | null] }>()

const toast = useToastStore()
const token = ref<string | null>(props.share?.token ?? null)
const generating = ref(false)
const revoking = ref(false)
const confirmingRevoke = ref(false)
const revokedToken = ref<string | null>(null)
const posterLoading = ref(false)

const link = computed(() => (token.value ? buildShareUrl(window.location.origin, token.value) : ''))

watch(
  () => props.share,
  (value) => {
    token.value = value?.token ?? null
  },
)

watch(visible, (open) => {
  if (open) reset()
})

function reset() {
  confirmingRevoke.value = false
  revokedToken.value = null
}

function close() {
  if (generating.value || revoking.value) return
  visible.value = false
}

async function generate() {
  if (generating.value) return
  generating.value = true
  try {
    const res = await generateShare(props.listId ?? undefined)
    token.value = res.data.token
    revokedToken.value = null
    confirmingRevoke.value = false
    emit('update:share', {
      token: res.data.token,
      url: res.data.url,
      created_at: res.data.created_at,
    })
    toast.success(res.data.is_new ? '分享链接已生成' : '已复用当前有效的分享链接')
  } catch {
    // 统一错误提示由请求拦截器处理
  } finally {
    generating.value = false
  }
}

async function copyLink() {
  if (!link.value) return
  try {
    await navigator.clipboard.writeText(link.value)
    toast.success('分享链接已复制')
  } catch {
    toast.error('复制失败，请手动选择链接复制')
  }
}

function selectLink(event: Event) {
  const target = event.target as HTMLInputElement | null
  target?.select()
}

/** S8：纯前端 canvas 生成分享海报并下载 PNG */
async function downloadPoster() {
  if (!token.value || posterLoading.value) return
  posterLoading.value = true
  try {
    await downloadSharePoster({
      title: props.title,
      shareUrl: link.value,
      teaNames: props.teaNames,
      teaCount: props.teaCount,
      createdAt: props.createdAt,
    })
    toast.success('海报已生成，请查看下载')
  } catch {
    toast.error('海报生成失败，请稍后重试')
  } finally {
    posterLoading.value = false
  }
}

async function onRevoke() {
  if (!token.value || revoking.value) return
  if (!confirmingRevoke.value) {
    confirmingRevoke.value = true
    return
  }
  revoking.value = true
  try {
    const oldToken = token.value
    await revokeShare(oldToken)
    revokedToken.value = oldToken
    token.value = null
    confirmingRevoke.value = false
    emit('update:share', null)
    toast.success('分享已撤销，旧链接永久失效')
  } catch {
    // 统一错误提示由请求拦截器处理
  } finally {
    revoking.value = false
  }
}
</script>

<template>
  <div v-if="visible" class="modal" role="dialog" aria-modal="true" @click.self="close">
    <div class="modal__panel">
      <header class="modal__header">
        <div>
          <h2 class="modal__title">分享我的清单</h2>
          <p class="modal__subtitle">任何人通过链接可只读查看，不会看到你的私密笔记</p>
        </div>
        <button type="button" class="modal__close" aria-label="关闭" @click="close">×</button>
      </header>

      <div v-if="revokedToken" class="share-revoked">
        <p class="share-revoked__title">链接已撤销</p>
        <p class="share-revoked__desc">
          旧的分享链接已永久失效，无法恢复。如需继续分享，请生成新的链接。
        </p>
      </div>

      <template v-if="token">
        <label class="share-label" for="share-link">分享链接</label>
        <div class="share-link">
          <input
            id="share-link"
            class="share-link__input"
            :value="link"
            readonly
            @focus="selectLink"
          />
          <button type="button" class="btn btn--secondary" @click="copyLink">复制链接</button>
        </div>
        <p class="share-tip">已有有效链接时会复用，不会重复生成；撤销后旧链接不可恢复。</p>

        <button
          type="button"
          class="btn btn--secondary poster-btn"
          :disabled="posterLoading"
          @click="downloadPoster"
        >
          {{ posterLoading ? '海报生成中…' : '⬇️ 下载分享海报' }}
        </button>
      </template>

      <div v-else class="share-empty">
        <p class="share-empty__desc">
          生成一条只读分享链接，把这份茶单发给朋友。链接大小写敏感，请勿修改。
        </p>
        <button type="button" class="btn btn--primary" :disabled="generating" @click="generate">
          {{ generating ? '生成中…' : '生成分享链接' }}
        </button>
      </div>

      <footer class="modal__footer">
        <button
          v-if="token"
          type="button"
          class="btn btn--danger"
          :disabled="revoking"
          @click="onRevoke"
        >
          {{ confirmingRevoke ? '再次点击确认撤销' : '撤销分享' }}
        </button>
        <button
          v-if="confirmingRevoke"
          type="button"
          class="btn btn--ghost"
          @click="confirmingRevoke = false"
        >
          取消
        </button>
        <button type="button" class="btn btn--ghost" @click="close">关闭</button>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.modal {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(44, 36, 24, 0.45);
}

.modal__panel {
  width: min(560px, 100%);
  background: var(--color-bg-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-modal);
  padding: 24px;
}

.modal__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.modal__title {
  font-family: var(--font-display);
  font-size: var(--text-h2);
  color: var(--color-text-primary);
  margin: 0 0 4px;
}

.modal__subtitle {
  font-size: var(--text-small);
  color: var(--color-text-muted);
  margin: 0;
}

.modal__close {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--color-text-muted);
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.modal__close:hover {
  background: var(--color-bg-muted);
}

.share-label {
  display: block;
  font-size: var(--text-small);
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.share-link {
  display: flex;
  gap: 8px;
}

.share-link__input {
  flex: 1;
  min-width: 0;
  height: 40px;
  padding: 0 12px;
  border: 1px solid var(--color-border-dark);
  border-radius: var(--radius-sm);
  background: var(--color-bg-page);
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
}

.share-tip {
  margin: 10px 0 0;
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

.poster-btn {
  margin-top: 14px;
  width: 100%;
}

.share-empty {
  padding: 8px 0 4px;
}

.share-empty__desc {
  margin: 0 0 16px;
  font-size: var(--text-small);
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.share-revoked {
  background: var(--color-bg-muted);
  border-left: 3px solid var(--color-warning);
  border-radius: var(--radius-sm);
  padding: 12px 16px;
  margin-bottom: 16px;
}

.share-revoked__title {
  margin: 0 0 4px;
  font-size: var(--text-small);
  font-weight: 600;
  color: var(--color-warning);
}

.share-revoked__desc {
  margin: 0;
  font-size: var(--text-caption);
  color: var(--color-text-secondary);
}

.modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 40px;
  padding: 0 20px;
  border-radius: var(--radius-full);
  font-size: var(--text-small);
  font-weight: 500;
  cursor: pointer;
  transition:
    background 0.2s,
    border-color 0.2s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn--primary {
  border: 1px solid var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.btn--primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn--secondary {
  border: 1px solid var(--color-border-dark);
  background: transparent;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.btn--secondary:hover:not(:disabled) {
  background: var(--color-bg-muted);
}

.btn--danger {
  border: 1px solid var(--color-error);
  background: transparent;
  color: var(--color-error);
}

.btn--danger:hover:not(:disabled) {
  background: var(--color-error);
  color: var(--color-text-inverse);
}

.btn--ghost {
  border: none;
  background: transparent;
  color: var(--color-text-muted);
}

.btn--ghost:hover:not(:disabled) {
  background: var(--color-bg-muted);
}
</style>
