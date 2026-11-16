<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppToast from '@/components/AppToast.vue'
import PaperTexture from '@/components/effects/PaperTexture.vue'

const route = useRoute()
/** 纸纹只作用于前台，管理员后台保持纯净背景 */
const showPaperTexture = computed(() => !route.path.startsWith('/admin'))
</script>

<template>
  <div id="app-root">
    <PaperTexture v-if="showPaperTexture" />
    <RouterView />
    <AppToast />
  </div>
</template>

<style scoped>
#app-root {
  min-height: 100svh;
}
</style>
