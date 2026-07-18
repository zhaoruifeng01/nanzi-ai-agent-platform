<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowPathIcon,
  ChevronRightIcon,
  SparklesIcon,
} from '@heroicons/vue/24/outline'
import { portalApi } from '../api/portal'
import type { ScenarioTemplateInstanceSummary, ScenarioTemplateSummary } from '../api/portal'
import { useToast } from '../composables/useToast'

const router = useRouter()
const { showToast } = useToast()

const templates = ref<ScenarioTemplateSummary[]>([])
const installedInstances = ref<ScenarioTemplateInstanceSummary[]>([])
const loading = ref(false)

const loadTemplates = async () => {
  loading.value = true
  try {
    const res = await portalApi.getScenarioTemplates()
    templates.value = res.data.data || []
  } catch (error) {
    showToast('获取场景模板失败', 'error')
  } finally {
    loading.value = false
  }
}

const loadInstalledInstances = async () => {
  try {
    const res = await portalApi.getScenarioTemplateInstances()
    installedInstances.value = res.data.data || []
  } catch (error) {
    showToast('获取已交付场景失败', 'error')
  }
}

const openDetail = (template: ScenarioTemplateSummary) => {
  router.push({ name: 'ScenarioTemplateDetail', params: { templateId: template.id } })
}

const openInstalledDebug = (instance: ScenarioTemplateInstanceSummary) => {
  router.push({
    name: 'AgentDebug',
    query: {
      agent_id: instance.agent.id,
      version_id: instance.latest_run?.version_id || undefined,
      sample_question: instance.sample_questions[0] || undefined,
    },
  })
}

onMounted(async () => {
  await Promise.all([loadTemplates(), loadInstalledInstances()])
})
</script>

<template>
  <div class="min-h-full bg-gray-50 px-4 py-5 sm:px-6 lg:px-8">
    <div class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-xs font-semibold uppercase text-blue-600">Solution Package</p>
        <h1 class="mt-1 text-2xl font-bold text-gray-900">场景包市场</h1>
        <p class="mt-1 text-sm text-gray-500">
          先选择一个要交付给业务的场景包，再进入独立的方案详情和交付向导。
        </p>
        <p class="mt-1 text-xs text-gray-400">首批内置：经营分析 ChatBI 助手、企业知识问答助手、运维巡检助手。</p>
      </div>
      <button
        class="inline-flex items-center justify-center gap-2 rounded-md border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="loading"
        @click="Promise.all([loadTemplates(), loadInstalledInstances()])"
      >
        <ArrowPathIcon class="h-4 w-4" :class="{ 'animate-spin': loading }" />
        刷新
      </button>
    </div>

    <section v-if="installedInstances.length" class="mb-6 rounded-lg border border-blue-100 bg-white p-5 shadow-sm">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="text-xs font-semibold uppercase text-blue-600">Delivered</p>
          <h2 class="mt-1 text-lg font-bold text-gray-900">已交付场景</h2>
          <p class="mt-1 text-sm text-gray-500">这里可以继续查看已安装场景，并直接带着推荐问题打开调试台验收。</p>
        </div>
      </div>
      <div class="mt-4 grid gap-3 xl:grid-cols-2">
        <article
          v-for="instance in installedInstances"
          :key="instance.id"
          class="rounded-lg border border-gray-200 bg-gray-50 p-4"
        >
          <div class="flex items-start justify-between gap-3">
            <div>
              <h3 class="text-sm font-semibold text-gray-900">{{ instance.agent.display_name }}</h3>
              <p class="mt-1 text-xs text-gray-500">{{ instance.template_name }} · {{ instance.agent.name }}</p>
            </div>
            <span class="rounded bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">{{ instance.status }}</span>
          </div>
          <div class="mt-3 space-y-1 text-xs text-gray-600">
            <div v-for="resource in instance.resource_summary" :key="resource.type" class="flex justify-between gap-3">
              <span>{{ resource.label }}</span>
              <span class="text-right text-gray-500">{{ (resource.names?.length ? resource.names : resource.ids).join('、') }}</span>
            </div>
          </div>
          <div class="mt-3 flex flex-wrap gap-2">
            <button
              class="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
              @click="openInstalledDebug(instance)"
            >
              打开调试台
            </button>
            <button
              class="rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
              @click="router.push({ name: 'ScenarioTemplateInstall', params: { templateId: instance.template_id }, query: { step: 'done', instance_id: instance.id } })"
            >
              查看交付记录
            </button>
          </div>
        </article>
      </div>
    </section>

    <div class="grid gap-4 xl:grid-cols-3">
      <article
        v-for="template in templates"
        :key="template.id"
        class="rounded-lg border border-gray-200 bg-white p-5 shadow-sm transition hover:border-blue-200 hover:shadow-md"
      >
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <h2 class="text-lg font-semibold text-gray-900">{{ template.name }}</h2>
              <span v-if="template.recommended" class="rounded bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">推荐</span>
            </div>
            <p class="mt-2 text-sm leading-6 text-gray-600">{{ template.description }}</p>
          </div>
          <SparklesIcon class="h-5 w-5 flex-shrink-0 text-blue-500" />
        </div>

        <div class="mt-5 grid grid-cols-2 gap-2 text-xs">
          <div class="rounded-md bg-gray-50 p-3">
            <div class="text-gray-400">预计交付</div>
            <div class="mt-1 font-semibold text-gray-800">{{ template.delivery_time || '待评估' }}</div>
          </div>
          <div class="rounded-md bg-gray-50 p-3">
            <div class="text-gray-400">交付成熟度</div>
            <div class="mt-1 font-semibold text-gray-800">{{ template.maturity || '基础版' }}</div>
          </div>
        </div>

        <div class="mt-4">
          <div class="text-xs font-semibold text-gray-400">适用部门</div>
          <div class="mt-2 flex flex-wrap gap-1.5">
            <span
              v-for="dept in template.target_departments"
              :key="dept"
              class="rounded border border-gray-200 px-2 py-0.5 text-xs text-gray-600"
            >
              {{ dept }}
            </span>
          </div>
        </div>

        <div class="mt-4 flex flex-wrap gap-2">
          <span
            v-for="capability in template.included_capabilities"
            :key="capability"
            class="rounded-md border border-gray-200 bg-gray-50 px-2 py-1 text-xs text-gray-600"
          >
            {{ capability }}
          </span>
        </div>

        <button
          class="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          @click="openDetail(template)"
        >
          查看方案
          <ChevronRightIcon class="h-4 w-4" />
        </button>
      </article>
    </div>

    <div v-if="!loading && !templates.length" class="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center text-sm text-gray-500">
      暂无可用场景模板
    </div>
  </div>
</template>
