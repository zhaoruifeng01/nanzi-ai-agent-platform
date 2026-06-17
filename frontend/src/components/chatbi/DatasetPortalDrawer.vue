<template>
  <div v-show="modelValue" class="fixed inset-0 z-50 overflow-hidden">
    <transition
      enter-active-class="ease-out duration-300"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="ease-in duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-show="modelValue"
        class="absolute inset-0 bg-gray-500/30 backdrop-blur-xs transition-opacity"
        @click="closeDrawer"
      />
    </transition>

    <div class="absolute inset-y-0 right-0 pl-0 sm:pl-10 max-w-full flex">
      <transition
        enter-active-class="transform transition ease-in-out duration-300"
        enter-from-class="translate-x-full"
        enter-to-class="translate-x-0"
        leave-active-class="transform transition ease-in-out duration-300"
        leave-from-class="translate-x-0"
        leave-to-class="translate-x-full"
      >
        <div
          v-show="modelValue"
          class="w-screen max-w-[min(100vw,28rem)] bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800 shadow-2xl flex flex-col h-full relative z-10 pb-[env(safe-area-inset-bottom,0px)]"
        >
          <div class="px-4 py-3 sm:py-4 border-b border-gray-150 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/20 flex items-center justify-between gap-2 pt-[max(0.75rem,env(safe-area-inset-top,0px))]">
            <span class="text-sm font-bold text-gray-900 dark:text-gray-100 flex items-center gap-1.5 select-none min-w-0">
              <svg class="w-4 h-4 text-blue-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2v-4zM14 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2v-4z" />
              </svg>
              <span class="truncate">数据门户导航</span>
            </span>
            <div class="flex items-center gap-2 flex-shrink-0">
              <label
                class="hidden sm:flex items-center gap-1.5 text-[10px] text-gray-500 dark:text-gray-400 cursor-pointer select-none whitespace-nowrap"
                title="开启后点击问题不会关闭抽屉，可连续提问（仅桌面端生效）"
              >
                <input
                  v-model="keepOpenOnQuestion"
                  type="checkbox"
                  class="rounded border-gray-300 text-primary focus:ring-primary/30"
                />
                提问后保持
              </label>
              <button
                type="button"
                class="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 p-1 rounded-md hover:bg-gray-150 dark:hover:bg-gray-800 transition-colors"
                title="关闭 (Esc)"
                @click="closeDrawer"
              >
                <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
          <div class="flex-1 overflow-y-auto p-3 sm:p-4 bg-white dark:bg-gray-900/60">
            <DatasetCapabilityMenu
              :payload="payload || { groups: [] }"
              :initial-loading="initialLoading"
              :background-refreshing="backgroundRefreshing"
              @quick-question="(query) => emit('quick-question', query)"
              @record-question-click="(p) => emit('record-question-click', p)"
              @clear-question-click="(p) => emit('clear-question-click', p)"
              @refresh="emit('refresh')"
            />
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import DatasetCapabilityMenu from "@/components/chatbi/DatasetCapabilityMenu.vue";

const modelValue = defineModel<boolean>({ default: false });
const keepOpenOnQuestion = defineModel<boolean>("keepOpenOnQuestion", { default: false });

defineProps<{
  payload: Record<string, unknown> | null;
  initialLoading?: boolean;
  backgroundRefreshing?: boolean;
}>();

const emit = defineEmits<{
  (event: "quick-question", query: string): void;
  (event: "record-question-click", payload: { query: string; label?: string; group_id?: string }): void;
  (event: "clear-question-click", payload: { query: string }): void;
  (event: "refresh"): void;
}>();

const closeDrawer = () => {
  modelValue.value = false;
};
</script>
