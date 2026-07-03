<template>
  <div class="space-y-6">
    <!-- 时间范围 -->
    <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
      <div class="flex flex-wrap items-center gap-2">
        <button
          v-for="preset in rangePresets"
          :key="preset.key"
          type="button"
          class="px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors"
          :class="activePreset === preset.key
            ? 'bg-blue-600 text-white border-blue-600'
            : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300 hover:text-blue-600'"
          @click="applyPreset(preset.key)"
        >
          {{ preset.label }}
        </button>
      </div>
      <div class="flex flex-wrap items-end gap-2">
        <div>
          <label class="block text-[10px] text-gray-500 mb-1">开始日期</label>
          <input
            v-model="customStart"
            type="date"
            class="border border-gray-200 rounded-lg px-2.5 py-1.5 text-xs focus:ring-2 focus:ring-blue-500 outline-none"
            @change="applyCustomRange"
          />
        </div>
        <div>
          <label class="block text-[10px] text-gray-500 mb-1">结束日期</label>
          <input
            v-model="customEnd"
            type="date"
            class="border border-gray-200 rounded-lg px-2.5 py-1.5 text-xs focus:ring-2 focus:ring-blue-500 outline-none"
            @change="applyCustomRange"
          />
        </div>
        <button
          type="button"
          class="px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors disabled:opacity-50"
          :disabled="loading"
          @click="refreshAll"
        >
          刷新
        </button>
      </div>
    </div>

    <!-- 汇总卡片 -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div class="rounded-xl border border-gray-100 bg-gray-50/80 p-4">
        <p class="text-xs text-gray-500">Token 总量</p>
        <p class="text-xl font-bold text-gray-900 tabular-nums mt-1">{{ formatNumber(summary.total_tokens) }}</p>
        <p class="text-[10px] text-gray-400 mt-1">输入 {{ formatNumber(summary.prompt_tokens) }} · 输出 {{ formatNumber(summary.completion_tokens) }}</p>
      </div>
      <div class="rounded-xl border border-gray-100 bg-gray-50/80 p-4">
        <p class="text-xs text-gray-500">对话交互</p>
        <p class="text-xl font-bold text-gray-900 tabular-nums mt-1">{{ formatNumber(summary.calls) }}</p>
        <p class="text-[10px] text-gray-400 mt-1">会话发起次数</p>
      </div>
      <div class="rounded-xl border border-gray-100 bg-gray-50/80 p-4">
        <p class="text-xs text-gray-500">日均 Token</p>
        <p class="text-xl font-bold text-gray-900 tabular-nums mt-1">{{ formatNumber(summary.avg_daily_tokens) }}</p>
        <p class="text-[10px] text-gray-400 mt-1">按 {{ trendData.length }} 天平均</p>
      </div>
      <div class="rounded-xl border border-gray-100 bg-gray-50/80 p-4">
        <p class="text-xs text-gray-500">单次平均</p>
        <p class="text-xl font-bold text-gray-900 tabular-nums mt-1">{{ formatNumber(summary.avg_tokens) }}</p>
        <p class="text-[10px] text-gray-400 mt-1">Token / 次交互</p>
      </div>
    </div>

    <!-- 趋势图 -->
    <div class="rounded-xl border border-gray-100 p-4 sm:p-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-1">Token 消耗趋势</h3>
      <p class="text-xs text-gray-400 mb-4">每日输入/输出 Token 与累计总量</p>
      <div v-if="loading" class="h-72 flex items-center justify-center text-gray-400 text-sm">加载中...</div>
      <div v-else-if="trendData.length === 0" class="h-72 flex items-center justify-center text-gray-400 text-sm">暂无数据</div>
      <v-chart v-else class="h-72 w-full" :option="trendChartOption" autoresize />
    </div>

    <!-- 日明细 -->
    <div class="rounded-xl border border-gray-100 overflow-hidden">
      <div class="px-4 py-3 border-b border-gray-100 bg-gray-50/80">
        <h3 class="text-sm font-semibold text-gray-900">日明细</h3>
        <p class="text-xs text-gray-400 mt-0.5">按天汇总的 Token 消耗</p>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead class="bg-white text-gray-500 text-xs">
            <tr>
              <th class="px-4 py-2.5 text-left font-medium">日期</th>
              <th class="px-4 py-2.5 text-right font-medium">交互次数</th>
              <th class="px-4 py-2.5 text-right font-medium">输入 Token</th>
              <th class="px-4 py-2.5 text-right font-medium">输出 Token</th>
              <th class="px-4 py-2.5 text-right font-medium">合计 Token</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="5" class="px-4 py-8 text-center text-gray-400">加载中...</td>
            </tr>
            <tr v-else-if="dailyRows.length === 0">
              <td colspan="5" class="px-4 py-8 text-center text-gray-400">所选时间范围内暂无记录</td>
            </tr>
            <tr
              v-for="row in dailyRows"
              :key="row.date"
              class="border-t border-gray-50 hover:bg-gray-50/60"
            >
              <td class="px-4 py-2.5 text-gray-900 font-medium">{{ row.date }}</td>
              <td class="px-4 py-2.5 text-right tabular-nums text-gray-600">{{ formatNumber(row.calls) }}</td>
              <td class="px-4 py-2.5 text-right tabular-nums text-sky-700">{{ formatNumber(row.prompt_tokens) }}</td>
              <td class="px-4 py-2.5 text-right tabular-nums text-rose-700">{{ formatNumber(row.completion_tokens) }}</td>
              <td class="px-4 py-2.5 text-right tabular-nums font-semibold text-gray-900">{{ formatNumber(row.total_tokens) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 交互明细 -->
    <div class="rounded-xl border border-gray-100 overflow-hidden">
      <div class="px-4 py-3 border-b border-gray-100 bg-gray-50/80 flex items-center justify-between gap-3">
        <div>
          <h3 class="text-sm font-semibold text-gray-900">交互明细</h3>
          <p class="text-xs text-gray-400 mt-0.5">每次对话/调用的 Token 消耗记录</p>
        </div>
        <span class="text-xs text-gray-400">共 {{ recordTotal }} 条</span>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead class="bg-white text-gray-500 text-xs">
            <tr>
              <th class="px-4 py-2.5 text-left font-medium">时间</th>
              <th class="px-4 py-2.5 text-left font-medium">智能体</th>
              <th class="px-4 py-2.5 text-left font-medium">模型</th>
              <th class="px-4 py-2.5 text-right font-medium">Token</th>
              <th class="px-4 py-2.5 text-center font-medium">状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="5" class="px-4 py-8 text-center text-gray-400">加载中...</td>
            </tr>
            <tr v-else-if="records.length === 0">
              <td colspan="5" class="px-4 py-8 text-center text-gray-400">暂无交互记录</td>
            </tr>
            <tr
              v-for="item in records"
              :key="item.id"
              class="border-t border-gray-50 hover:bg-gray-50/60"
            >
              <td class="px-4 py-2.5 text-gray-700 whitespace-nowrap">{{ formatDateTime(item.created_at) }}</td>
              <td class="px-4 py-2.5 text-gray-800">{{ item.agent_name }}</td>
              <td class="px-4 py-2.5 text-gray-500 font-mono text-xs">{{ item.model_id || '—' }}</td>
              <td class="px-4 py-2.5 text-right tabular-nums font-medium text-gray-900">{{ formatNumber(item.total_tokens) }}</td>
              <td class="px-4 py-2.5 text-center">
                <span
                  class="text-[10px] px-2 py-0.5 rounded-full font-medium"
                  :class="item.status === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'"
                >
                  {{ item.status === 'success' ? '成功' : item.status }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="recordTotal > recordPageSize" class="px-4 py-3 border-t border-gray-100 flex items-center justify-between">
        <button
          type="button"
          class="px-3 py-1.5 text-xs rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40"
          :disabled="recordPage <= 1 || loading"
          @click="changeRecordPage(recordPage - 1)"
        >
          上一页
        </button>
        <span class="text-xs text-gray-500">第 {{ recordPage }} / {{ recordTotalPages }} 页</span>
        <button
          type="button"
          class="px-3 py-1.5 text-xs rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40"
          :disabled="recordPage >= recordTotalPages || loading"
          @click="changeRecordPage(recordPage + 1)"
        >
          下一页
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import axios from '../../utils/axios'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components'

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
])

interface TrendRow {
  date: string
  calls: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

interface RecordRow {
  id: number
  created_at: string
  agent_name: string
  model_id: string
  total_tokens: number
  status: string
}

const rangePresets = [
  { key: '7d', label: '近 7 天', days: 7 },
  { key: '30d', label: '近 30 天', days: 30 },
  { key: '90d', label: '近 90 天', days: 90 },
] as const

type PresetKey = typeof rangePresets[number]['key'] | 'custom'

const loading = ref(false)
const activePreset = ref<PresetKey>('7d')
const queryDays = ref(7)
const customStart = ref('')
const customEnd = ref('')
const trendData = ref<TrendRow[]>([])
const records = ref<RecordRow[]>([])
const recordPage = ref(1)
const recordPageSize = 20
const recordTotal = ref(0)

const formatDateInput = (date: Date) => {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const initDefaultCustomRange = () => {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - 6)
  customEnd.value = formatDateInput(end)
  customStart.value = formatDateInput(start)
}

const queryParams = computed(() => {
  if (activePreset.value === 'custom') {
    return { start_date: customStart.value, end_date: customEnd.value }
  }
  return { days: queryDays.value }
})

const summary = computed(() => {
  let prompt_tokens = 0
  let completion_tokens = 0
  let calls = 0
  for (const row of trendData.value) {
    prompt_tokens += row.prompt_tokens || 0
    completion_tokens += row.completion_tokens || 0
    calls += row.calls || 0
  }
  const breakdown = prompt_tokens + completion_tokens
  const raw_total = trendData.value.reduce((sum, row) => sum + (row.total_tokens || 0), 0)
  const total_tokens = breakdown > 0 ? breakdown : raw_total
  const dayCount = Math.max(trendData.value.length, 1)
  return {
    prompt_tokens,
    completion_tokens,
    total_tokens,
    calls,
    avg_daily_tokens: Math.round(total_tokens / dayCount),
    avg_tokens: calls > 0 ? Math.round(total_tokens / calls) : 0,
  }
})

const dailyRows = computed(() =>
  [...trendData.value].reverse().filter((row) =>
    row.calls > 0 || row.prompt_tokens > 0 || row.completion_tokens > 0 || row.total_tokens > 0,
  ),
)

const recordTotalPages = computed(() =>
  Math.max(1, Math.ceil(recordTotal.value / recordPageSize)),
)

const trendChartOption = computed(() => {
  if (!trendData.value.length) return {}
  const dates = trendData.value.map((item) => item.date.slice(5))
  const promptTokens = trendData.value.map((item) => item.prompt_tokens || 0)
  const completionTokens = trendData.value.map((item) => item.completion_tokens || 0)
  let cumulative = 0
  const cumulativeTokens = trendData.value.map((item) => {
    const daily = (item.prompt_tokens || 0) + (item.completion_tokens || 0) || item.total_tokens || 0
    cumulative += daily
    return cumulative
  })

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const items = Array.isArray(params) ? params : [params]
        const date = items[0]?.axisValue || ''
        const lines = items.map((item: any) => {
          const val = formatNumber(Number(item.value) || 0)
          return `${item.marker}${item.seriesName}: ${val}`
        })
        return [date, ...lines].join('<br/>')
      },
    },
    legend: { data: ['输入 Token', '输出 Token', '累计 Token'], bottom: 0 },
    grid: { left: 12, right: 16, bottom: 48, top: 24, containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#d1d5db' } },
      axisTick: { show: false },
    },
    yAxis: [
      {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          formatter: (value: number) => formatAxisValue(value),
        },
        splitLine: { lineStyle: { type: 'dashed', color: '#f3f4f6' } },
      },
      {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          formatter: (value: number) => formatAxisValue(value),
        },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '输入 Token',
        type: 'bar',
        stack: 'daily',
        data: promptTokens,
        itemStyle: { color: '#0ea5e9' },
        barMaxWidth: 24,
      },
      {
        name: '输出 Token',
        type: 'bar',
        stack: 'daily',
        data: completionTokens,
        itemStyle: { color: '#f43f5e' },
        barMaxWidth: 24,
      },
      {
        name: '累计 Token',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        showSymbol: false,
        data: cumulativeTokens,
        itemStyle: { color: '#6366f1' },
        lineStyle: { width: 2 },
      },
    ],
  }
})

