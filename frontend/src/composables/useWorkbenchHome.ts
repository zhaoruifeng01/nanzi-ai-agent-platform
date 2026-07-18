import { ref } from "vue"
import axios from "@/utils/axios"
import type { WorkbenchHomePayload } from "@/types/workbench"

export function useWorkbenchHome() {
  const payload = ref<WorkbenchHomePayload | null>(null)
  const loading = ref(false)
  const refreshing = ref(false)
  const error = ref("")

  const load = async (options: { silent?: boolean } = {}) => {
    const silent = Boolean(options.silent && payload.value)
    if (silent) refreshing.value = true
    else loading.value = true
    error.value = ""
    try {
      const response = await axios.get("/api/portal/workbench/home")
      payload.value = response.data?.data
    } catch {
      error.value = payload.value
        ? "工作台暂时无法更新，已保留最近一次成功内容。"
        : "工作台暂时无法加载，请稍后重试。"
    } finally {
      loading.value = false
      refreshing.value = false
    }
  }

  const refresh = () => load({ silent: true })

  return { payload, loading, refreshing, error, load, refresh }
}
