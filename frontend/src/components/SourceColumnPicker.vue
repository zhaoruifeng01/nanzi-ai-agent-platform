<template>
  <div ref="rootRef" class="relative min-w-0">
    <button
      type="button"
      class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-left outline-none disabled:bg-gray-50 disabled:cursor-not-allowed flex items-center justify-between gap-2"
      :class="accentRingClass"
      :disabled="disabled || loading"
      @click.stop="togglePicker"
    >
      <span v-if="loading" class="text-gray-400">加载中...</span>
      <span v-else-if="!hasValue" class="text-gray-400">请选择来源字段</span>
      <span v-else class="flex flex-col min-w-0 flex-1">
        <span class="truncate font-mono text-gray-900">{{ modelValue }}</span>
        <span class="truncate text-xs text-gray-400">{{ selectedSubtitle }}</span>
      </span>
      <svg
        class="h-4 w-4 shrink-0 text-gray-400 transition-transform"
        :class="{ 'rotate-180': open }"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <div
      v-if="open"
      class="absolute left-0 right-0 top-full z-[10001] mt-1 rounded-lg border border-gray-200 bg-white shadow-xl overflow-hidden"
    >
      <div class="flex items-center gap-2 border-b border-gray-100 px-3 py-2 bg-gray-50">
        <svg class="w-4 h-4 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          ref="searchInputRef"
          v-model="searchQuery"
          type="text"
          class="flex-1 min-w-0 bg-transparent border-none focus:ring-0 text-sm py-0.5 outline-none"
          placeholder="搜索字段名、中文备注或示例..."
          @click.stop
        />
      </div>
      <div class="max-h-56 overflow-y-auto">
        <button
          v-for="col in filteredColumns"
          :key="col.name"
          type="button"
          class="w-full px-3 py-2.5 text-left transition-colors"
          :class="modelValue === col.name ? activeItemClass : 'hover:bg-gray-50 text-gray-800'"
          @click.stop="selectColumn(col.name)"
        >
          <div class="text-sm font-mono truncate">{{ col.name }}</div>
          <div
            class="text-xs truncate mt-0.5"
            :class="modelValue === col.name ? activeSubClass : 'text-gray-500'"
          >
            {{ columnSubtitle(col) }}
          </div>
          <div
            v-if="col.sample"
            class="text-[11px] font-mono truncate mt-0.5"
            :class="modelValue === col.name ? activeSampleClass : 'text-gray-400'"
          >
            示例：{{ col.sample }}
          </div>
        </button>
        <div
          v-if="!loading && filteredColumns.length === 0"
          class="px-3 py-6 text-center text-sm text-gray-400"
        >
          {{ searchQuery.trim() ? '无匹配字段' : '暂无可用字段' }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'

export interface SourceColumn {
  name: string
  type?: string
  comment?: string
  sample?: string
}

const props = withDefaults(
  defineProps<{
    modelValue?: string | null
    columns: SourceColumn[]
    loading?: boolean
    disabled?: boolean
    accent?: 'indigo' | 'violet'
  }>(),
  {
    loading: false,
    disabled: false,
    accent: 'indigo',
  },
)

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const rootRef = ref<HTMLElement | null>(null)
const searchInputRef = ref<HTMLInputElement | null>(null)
const open = ref(false)
const searchQuery = ref('')

const accentRingClass = computed(() =>
  props.accent === 'violet' ? 'focus:ring-2 focus:ring-violet-500' : 'focus:ring-2 focus:ring-indigo-500',
)
const activeItemClass = computed(() =>
  props.accent === 'violet'
    ? 'bg-violet-50 text-violet-700'
    : 'bg-indigo-50 text-indigo-700',
)
const activeSubClass = computed(() =>
  props.accent === 'violet' ? 'text-violet-500/80' : 'text-indigo-500/80',
)
const activeSampleClass = computed(() =>
  props.accent === 'violet' ? 'text-violet-400' : 'text-indigo-400',
)

const columnSubtitle = (col: SourceColumn) => {
  const comment = String(col.comment || '').trim()
  if (comment) return comment
  return col.type || '—'
}

const selectedColumn = computed(() =>
  props.columns.find((col) => col.name === props.modelValue) || null,
)

const hasValue = computed(() => !!String(props.modelValue || '').trim())

const selectedSubtitle = computed(() => {
  if (!selectedColumn.value) return ''
  return columnSubtitle(selectedColumn.value)
})

const filteredColumns = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase()
  if (!keyword) return props.columns
  return props.columns.filter((col) => {
    const name = String(col.name || '').toLowerCase()
    const comment = String(col.comment || '').toLowerCase()
    const sample = String(col.sample || '').toLowerCase()
    const type = String(col.type || '').toLowerCase()
    return (
      name.includes(keyword) ||
      comment.includes(keyword) ||
      sample.includes(keyword) ||
      type.includes(keyword)
    )
  })
})

const closePicker = () => {
  open.value = false
  searchQuery.value = ''
}

const togglePicker = async () => {
  if (props.disabled || props.loading) return
  open.value = !open.value
  if (open.value) {
    await nextTick()
    searchInputRef.value?.focus()
  } else {
    searchQuery.value = ''
  }
}

const selectColumn = (name: string) => {
  emit('update:modelValue', name)
  closePicker()
}

const onOutsideClick = (event: MouseEvent) => {
  if (!rootRef.value?.contains(event.target as Node)) {
    closePicker()
  }
}

onMounted(() => {
  document.addEventListener('click', onOutsideClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onOutsideClick)
})
</script>
