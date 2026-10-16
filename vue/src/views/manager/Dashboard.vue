<template>
  <div v-loading="loading">
    <el-row :gutter="16" class="cards">
      <el-col :span="6"><el-card><div class="stat"><div class="num">{{ data.total_users }}</div><div class="label">用户数</div></div></el-card></el-col>
      <el-col :span="6"><el-card><div class="stat"><div class="num">{{ data.total_analyses }}</div><div class="label">分析数</div></div></el-card></el-col>
      <el-col :span="6"><el-card><div class="stat"><div class="num">{{ data.total_patents }}</div><div class="label">检索专利数</div></div></el-card></el-col>
      <el-col :span="6"><el-card><div class="stat"><div class="num">{{ sourceCount }}</div><div class="label">数据源类型</div></div></el-card></el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="10">
        <el-card><template #header>风险分布</template><div ref="riskRef" style="height:300px" /></el-card>
      </el-col>
      <el-col :span="14">
        <el-card><template #header>Agent 节点调用统计</template><div ref="nodeRef" style="height:300px" /></el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top:16px">
      <template #header>数据源命中统计</template>
      <el-table :data="sourceRows" size="small">
        <el-table-column prop="source" label="数据源" />
        <el-table-column prop="count" label="命中数" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { adminRequest } from '../../utils/request'

const loading = ref(false)
const data = ref({ total_users: 0, total_analyses: 0, total_patents: 0, risk_distribution: {}, node_stats: {}, source_stats: {} })
const riskRef = ref(null)
const nodeRef = ref(null)
let riskChart = null
let nodeChart = null

const sourceRows = computed(() => Object.entries(data.value.source_stats || {}).map(([source, count]) => ({ source, count })))
const sourceCount = computed(() => Object.keys(data.value.source_stats || {}).length)

function drawCharts() {
  if (riskRef.value) {
    riskChart = riskChart || echarts.init(riskRef.value)
    const r = data.value.risk_distribution || {}
    riskChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie', radius: ['40%', '65%'],
        data: [
          { name: '高风险', value: r.high || 0, itemStyle: { color: '#f56c6c' } },
          { name: '中风险', value: r.medium || 0, itemStyle: { color: '#e6a23c' } },
          { name: '低风险', value: r.low || 0, itemStyle: { color: '#67c23a' } },
          { name: '排除', value: r.excluded || 0, itemStyle: { color: '#909399' } },
        ],
      }],
    })
  }
  if (nodeRef.value) {
    nodeChart = nodeChart || echarts.init(nodeRef.value)
    const ns = data.value.node_stats || {}
    const names = Object.keys(ns)
    nodeChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { bottom: 0 },
      grid: { left: 40, right: 20, bottom: 40, top: 20 },
      xAxis: { type: 'category', data: names },
      yAxis: { type: 'value' },
      series: [
        { name: '成功', type: 'bar', stack: 't', data: names.map(n => ns[n].success || 0), itemStyle: { color: '#67c23a' } },
        { name: '降级', type: 'bar', stack: 't', data: names.map(n => ns[n].degraded || 0), itemStyle: { color: '#e6a23c' } },
        { name: '失败', type: 'bar', stack: 't', data: names.map(n => ns[n].failed || 0), itemStyle: { color: '#f56c6c' } },
      ],
    })
  }
}

async function load() {
  loading.value = true
  try {
    const res = await adminRequest.get('/api/fto/dashboard/overview')
    data.value = res.data
    await new Promise(r => setTimeout(r, 50))
    drawCharts()
  } finally { loading.value = false }
}

function resize() { riskChart?.resize(); nodeChart?.resize() }
onMounted(() => { load(); window.addEventListener('resize', resize) })
onBeforeUnmount(() => { window.removeEventListener('resize', resize); riskChart?.dispose(); nodeChart?.dispose() })
</script>

<style scoped>
.cards .num { font-size: 28px; font-weight: 700; color: #2f6bff; }
.cards .label { color: #909399; font-size: 13px; margin-top: 4px; }
</style>
