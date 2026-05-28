<template>
  <div class="space-y-6 pb-12">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-xl sm:text-2xl font-bold text-gray-900 tracking-tight">Token 统计分析</h1>
        <p class="text-sm text-gray-500 mt-1">系统大模型算力消耗量、交互频次及智能体分布审计</p>
      </div>
      <div class="flex items-center gap-3">
        <select
          v-model="period"
          @change="onPeriodChange"
          class="rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-bold text-gray-700 shadow-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary cursor-pointer active:scale-95 transition-all"
        >
          <option value="today">今日</option>
          <option value="week">最近 7 天</option>
          <option value="month">最近 30 天</option>
        </select>
        <button
          @click="refreshAll"
          :disabled="loading"
          class="inline-flex items-center justify-center p-2 sm:px-4 sm:py-2 border border-gray-200 rounded-xl shadow-sm text-sm font-bold text-gray-700 bg-white hover:bg-gray-50 active:scale-95 transition-all disabled:opacity-50"
        >
          <svg
            class="h-5 w-5 text-primary"
            :class="{ 'animate-spin': loading, 'sm:mr-2': true }"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2.5"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          <span class="hidden sm:inline">刷新</span>
        </button>
      </div>
    </div>

    <!-- Statistics Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm flex items-center justify-between">
        <div class="space-y-1">
          <span class="text-xs text-gray-500 font-bold uppercase tracking-wider">算力 Token 总量</span>
          <h3 class="text-2xl sm:text-3xl font-black text-gray-900">{{ formatCompactNumber(summaryData.total_tokens) }}</h3>
          <p class="text-xs text-gray-400">大模型输入输出累计值</p>
        </div>
        <div class="p-3.5 bg-blue-50/80 rounded-2xl text-blue-600">
          <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
      </div>

      <div class="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm flex items-center justify-between">
        <div class="space-y-1">
          <span class="text-xs text-gray-500 font-bold uppercase tracking-wider">对话交互频次</span>
          <h3 class="text-2xl sm:text-3xl font-black text-gray-900">{{ formatNumber(summaryData.calls) }}</h3>
          <p class="text-xs text-gray-400">大模型会话发起总次数</p>
        </div>
        <div class="p-3.5 bg-purple-50/80 rounded-2xl text-purple-600">
          <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </div>
      </div>

      <div class="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm flex items-center justify-between">
        <div class="space-y-1">
          <span class="text-xs text-gray-500 font-bold uppercase tracking-wider">平均单次消耗</span>
          <h3 class="text-2xl sm:text-3xl font-black text-gray-900">{{ formatCompactNumber(summaryData.avg_tokens) }}</h3>
          <p class="text-xs text-gray-400">平均每次会话 Token 数</p>
        </div>
        <div class="p-3.5 bg-yellow-50/80 rounded-2xl text-yellow-600">
          <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        </div>
      </div>

      <div class="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm flex items-center justify-between">
        <div class="space-y-1">
          <span class="text-xs text-gray-500 font-bold uppercase tracking-wider">当前活跃智能体</span>
          <h3 class="text-2xl sm:text-3xl font-black text-gray-900">{{ agentData.length }}</h3>
          <p class="text-xs text-gray-400">贡献 Token 消耗的智能体数</p>
        </div>
        <div class="p-3.5 bg-green-50/80 rounded-2xl text-green-600">
          <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
        </div>
      </div>
    </div>

    <!-- Trend Analysis Area -->
    <div class="bg-white rounded-2xl shadow-sm p-4 sm:p-6 border border-gray-100">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-base sm:text-lg font-bold text-gray-900 flex items-center">
          <span class="w-1.5 h-1.5 rounded-full bg-primary mr-2"></span>
          双 Y 轴趋势分析 (API 频次 vs Token 消耗)
        </h2>
      </div>
      <div class="h-96 w-full relative flex items-center justify-center">
        <div v-if="trendData.length === 0" class="text-gray-400 text-sm">
          暂无趋势数据
        </div>
        <v-chart v-else class="h-full w-full" :option="trendChartOption" autoresize />
      </div>
    </div>

    <!-- Agent Distribution Area -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="bg-white rounded-2xl shadow-sm p-4 sm:p-6 border border-gray-100 flex flex-col justify-between">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-base sm:text-lg font-bold text-gray-900 flex items-center">
            <span class="w-1.5 h-1.5 rounded-full bg-primary mr-2"></span>
            智能体占比
          </h2>
        </div>
        <div class="h-72 w-full relative flex items-center justify-center">
          <div v-if="agentData.length === 0" class="text-gray-400 text-sm">
            暂无智能体分布
          </div>
          <v-chart v-else class="h-full w-full" :option="agentChartOption" autoresize />
        </div>
      </div>

      <div class="bg-white rounded-2xl shadow-sm p-4 sm:p-6 border border-gray-100 lg:col-span-2 flex flex-col justify-between">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-base sm:text-lg font-bold text-gray-900 flex items-center">
            <span class="w-1.5 h-1.5 rounded-full bg-primary mr-2"></span>
            智能体算力消耗排行榜
          </h2>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-100 text-sm">
            <thead>
              <tr class="text-left text-xs font-bold text-gray-400 uppercase tracking-wider">
                <th class="py-3 px-4">智能体名称</th>
                <th class="py-3 px-4">交互次数</th>
                <th class="py-3 px-4">总 Token 消耗</th>
                <th class="py-3 px-4">平均单次消耗</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-50 text-gray-700">
              <tr v-if="agentData.length === 0">
                <td colspan="4" class="py-10 text-center text-gray-400">暂无明细数据</td>
              </tr>
              <tr v-for="agent in agentData" :key="agent.agent_id" class="hover:bg-gray-50/50 transition-colors">
                <td class="py-3 px-4 font-bold text-gray-900">{{ agent.name }}</td>
                <td class="py-3 px-4">{{ formatNumber(agent.calls) }} 次</td>
                <td class="py-3 px-4 font-semibold">{{ formatCompactNumber(agent.total_tokens) }}</td>
                <td class="py-3 px-4 text-gray-500">{{ formatCompactNumber(Math.round(agent.total_tokens / Math.max(agent.calls, 1))) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- User Ranking Card (Admin Only) -->
    <div v-if="userInfo?.role === 'admin'" class="bg-white rounded-2xl shadow-sm p-4 sm:p-6 border border-gray-100">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h2 class="text-base sm:text-lg font-bold text-gray-900 flex items-center">
            <span class="w-1.5 h-1.5 rounded-full bg-primary mr-2"></span>
            系统用户算力审计账单
          </h2>
          <p class="text-xs text-gray-400 mt-1">按用户累计大模型资源 Token 消耗的分布和占比排行</p>
        </div>
      </div>
      
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-100 text-sm">
          <thead>
            <tr class="text-left text-xs font-bold text-gray-400 uppercase tracking-wider">
              <th class="py-3 px-4">用户名 / 账号</th>
              <th class="py-3 px-4">真实姓名</th>
              <th class="py-3 px-4">API 调用次数</th>
              <th class="py-3 px-4">总 Token 消耗</th>
              <th class="py-3 px-4">系统算力占比</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50 text-gray-700">
            <tr v-if="userData.length === 0">
              <td colspan="5" class="py-10 text-center text-gray-400">暂无用户审计账单</td>
            </tr>
            <tr v-for="userItem in userData" :key="userItem.username" class="hover:bg-gray-50/50 transition-colors">
              <td class="py-3.5 px-4 font-bold text-gray-900">{{ userItem.username }}</td>
              <td class="py-3.5 px-4 text-gray-600">{{ userItem.real_name || '-' }}</td>
              <td class="py-3.5 px-4">{{ formatNumber(userItem.calls) }} 次</td>
              <td class="py-3.5 px-4 font-semibold text-gray-900">{{ formatCompactNumber(userItem.total_tokens) }}</td>
              <td class="py-3.5 px-4">
                <div class="flex items-center gap-3 w-48">
                  <div class="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      class="h-full bg-indigo-500 rounded-full transition-all duration-500"
                      :style="{ width: `${userItem.ratio}%` }"
                    ></div>
                  </div>
                  <span class="text-xs font-bold text-gray-500 w-10 text-right">{{ userItem.ratio }}%</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import axios from "../utils/axios";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart, PieChart } from "echarts/charts";
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from "echarts/components";

use([
  CanvasRenderer,
  LineChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
]);

const API_BASE = "";
const apiKey = ref(localStorage.getItem("api_key") || "");
const userInfo = ref<any>(null);
const loading = ref(false);
const period = ref("week");

// 数据源
const trendData = ref<any[]>([]);
const agentData = ref<any[]>([]);
const userData = ref<any[]>([]);

// 头部核心卡片数据
const summaryData = computed(() => {
  let total_tokens = 0;
  let calls = 0;
  
  if (trendData.value && trendData.value.length > 0) {
    total_tokens = trendData.value.reduce((acc, curr) => acc + (curr.total_tokens || 0), 0);
    calls = trendData.value.reduce((acc, curr) => acc + (curr.calls || 0), 0);
  }
  
  const avg_tokens = calls > 0 ? Math.round(total_tokens / calls) : 0;
  
  return {
    total_tokens,
    calls,
    avg_tokens
  };
});

const formatNumber = (num: number) => {
  if (num === undefined || num === null) return "0";
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
};

const formatCompactNumber = (num: number) => {
  if (num === undefined || num === null) return "0";
  if (num >= 1.0e9) {
    return (num / 1.0e9).toFixed(2).replace(/\.00$/, "") + " B";
  }
  if (num >= 1.0e6) {
    return (num / 1.0e6).toFixed(2).replace(/\.00$/, "") + " M";
  }
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
};

// 时段切换
const onPeriodChange = () => {
  refreshAll();
};

const refreshAll = async () => {
  loading.value = true;
  try {
    let daysVal = 7;
    if (period.value === "today") daysVal = 1;
    else if (period.value === "month") daysVal = 30;

    // 1. 获取折线趋势
    const trendRes = await axios.get(`${API_BASE}/api/portal/dashboard/token-stats/trends`, {
      headers: { "X-API-Key": apiKey.value },
      params: { days: daysVal }
    });
    trendData.value = trendRes.data;

    // 2. 获取智能体分布占比
    const agentRes = await axios.get(`${API_BASE}/api/portal/dashboard/token-stats/agents`, {
      headers: { "X-API-Key": apiKey.value },
      params: { period: period.value }
    });
    agentData.value = agentRes.data;

    // 3. 获取用户排行榜
    if (userInfo.value?.role === "admin") {
      const userRes = await axios.get(`${API_BASE}/api/portal/dashboard/token-stats/users`, {
        headers: { "X-API-Key": apiKey.value },
        params: { period: period.value }
      });
      userData.value = userRes.data;
    }
  } catch (error) {
    console.error("Failed to load token statistics:", error);
  } finally {
    loading.value = false;
  }
};

const trendChartOption = computed(() => {
  if (!trendData.value || trendData.value.length === 0) return {};

  const dates = trendData.value.map(item => item.date);
  const tokens = trendData.value.map(item => item.total_tokens);
  const calls = trendData.value.map(item => item.calls);

  return {
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255, 255, 255, 0.95)",
      borderWidth: 1,
      borderColor: "#e5e7eb",
      textStyle: { color: "#374151" },
      padding: [10, 14]
    },
    legend: {
      data: ["Token 消耗量", "API 交互次数"],
      bottom: 0,
      icon: "circle"
    },
    grid: {
      left: "3%",
      right: "4%",
      bottom: "10%",
      top: "10%",
      containLabel: true
    },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: dates,
      axisLine: { lineStyle: { color: "#9ca3af" } },
      axisTick: { show: false }
    },
    yAxis: [
      {
        type: "value",
        name: "Token 消耗",
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { type: "dashed", color: "#f3f4f6" } }
      },
      {
        type: "value",
        name: "交互次数",
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: "Token 消耗量",
        type: "line",
        smooth: true,
        showSymbol: false,
        data: tokens,
        itemStyle: { color: "#4f46e5" },
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(79, 70, 229, 0.2)" },
              { offset: 1, color: "rgba(79, 70, 229, 0)" }
            ]
          }
        }
      },
      {
        name: "API 交互次数",
        type: "line",
        yAxisIndex: 1,
        smooth: true,
        showSymbol: false,
        data: calls,
        itemStyle: { color: "#10b981" },
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(16, 185, 129, 0.2)" },
              { offset: 1, color: "rgba(16, 185, 129, 0)" }
            ]
          }
        }
      }
    ]
  };
});

