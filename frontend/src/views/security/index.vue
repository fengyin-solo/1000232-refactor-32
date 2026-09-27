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
      <article v-for="item in statCards" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <div class="area-row">
      <article v-for="item in areas" :key="item.area" class="area-card">
        <strong>{{ item.area }}</strong>
        <span>巡视 {{ item.total }} 次 · 异常 {{ item.abnormal }} · 待处理 {{ item.pending }}</span>
        <span>巡视人员：{{ item.inspectors.join('、') || EMPTY_CELL_TEXT }}</span>
        <span>交接事项：{{ item.handover_items.join('；') || EMPTY_CELL_TEXT }}</span>
      </article>
      <p v-if="!areas.length" class="empty-state">暂无巡视区域数据</p>
    </div>

    <form class="filter-bar" @submit.prevent="applyFilters">
      <label class="filter-item">
        <span>巡视编号</span>
        <input v-model="filters.keyword" placeholder="按巡视编号检索" />
      </label>
      <label class="filter-item">
        <span>巡视区域</span>
        <select v-model="filters.area">
          <option value="">全部区域</option>
          <option v-for="area in areaOptions" :key="area" :value="area">{{ area }}</option>
        </select>
      </label>
      <label class="filter-item">
        <span>巡视人员</span>
        <input v-model="filters.inspector" placeholder="按巡视人员检索" />
      </label>
      <label class="filter-item">
        <span>巡视状态</span>
        <select v-model="filters.status">
          <option value="">全部状态</option>
          <option v-for="status in SECURITY_STATUSES" :key="status" :value="status">{{ status }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in SECURITY_COLUMNS" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in SECURITY_COLUMNS" :key="column">{{ cellText(row[column]) }}</td>
          <td class="row-actions">
            <button
              v-for="action in SECURITY_ACTIONS"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row, filters)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="SECURITY_COLUMNS.length + 1" class="empty-state">{{ EMPTY_LIST_TEXT }}</td>
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

import {
  EMPTY_CELL_TEXT,
  EMPTY_LIST_TEXT,
  SECURITY_ACTIONS,
  SECURITY_COLUMNS,
  SECURITY_STATUSES,
  cellText,
  useSecurityRecords,
} from './useSecurityRecords'

const { rows, total, areas, areaOptions, statCards, errorMessage, refresh, runAction } =
  useSecurityRecords()

const filters = ref<Record<string, string>>({ keyword: '', area: '', inspector: '', status: '' })

function applyFilters() {
  void refresh(filters.value)
}

function resetFilters() {
  filters.value = { keyword: '', area: '', inspector: '', status: '' }
  void refresh(filters.value)
}

function exportRows() {
  window.open('/api/security/export', '_blank')
}

function openCreate() {
  errorMessage.value = '安防记录登记入口尚未接入审批流'
}

onMounted(() => refresh(filters.value))
</script>

<style scoped>
.area-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}
.area-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 220px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 12px;
  color: var(--muted);
}
.area-card strong {
  font-size: 13px;
  color: #1f2937;
}
</style>
