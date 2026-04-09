<template>
  <el-dialog
    v-model="visible"
    title="API 配置"
    width="700px"
    :close-on-click-modal="!required"
    :close-on-press-escape="!required"
    :show-close="!required"
    :before-close="handleBeforeClose"
    class="api-config-dialog"
  >
    <div class="api-config-content">
      <!-- 1. 选择模型 -->
      <div class="section">
        <h3 class="section-title">1. 选择模型</h3>
        <div class="model-cards">
          <!-- Gemini 卡片 -->
          <div 
            class="model-card" 
            :class="{ 'selected': selectedModel === 'gemini' }"
            @click="selectedModel = 'gemini'"
          >
            <div class="model-card-check" v-if="selectedModel === 'gemini'">
              <el-icon><Check /></el-icon>
            </div>
            <h4 class="model-card-title">Google Gemini</h4>
            <p class="model-card-desc">具有高性能和低延迟的多模态能力。</p>
          </div>
          
          <!-- 豆包 卡片 -->
          <div
            class="model-card"
            :class="{ 'selected': selectedModel === 'doubao' }"
            @click="selectedModel = 'doubao'"
          >
            <div class="model-card-check" v-if="selectedModel === 'doubao'">
              <el-icon><Check /></el-icon>
            </div>
            <h4 class="model-card-title">豆包</h4>
            <p class="model-card-desc">针对中文任务和创意写作进行了优化。</p>
          </div>
        </div>
      </div>
      
      <!-- 2. 配置凭证 -->
      <div class="section">
        <h3 class="section-title">2. 配置 {{ selectedModel === 'gemini' ? 'Gemini' : '豆包' }}</h3>
        
        <!-- API Key 输入 -->
        <div class="form-group">
          <label class="form-label">
            API 密钥 (API Key) <span class="required-mark">*</span>
          </label>
          <el-input
            v-model="currentConfig.api_key"
            type="password"
            :placeholder="`请输入您的 ${selectedModel === 'gemini' ? 'Gemini' : '豆包'} API Key`"
            show-password
            :disabled="loading"
            @blur="validateCurrentConfig"
            class="api-key-input"
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
          <p class="error-hint" v-if="currentErrors.api_key">{{ currentErrors.api_key }}</p>
        </div>
        
        <!-- 使用自定义端点/代理 -->
        <div class="form-group">
          <div class="switch-group">
            <label class="switch-label">使用自定义端点/代理</label>
            <el-switch 
              v-model="currentConfig.useCustomEndpoint"
              @change="handleCustomEndpointChange"
              :disabled="loading"
            />
          </div>
        </div>
        
        <!-- 自定义端点输入（当开关打开时显示） -->
        <div class="form-group" v-if="currentConfig.useCustomEndpoint">
          <label class="form-label">
            Base URL <span class="required-mark">*</span>
          </label>
          <el-input
            v-model="currentConfig.base_url"
            placeholder="例如：https://api.speeedai.com/v1beta"
            :disabled="loading"
            @blur="validateCurrentConfig"
            class="base-url-input"
          >
            <template #prefix>
              <el-icon><Link /></el-icon>
            </template>
          </el-input>
          <p class="form-hint">
            推荐使用 <a href="https://speeedai.com" target="_blank" class="recommend-link">SpeeedAI</a>
          </p>
          <p class="error-hint" v-if="currentErrors.base_url">{{ currentErrors.base_url }}</p>
        </div>
        
        <!-- 自定义模型名称输入（当使用自定义端点时显示） -->
        <div class="form-group" v-if="currentConfig.useCustomEndpoint">
          <label class="form-label">
            自定义模型名称（可选）
          </label>
          <el-input
            v-model="currentConfig.custom_model_name"
            :placeholder="`例如：${selectedModel === 'gemini' ? 'gemini-2.5-flash-image' : 'doubao-seedream-4-0-250828'}`"
            :disabled="loading"
            class="custom-model-input"
          >
            <template #prefix>
              <el-icon><Setting /></el-icon>
            </template>
          </el-input>
          <p class="form-hint">
            如果您的代理服务使用非标准模型名称，请在此填写。留空则使用标准模型名称。
          </p>
        </div>
      </div>
      
      <!-- 错误提示 -->
      <div class="error-message" v-if="errorMessage">
        <el-icon><WarningFilled /></el-icon>
        <span>{{ errorMessage }}</span>
      </div>
    </div>
    
    <template #footer>
      <el-button 
        v-if="!required" 
        @click="handleCancel" 
        :disabled="loading"
      >
        取消
      </el-button>
      <el-button 
        type="primary" 
        @click="handleConfirm" 
        :loading="loading"
        :disabled="!canSave"
      >
        保存配置
      </el-button>
    </template>
  </el-dialog>
</template>

<script>
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled, Check, WarningFilled, Warning, Lock, Link, Setting } from '@element-plus/icons-vue'
import { 
  getApiConfig, 
  saveApiConfig, 
  isApiConfigured, 
  validateApiConfig 
} from '../utils/apiConfig'

