/** 安防巡视共用实现：巡视区域读取、异常统计与处理入口统一走这里。
 *
 * 列表、区域概览、异常统计都从后端同一份安防记录口径取数，
 * 巡视人员与交接事项随区域概览一起给出；空数据反馈（单元格占位、
 * 空列表提示）也收在这里，页面不再各自维护一套。
 */
import { computed, ref } from 'vue'

import { fetchJson, request } from '@/api/client'

export type SecurityRow = Record<string, string | number | null>

export type SecurityArea = {
  area: string
  total: number
  abnormal: number
  pending: number
  inspectors: string[]
  handover_items: string[]
}

export type SecurityStats = {
  today: number
  abnormal: number
  pending_areas: number
}

const ENDPOINT = '/api/security'

export const SECURITY_COLUMNS = [
  '巡视编号', '巡视区域', '巡视人员', '巡视时间', '异常描述', '处理情况', '交接事项', '巡视状态',
]
export const SECURITY_ACTIONS = ['开始巡视', '记录异常', '完成巡视']
export const SECURITY_STATUSES = ['已排班', '巡视中', '正常完成', '发现异常']

/** 空数据反馈口径：单元格空值统一占位，空列表统一一句提示。 */
export const EMPTY_CELL_TEXT = '—'
export const EMPTY_LIST_TEXT = '暂无安防巡视数据，可先登记安防记录'

export function cellText(value: unknown): string {
  const text = String(value ?? '').trim()
  return text === '' || text === 'None' ? EMPTY_CELL_TEXT : text
}

export function useSecurityRecords() {
  const rows = ref<SecurityRow[]>([])
  const total = ref(0)
  const areas = ref<SecurityArea[]>([])
  const stats = ref<SecurityStats>({ today: 0, abnormal: 0, pending_areas: 0 })
  const errorMessage = ref('')

  const statCards = computed(() => [
    { label: '今日巡视', value: stats.value.today },
    { label: '异常巡视', value: stats.value.abnormal },
    { label: '待巡视区域', value: stats.value.pending_areas },
  ])

  /** 巡视区域读取：选项与汇总都来自同一份区域概览。 */
  const areaOptions = computed(() => areas.value.map((item) => item.area))

  async function loadRows(filters: Record<string, string>) {
    const query = new URLSearchParams()
    for (const [key, value] of Object.entries(filters)) {
      const text = String(value ?? '').trim()
      if (text) {
        query.set(key, text)
      }
    }
    const response = await request(`${ENDPOINT}?${query.toString()}`)
    if (!response.ok) {
      throw new Error('安防记录列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  }

  async function loadAreas() {
    const payload = await fetchJson<{ areas: SecurityArea[] }>(`${ENDPOINT}/areas`)
    areas.value = payload.areas ?? []
  }

  async function loadStats() {
    const payload = await fetchJson<{ stats: SecurityStats }>(`${ENDPOINT}/stats`)
    stats.value = payload.stats ?? { today: 0, abnormal: 0, pending_areas: 0 }
  }

  /** 三个入口共用一次刷新，保证页面各区块看到的是同一份数据。 */
  async function refresh(filters: Record<string, string> = {}) {
    errorMessage.value = ''
    try {
      await Promise.all([loadRows(filters), loadAreas(), loadStats()])
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '安防巡视数据读取失败'
    }
  }

  /** 处理入口：开始巡视、记录异常、完成巡视统一从这里发起。 */
  async function runAction(action: string, row: SecurityRow, filters: Record<string, string> = {}) {
    errorMessage.value = ''
    try {
      const response = await request(`${ENDPOINT}/${row.id}/actions`, {
        method: 'POST',
        body: JSON.stringify({ action }),
      })
      if (!response.ok) {
        throw new Error('安防巡视动作未生效，请稍后重试')
      }
      await refresh(filters)
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '安防巡视操作失败'
    }
  }

  return {
    rows,
    total,
    areas,
    areaOptions,
    stats,
    statCards,
    errorMessage,
    refresh,
    runAction,
  }
}
