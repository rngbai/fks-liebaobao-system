<script setup>
import { computed } from 'vue'
import { formatNumber } from '../utils/format'
import StatusPill from './StatusPill.vue'

const props = defineProps({
  item: {
    type: Object,
    default: () => ({}),
  },
  kind: {
    type: String,
    default: 'guarantee',
  },
  busy: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['copy', 'submit', 'inspect'])

function resolveTone(statusClass = '') {
  if (statusClass === 'success' || statusClass === 'done') return 'success'
  if (statusClass === 'matched' || statusClass === 'info') return 'info'
  if (statusClass === 'pending') return 'warning'
  if (statusClass === 'cancelled' || statusClass === 'expired' || statusClass === 'appeal') return 'danger'
  return 'neutral'
}

const tone = computed(() => resolveTone(props.item.statusClass || ''))
const isGuarantee = computed(() => props.kind === 'guarantee')
const orderId = computed(() => props.item.id || props.item.orderNo || '')
const title = computed(() => {
  if (isGuarantee.value) {
    return `${props.item.petName || props.item.pet_name || '未填写兽王'} · ${formatNumber(props.item.tradeQuantity ?? props.item.trade_quantity ?? 1)} 只`
  }
  return `${props.item.userNickName || '方块兽玩家'} · ${props.item.account || '未设置账号'}`
})
const subtitle = computed(() => {
  if (isGuarantee.value) {
    return `卖家猎人 ${props.item.sellerGameNick || props.item.seller_game_nick || '未填写'} / ${props.item.sellerGameId || props.item.seller_game_id || '未填写'}`
  }
  return `方块兽 ID ${props.item.beastId || '未绑定'} · 申请时间 ${props.item.createTime || '—'}`
})
const amountValue = computed(() => {
  if (isGuarantee.value) {
    return formatNumber(props.item.actualReceive ?? props.item.actual_receive ?? 0)
  }
  return formatNumber(props.item.actualAmount ?? props.item.actual_amount ?? 0)
})
const amountLabel = computed(() => (isGuarantee.value ? '买家实收' : '预计实转'))
const infoBlocks = computed(() => {
  if (isGuarantee.value) {
    const proofUploadedTime = props.item.buyerProofUploadedTime || props.item.buyer_proof_uploaded_time || '未上传'
    return [
      {
        label: '买家资料',
        value: `${props.item.buyerBeastNick || props.item.buyer_beast_nick || '未填写'} / ${props.item.buyerBeastId || props.item.buyer_beast_id || '未填写'}`,
      },
      {
        label: '金额口径',
        value: `标价 ${formatNumber(props.item.gemAmount ?? props.item.gem_amount ?? 0)} / 卖家实扣 ${formatNumber(props.item.sellerTotalCost ?? props.item.seller_total_cost ?? ((props.item.gemAmount ?? props.item.gem_amount ?? 0) + (props.item.feeAmount ?? props.item.fee_amount ?? 0)))} / 买家实收 ${formatNumber(props.item.actualReceive ?? props.item.actual_receive ?? 0)}`,
      },

      {
        label: '截图凭证',
        value: props.item.buyerProofImage || props.item.buyer_proof_image ? `已上传 · ${proofUploadedTime}` : '未上传',
      },
      {
        label: '匹配备注',
        value: props.item.buyerTradeNote || props.item.buyer_trade_note || '无',
      },
    ]
  }

  return [
    {
      label: '申请数量',
      value: `${formatNumber(props.item.requestAmount ?? props.item.request_amount ?? 0)}（手续费 ${formatNumber(props.item.feeAmount ?? props.item.fee_amount ?? 0)}）`,
    },
    {
      label: '绑定账号',
      value: `${props.item.userNickName || '方块兽玩家'} / ${props.item.account || '未设置账号'}`,
    },
    {
      label: '用户备注',
      value: props.item.userNote || '无',
    },
    {
      label: '当前状态',
      value: props.item.statusText || '待处理',
    },
  ]
})

const copyActions = computed(() => {
  if (isGuarantee.value) {
    return [
      { label: '复制单号', value: orderId.value },
      { label: '复制买家ID', value: props.item.buyerBeastId || props.item.buyer_beast_id || '' },
      { label: '复制猎人ID', value: props.item.sellerGameId || props.item.seller_game_id || '' },
    ]
  }

  return [
    { label: '复制单号', value: props.item.id || '' },
    { label: '复制方块兽ID', value: props.item.beastId || '' },
  ]
})

const actionLabel = computed(() => (isGuarantee.value ? '登记担保完成' : '登记转出完成'))
</script>

<template>
  <article class="queue-row">
    <div class="queue-main">
      <div class="queue-headline">
        <div>
          <div class="queue-id">{{ orderId }}</div>
          <div class="queue-title">{{ title }}</div>
          <div class="queue-subtitle">{{ subtitle }}</div>
        </div>
        <div class="queue-badges">
          <StatusPill :label="item.statusText || '待处理'" :tone="tone" />
          <div class="amount-chip">
            <span class="amount-value">{{ amountValue }}</span>
            <span class="amount-label">{{ amountLabel }}</span>
          </div>
        </div>
      </div>

      <div class="queue-info-grid">
        <div v-for="block in infoBlocks" :key="block.label" class="info-block">
          <div class="info-label">{{ block.label }}</div>
          <div class="info-value">{{ block.value }}</div>
        </div>
      </div>
    </div>

    <div class="queue-actions">
      <button class="ghost-btn" type="button" @click="emit('inspect', item)">查看详情</button>
      <button
        v-for="action in copyActions"
        :key="action.label"
        class="ghost-btn"
        type="button"
        @click="emit('copy', action)"
      >
        {{ action.label }}
      </button>
      <button class="primary-btn" type="button" :disabled="busy" @click="emit('submit', orderId)">
        {{ busy ? '处理中...' : actionLabel }}
      </button>
    </div>
  </article>
</template>

<style scoped>
.queue-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 240px;
  gap: 18px;
  padding: 18px;
  border-radius: 24px;
  border: 1px solid rgba(191, 205, 230, 0.1);
  background: rgba(255, 255, 255, 0.035);
}