export default {
  name: 'ApiConfigDialog',
  components: {
    InfoFilled,
    Check,
    WarningFilled,
    Warning,
    Lock,
    Link,
    Setting
  },
  props: {
    modelValue: {
      type: Boolean,
      default: false
    },
    required: {
      type: Boolean,
      default: false
    },
    highlightApiType: {
      type: String,
      default: null
    }
  },
  emits: ['update:modelValue', 'confirmed'],
  setup(props, { emit }) {
    const visible = ref(props.modelValue)
    const loading = ref(false)
    const errorMessage = ref('')
    const selectedModel = ref('gemini') // 'gemini' 或 'doubao'
    
    // 当前配置
    const currentConfig = ref({
      api_key: '',
      base_url: '',
      useCustomEndpoint: false,
      type: 'official'
    })
    
    const currentErrors = ref({
      api_key: '',
      base_url: ''
    })
    
    // 监听外部传入的modelValue变化
    watch(() => props.modelValue, (newVal) => {
      visible.value = newVal
      if (newVal) {
        // 如果有高亮的API类型，自动选择对应的模型
        if (props.highlightApiType) {
          selectedModel.value = props.highlightApiType
        } else {
          // 如果没有高亮，默认选择第一个已配置的模型，否则选择gemini
          const geminiConfigured = isApiConfigured('gemini')
          const doubaoConfigured = isApiConfigured('doubao')
          if (geminiConfigured && !doubaoConfigured) {
            selectedModel.value = 'gemini'
          } else if (doubaoConfigured && !geminiConfigured) {
            selectedModel.value = 'doubao'
          } else if (!geminiConfigured && !doubaoConfigured) {
            // 都没有配置，默认选择gemini
            selectedModel.value = 'gemini'
          }
        }
        loadConfigs()
        errorMessage.value = ''
      }
    })
    
    // 监听高亮API类型变化
    watch(() => props.highlightApiType, (newVal) => {
      if (newVal && visible.value) {
        selectedModel.value = newVal
        loadCurrentConfig()
      }
    })
    
    // 监听内部visible变化，同步到外部
    watch(visible, (newVal) => {
      emit('update:modelValue', newVal)
    })
    
    // 监听模型切换
    watch(selectedModel, () => {
      loadCurrentConfig()
    })
    
    // 加载配置
    const loadConfigs = () => {
      loadCurrentConfig()
    }
    
    // 加载当前选中模型的配置
    const loadCurrentConfig = () => {
      const config = getApiConfig(selectedModel.value)
      if (config) {
        currentConfig.value = {
          api_key: config.api_key || '',
          base_url: config.base_url || '',
          useCustomEndpoint: !!(config.base_url && config.base_url.trim()),
          custom_model_name: config.custom_model_name || '',
          type: config.type || 'official'
        }
      } else {
        // 兼容旧格式
        const oldKey = localStorage.getItem(`${selectedModel.value}_api_key`)
        const oldUrl = localStorage.getItem(`${selectedModel.value}_base_url`)
        if (oldKey || oldUrl) {
          currentConfig.value = {
            api_key: oldKey || '',
            base_url: oldUrl || '',
            useCustomEndpoint: !!(oldUrl && oldUrl.trim()),
            custom_model_name: '',
            type: oldUrl ? 'third_party' : 'official'
          }
        } else {
          currentConfig.value = {
            api_key: '',
            base_url: '',
            useCustomEndpoint: false,
            custom_model_name: '',
            type: 'official'
          }
        }
      }
      currentErrors.value = { api_key: '', base_url: '' }
    }
    
    // 处理自定义端点开关变化
    const handleCustomEndpointChange = (value) => {
      if (!value) {
        // 关闭时清空base_url
        currentConfig.value.base_url = ''
        currentConfig.value.type = 'official'
      } else {
        currentConfig.value.type = 'third_party'
      }
      validateCurrentConfig()
    }
    
    // 验证当前配置
    const validateCurrentConfig = () => {
      const configToValidate = {
        type: currentConfig.value.useCustomEndpoint ? 'third_party' : 'official',
        api_key: currentConfig.value.api_key,
        base_url: currentConfig.value.base_url
      }
      
      const result = validateApiConfig(selectedModel.value, configToValidate)
      if (!result.valid) {
        if (configToValidate.type === 'official') {
          currentErrors.value.api_key = result.error
          currentErrors.value.base_url = ''
        } else {
          if (result.error.includes('Base URL')) {
            currentErrors.value.base_url = result.error
            currentErrors.value.api_key = ''
          } else {
            currentErrors.value.api_key = result.error
            currentErrors.value.base_url = ''
          }
        }
      } else {
        currentErrors.value = { api_key: '', base_url: '' }
      }
    }
    
    // 检查是否可以保存
    const canSave = computed(() => {
      const configToValidate = {
        type: currentConfig.value.useCustomEndpoint ? 'third_party' : 'official',
        api_key: currentConfig.value.api_key,
        base_url: currentConfig.value.base_url
      }
      return validateApiConfig(selectedModel.value, configToValidate).valid
    })
    
    // 处理对话框关闭前
    const handleBeforeClose = (done) => {
      if (props.required) {
        // 首次使用模式，不允许关闭
        ElMessage.warning('请先配置 API 才能继续使用')
        return
      }
      done()
    }
    
    const handleCancel = () => {
      visible.value = false
    }
    
    const handleConfirm = async () => {
      errorMessage.value = ''
      
      // 验证配置
      validateCurrentConfig()
      
      if (!canSave.value) {
        errorMessage.value = '请填写完整的配置信息'
        return
      }
      
      loading.value = true
      
      try {
        // 保存当前模型的配置
        const configToSave = {
          type: currentConfig.value.useCustomEndpoint ? 'third_party' : 'official',
          api_key: currentConfig.value.api_key.trim(),
          base_url: currentConfig.value.useCustomEndpoint ? currentConfig.value.base_url.trim() : '',
          custom_model_name: currentConfig.value.useCustomEndpoint && currentConfig.value.custom_model_name 
            ? currentConfig.value.custom_model_name.trim() : '',
          configured: true
        }
        saveApiConfig(selectedModel.value, configToSave)
        
        // 同时保存到旧格式（兼容性）
        if (configToSave.api_key) {
          localStorage.setItem(`${selectedModel.value}_api_key`, configToSave.api_key)
        } else {
          localStorage.removeItem(`${selectedModel.value}_api_key`)
        }
        if (configToSave.base_url) {
          localStorage.setItem(`${selectedModel.value}_base_url`, configToSave.base_url)
        } else {
          localStorage.removeItem(`${selectedModel.value}_base_url`)
        }
        
        // 触发确认事件（保持兼容格式）
        const eventData = {}
        if (selectedModel.value === 'gemini') {
          eventData.geminiApiKey = configToSave.api_key || null
          eventData.geminiBaseUrl = configToSave.base_url || null
        } else if (selectedModel.value === 'doubao') {
          eventData.doubaoApiKey = configToSave.api_key || null
          eventData.doubaoBaseUrl = configToSave.base_url || null
        }
        
        // 延迟一下再关闭，让父组件有时间处理
        setTimeout(() => {
          visible.value = false
          loading.value = false
          ElMessage.success('API 配置已保存')
          // 在关闭后触发确认事件，确保父组件能正确更新
          emit('confirmed', eventData)
        }, 100)
        
      } catch (error) {
        console.error('保存API配置失败:', error)
        errorMessage.value = '保存失败，请重试'
        loading.value = false
      }
    }
    
    return {
      visible,
      selectedModel,
      currentConfig,
      currentErrors,
      loading,
      errorMessage,
      canSave,
      handleCustomEndpointChange,
      handleBeforeClose,
      handleCancel,
      handleConfirm,
      validateCurrentConfig
    }
  }
}
</script>