const formatNumber = (num: number) => {
  if (!num) return '0'
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

const formatAxisValue = (value: number) => {
  const num = Number(value) || 0
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(num >= 10_000_000 ? 0 : 1)}M`
  if (num >= 10_000) return `${(num / 10_000).toFixed(num >= 100_000 ? 0 : 1)}万`
  if (num >= 1_000) return `${(num / 1_000).toFixed(0)}k`
  return String(num)
}

const formatDateTime = (value: string) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const applyPreset = (key: typeof rangePresets[number]['key']) => {
  activePreset.value = key
  const preset = rangePresets.find((item) => item.key === key)
  queryDays.value = preset?.days || 7
  initDefaultCustomRange()
  recordPage.value = 1
  refreshAll()
}

const applyCustomRange = () => {
  if (!customStart.value || !customEnd.value) return
  activePreset.value = 'custom'
  recordPage.value = 1
  refreshAll()
}

const changeRecordPage = (page: number) => {
  recordPage.value = page
  loadRecords()
}

const loadTrends = async () => {
  const res = await axios.get('/api/portal/dashboard/token-stats/trends', {
    params: queryParams.value,
  })
  trendData.value = res.data || []
}

const loadRecords = async () => {
  const res = await axios.get('/api/portal/dashboard/token-stats/records', {
    params: {
      ...queryParams.value,
      page: recordPage.value,
      size: recordPageSize,
    },
  })
  records.value = res.data?.items || []
  recordTotal.value = res.data?.total || 0
}

const refreshAll = async () => {
  loading.value = true
  try {
    await Promise.all([loadTrends(), loadRecords()])
  } catch (error) {
    console.error('Failed to load personal token usage', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  initDefaultCustomRange()
  refreshAll()
})
</script>
