<template>
  <section class="page" data-module="security">
    <header class="page-head">
      <div>
        <h2>安防巡视管理</h2>
        <p class="page-desc">维护安防记录，围绕巡视编号、巡视区域、巡视人员、巡视时间做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记安防记录</button>
        <button class="btn" type="button" @click="exportRows">导出安防巡视清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td class="row-actions">
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">{{ emptyText }}</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条安防巡视记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchJson, request } from '@/api/client'

type Row = Record<string, string | number | null>
type Stat = { label: string; value: number }
type PagePayload = { items: Row[]; total: number }

const ENDPOINT = '/api/security'
const columns = ["巡视编号", "巡视区域", "巡视人员", "巡视时间", "异常描述", "处理情况", "交接事项", "巡视状态"]
const actions = ["开始巡视", "记录异常", "完成巡视"]
// 筛选条件与后端共用同一套口径：页面字段 -> 查询参数
const FILTER_PARAMS: Record<string, string> = {
  巡视编号: 'keyword',
  巡视区域: 'area',
  巡视人员: 'operator',
  交接事项: 'handover',
}
const filterFields = Object.keys(FILTER_PARAMS)
const emptyText = '暂无安防巡视数据，可先登记安防记录'
const LIST_ERROR_TEXT = '安防巡视列表读取失败'

const rows = ref<Row[]>([])
const total = ref(0)
const stats = ref<Stat[]>([
  { label: '今日巡视', value: 0 },
  { label: '异常巡视', value: 0 },
  { label: '待巡视区域', value: 0 },
])
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})

function buildQuery(): string {
  const params = new URLSearchParams()
  for (const field of filterFields) {
    const value = filters.value[field]?.trim()
    if (value) {
      params.set(FILTER_PARAMS[field], value)
    }
  }
  return params.toString()
}

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '安防记录登记入口尚未接入审批流'
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    const result = (await response.json()) as { ok?: boolean; message?: string }
    if (!response.ok || !result.ok) {
      throw new Error(result.message || '安防巡视动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '安防巡视操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = buildQuery()
  try {
    const [listPayload, statPayload] = await Promise.all([
      fetchJson<PagePayload>(`${ENDPOINT}?${query}`),
      fetchJson<Stat[]>(`${ENDPOINT}/stats?${query}`),
    ])
    rows.value = listPayload.items ?? []
    total.value = listPayload.total ?? rows.value.length
    stats.value = statPayload
  } catch {
    rows.value = []
    total.value = 0
    errorMessage.value = LIST_ERROR_TEXT
  }
}

onMounted(reload)
</script>