<style scoped>
.api-config-dialog :deep(.el-dialog__header) {
  padding: 24px 24px 8px;
  border-bottom: none;
}

.api-config-dialog :deep(.el-dialog__title) {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
}

.api-config-dialog :deep(.el-dialog__body) {
  padding: 0 24px 24px;
}

.api-config-dialog :deep(.el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid #f0f0f0;
}

.api-config-content {
  padding: 0;
}

.subtitle {
  margin: 0 0 24px 0;
  font-size: 14px;
  color: #666;
}

.section {
  margin-bottom: 32px;
}

.section:last-child {
  margin-bottom: 0;
}

.section-title {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
}

.section-hint {
  margin: 0 0 20px 0;
  font-size: 14px;
  color: #666;
}

/* 模型卡片 */
.model-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 8px;
}

.model-card {
  position: relative;
  padding: 16px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
}

.model-card:hover {
  border-color: #d1d5db;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.model-card.selected {
  border-color: #667eea;
  background: #f8f9ff;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.model-card-check {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 20px;
  height: 20px;
  background: #667eea;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 12px;
}

.model-card-title {
  margin: 0 0 6px 0;
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
}

.model-card-desc {
  margin: 0;
  font-size: 12px;
  color: #666;
  line-height: 1.4;
}

/* 表单 */
.form-group {
  margin-bottom: 20px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 8px;
}

.required-mark {
  color: #dc2626;
  margin-left: 2px;
}

.api-key-input :deep(.el-input__wrapper) {
  padding: 12px 16px;
}

.api-key-input :deep(.el-input__prefix) {
  color: #9ca3af;
}

/* 统一输入框尺寸 */
:deep(.el-input__wrapper) {
  padding: 12px 16px;
  min-height: 40px;
}

:deep(.el-input__inner) {
  font-size: 14px;
}

.switch-group {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.switch-label {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}

.form-hint {
  margin: 8px 0 0 0;
  font-size: 12px;
  color: #6b7280;
}

.recommend-link {
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
}

.recommend-link:hover {
  color: #5568d3;
  text-decoration: underline;
}

.error-hint {
  margin: 8px 0 0 0;
  font-size: 12px;
  color: #dc2626;
}

.error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #dc2626;
  font-size: 14px;
  margin-top: 20px;
}

.error-message .el-icon {
  font-size: 16px;
}

/* 响应式 */
@media (max-width: 768px) {
  .model-cards {
    grid-template-columns: 1fr;
  }
}
</style>
