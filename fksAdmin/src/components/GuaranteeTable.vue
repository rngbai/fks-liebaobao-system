<script setup>
import { formatNumber } from '../utils/format'
import StatusPill from './StatusPill.vue'

const props = defineProps({
  rows: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['inspect'])

function resolveTone(statusClass = '') {
  if (statusClass === 'success' || statusClass === 'done') return 'success'
  if (statusClass === 'matched') return 'info'
  if (statusClass === 'pending') return 'warning'
  if (statusClass === 'appeal' || statusClass === 'cancelled' || statusClass === 'expired') return 'danger'
  return 'neutral'
}
</script>

<template>
  <div class="table-shell">
    <div v-if="!rows.length" class="table-empty">暂无担保档案。</div>
    <div v-else class="table-scroll">
      <table class="ops-table">
        <thead>
          <tr>
            <th>订单 / 状态</th>
            <th>买卖双方</th>
            <th>交易内容</th>
            <th>截图 / 时间</th>
            <th>后台备注</th>
            <th class="align-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id || row.orderNo">
            <td>
              <div class="strong-text">{{ row.id || row.orderNo }}</div>
              <div class="muted-text">{{ row.petName || row.pet_name || '未填写兽王' }}</div>
              <div class="status-wrap">
                <StatusPill :label="row.statusText || '未知状态'" :tone="resolveTone(row.statusClass || '')" />
              </div>
            </td>
            <td>
              <div class="strong-text">卖家：{{ row.sellerNickName || '未设置' }}</div>
              <div class="muted-text">卖家ID：{{ row.sellerBeastId || row.seller_beast_id || '未绑定' }}</div>
              <div class="muted-text">买家：{{ row.buyerBeastNick || row.buyer_beast_nick || '未填写' }} / {{ row.buyerBeastId || row.buyer_beast_id || '未填写' }}</div>
            </td>
            <td>
              <div class="strong-text">{{ formatNumber(row.tradeQuantity ?? row.trade_quantity ?? 1) }} 只 · 标价 {{ formatNumber(row.gemAmount ?? row.gem_amount ?? 0) }} 宝石</div>
              <div class="muted-text">卖家实扣：{{ formatNumber(row.sellerTotalCost ?? row.seller_total_cost ?? ((row.gemAmount ?? row.gem_amount ?? 0) + (row.feeAmount ?? row.fee_amount ?? 0))) }} / 买家实收：{{ formatNumber(row.actualReceive ?? row.actual_receive ?? 0) }}</div>
              <div class="muted-text">地球猎人：{{ row.sellerGameNick || row.seller_game_nick || '未填写' }} / {{ row.sellerGameId || row.seller_game_id || '未填写' }}</div>
            </td>

            <td>
              <div class="proof-tag" :class="{ 'is-ready': row.buyerProofImage || row.buyer_proof_image }">
                {{ row.buyerProofImage || row.buyer_proof_image ? '截图已上传' : '无截图' }}
              </div>
              <div class="muted-text">匹配：{{ row.matchedTime || row.matched_time || '—' }}</div>
              <div class="muted-text">上传：{{ row.buyerProofUploadedTime || row.buyer_proof_uploaded_time || '—' }}</div>
            </td>
            <td>
              <div class="muted-text">{{ row.adminNote || row.admin_note || '无后台备注' }}</div>
              <div class="muted-text">完成：{{ row.finishedTime || row.finished_time || '—' }}</div>
            </td>
            <td class="align-right">
              <button class="table-btn" type="button" @click="emit('inspect', row)">详情</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.table-shell {
  border-radius: 24px;
  border: 1px solid rgba(191, 205, 230, 0.1);
  background: rgba(255, 255, 255, 0.03);
}

.table-scroll {
  overflow-x: auto;
}

.ops-table {
  width: 100%;
  min-width: 1160px;
  border-collapse: collapse;
}

.ops-table th,
.ops-table td {
  padding: 16px 18px;
  border-bottom: 1px solid rgba(191, 205, 230, 0.08);
  text-align: left;
  vertical-align: top;
}

.ops-table th {
  position: sticky;
  top: 0;
  background: rgba(11, 18, 30, 0.94);
  color: rgba(222, 230, 243, 0.52);
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.ops-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.035);
}

.ops-table tbody tr:last-child td {
  border-bottom: none;
}

.strong-text {
  color: #fff8ec;
  font-weight: 700;
}

.muted-text {
  margin-top: 6px;
  color: rgba(229, 236, 248, 0.68);
  line-height: 1.7;
}

.status-wrap {
  margin-top: 10px;
}

.proof-tag {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(191, 205, 230, 0.12);
  background: rgba(255, 255, 255, 0.05);
  color: #edf2fb;
  font-size: 12px;
  font-weight: 700;
}

.proof-tag.is-ready {
  border-color: rgba(105, 215, 174, 0.24);
  background: rgba(105, 215, 174, 0.14);
  color: #acf2d5;
}

.align-right {
  text-align: right;
}

.table-btn {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 12px;
  border: 1px solid rgba(191, 205, 230, 0.12);
  background: rgba(255, 255, 255, 0.05);
  color: #edf2fb;
  font-weight: 700;
  cursor: pointer;
}

.table-empty {
  padding: 26px 18px;
  text-align: center;
  color: rgba(229, 236, 248, 0.72);
}
</style>