const agentChartOption = computed(() => {
  if (!agentData.value || agentData.value.length === 0) return {};

  // 只展示前5，其余的归类为其他
  let displayData = [];
  if (agentData.value.length <= 5) {
    displayData = agentData.value.map(item => ({
      name: item.name,
      value: item.total_tokens
    }));
  } else {
    displayData = agentData.value.slice(0, 4).map(item => ({
      name: item.name,
      value: item.total_tokens
    }));
    const otherSum = agentData.value.slice(4).reduce((acc, curr) => acc + curr.total_tokens, 0);
    displayData.push({
      name: "其他",
      value: otherSum
    });
  }

  return {
    tooltip: {
      trigger: "item",
      formatter: "{b}: {c} ({d}%)"
    },
    legend: {
      orient: "horizontal",
      bottom: "0%",
      left: "center",
      icon: "circle",
      textStyle: { color: "#4b5563", fontSize: 11 }
    },
    series: [
      {
        name: "Token 消耗占比",
        type: "pie",
        radius: ["40%", "70%"],
        roseType: "radius",
        itemStyle: {
          borderRadius: 8,
          borderColor: "#fff",
          borderWidth: 2
        },
        label: { show: false },
        emphasis: {
          label: {
            show: true,
            fontSize: 12,
            fontWeight: "bold",
            formatter: "{b}\n{d}%"
          }
        },
        data: displayData,
        color: ["#6366f1", "#ec4899", "#10b981", "#f59e0b", "#3b82f6"]
      }
    ]
  };
});

const loadUserInfo = () => {
  const stored = localStorage.getItem("user_info");
  if (stored) {
    userInfo.value = JSON.parse(stored);
  }
};

onMounted(() => {
  loadUserInfo();
  refreshAll();
});
</script>