.queue-headline {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}

.queue-id,
.info-label,
.amount-label {
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(222, 230, 243, 0.48);
}

.queue-title {
  margin-top: 8px;
  font-size: 20px;
  font-weight: 800;
  color: #fff8ec;
}

.queue-subtitle,
.info-value {
  margin-top: 8px;
  color: rgba(229, 236, 248, 0.74);
  line-height: 1.75;
}

.queue-badges {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.amount-chip {
  min-width: 118px;
  padding: 12px 14px;
  border-radius: 18px;
  border: 1px solid rgba(214, 167, 99, 0.16);
  background: rgba(214, 167, 99, 0.08);
  text-align: right;
}

.amount-value {
  display: block;
  font-family: 'Bahnschrift', 'Segoe UI Variable Display', 'Microsoft YaHei UI', sans-serif;
  font-size: 28px;
  font-weight: 800;
  color: #fff6df;
}

.queue-info-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.info-block {
  padding: 14px;
  border-radius: 18px;
  border: 1px solid rgba(191, 205, 230, 0.08);
  background: rgba(255, 255, 255, 0.03);
}

.queue-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  justify-content: center;
}

.ghost-btn,
.primary-btn {
  min-height: 42px;
  border-radius: 14px;
  border: 1px solid rgba(191, 205, 230, 0.12);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.ghost-btn {
  background: rgba(255, 255, 255, 0.05);
  color: #edf2fb;
}

.primary-btn {
  border: none;
  background: linear-gradient(135deg, #d6a763, #b88743);
  color: #1e1203;
  box-shadow: 0 14px 28px rgba(184, 135, 67, 0.18);
}

.primary-btn:disabled {
  cursor: wait;
  opacity: 0.7;
}

@media (max-width: 1280px) {
  .queue-row {
    grid-template-columns: 1fr;
  }

  .queue-actions {
    flex-direction: row;
    flex-wrap: wrap;
  }
}

@media (max-width: 900px) {
  .queue-info-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .queue-headline {
    flex-direction: column;
  }

  .queue-badges {
    align-items: flex-start;
  }

  .queue-info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
