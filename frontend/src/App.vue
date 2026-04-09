<template>
  <div id="app">
    <!-- API配置对话框 -->
    <ApiConfigDialog 
      v-model="showApiConfigDialog" 
      :required="isFirstTime"
      :highlight-api-type="highlightApiType"
      @confirmed="handleApiConfigConfirmed"
    />
    
    <div class="app-container">
      <div class="main-content">
        <!-- 左侧操作面板 -->
        <div class="left-panel">
          <div class="panel-content">
            <!-- 顶部标题区域 -->
            <div class="header-section">
              <div class="title-row">
                <div class="logo-icon">
                  <div class="icon-stack">
                    <div class="icon-layer"></div>
                    <div class="icon-layer"></div>
                    <div class="icon-layer"></div>
                  </div>
                </div>
                <h1 class="app-title">BatchGen Pro</h1>
                <p class="app-subtitle">批量图片生成工具</p>
              </div>
              
              <!-- 标签切换 -->
              <div class="tab-switcher">
                <div class="tab-item" :class="{ active: activeTab === 'generate' }" @click="activeTab = 'generate'">
                  <span>批量生图</span>
                </div>
                <div class="tab-item" :class="{ active: activeTab === 'edit' }" @click="activeTab = 'edit'">
                  <span>批量改图</span>
                </div>
                <div class="tab-item" :class="{ active: activeTab === 'video' }" @click="activeTab = 'video'">
                  <span>视频生成</span>
                </div>
              </div>

              <p class="tab-description">
                {{ activeTabDescription }}
              </p>
            </div>
            
              <!-- 操作区域 -->
            <div class="operation-section">
              <!-- 大模型选择器（图片生成时显示） -->
              <div class="form-group" v-if="activeTab !== 'video'">
                <div class="model-selector-header">
                  <label class="form-label">大模型</label>
                  <el-button 
                    type="text" 
                    class="api-config-link"
                    @click="showApiConfigDialog = true"
                  >
                    <el-icon><Setting /></el-icon>
                    API Key 配置
                  </el-button>
                </div>
                <el-select 
                  v-model="selectedModel" 
                  class="model-selector"
                  placeholder="选择模型"
                  @change="handleModelChange"
                >
                  <el-option
                    v-for="model in availableModels"
                    :key="model.value"
                    :label="model.label"
                    :value="model.value"
                    :disabled="model.disabled"
                  >
                    <div class="model-option">
                      <span>{{ model.label }}</span>
                      <span class="model-status" :class="model.statusClass">
                        <el-icon v-if="model.statusIcon"><component :is="model.statusIcon" /></el-icon>
                        <span>{{ model.statusText }}</span>
                      </span>
                    </div>
                  </el-option>
                </el-select>
              </div>
              
              <!-- Prompt输入（仅在批量生图和批量改图时显示） -->
              <div class="form-group" v-if="activeTab !== 'video'">
                <label class="form-label">Prompt</label>
                <el-input
                  v-model="batchPrompt"
                  type="textarea"
                  :rows="3"
                  :placeholder="activeTab === 'generate' ? '输入提示词，使用 {变量名} 来定义变量（仅支持一个变量），例如：生成一张{动物}的图片' : '输入提示词'"
                  class="prompt-input"
                  @input="activeTab === 'generate' ? handlePromptChange() : null"
                />
              </div>
              
              <!-- 批量生图：参考图片上传（单图） + 数量选择 -->
              <template v-if="activeTab === 'generate'">
                <div class="form-group">
                  <div class="upload-header">
                    <label class="form-label">参考图片（可选）</label>
                    <el-icon class="clear-icon" @click="clearReferenceImage"><RefreshLeft /></el-icon>
                  </div>
                  
                  <el-upload
                    class="reference-upload"
                    :auto-upload="false"
                    :limit="1"
                    :on-change="handleReferenceImageChange"
                    :on-remove="handleReferenceImageRemove"
                    :file-list="referenceImageList"
                    accept="image/*"
                    list-type="picture-card"
                  >
                    <el-icon><Plus /></el-icon>
                  </el-upload>
                </div>
                
                <!-- 变量检测和输入 -->
                <div v-if="detectedVariables.length > 0" class="form-group variable-section">
                  <div class="variable-header">
                    <label class="form-label">✨ 检测到变量: {{'{'}}{{ detectedVariables[0] }}{{'}'}}</label>
                  </div>
                  
                  <div class="variable-input-group">
                    <label class="variable-label">{{'{'}}{{ detectedVariables[0] }}{{'}'}}</label>
                    <el-input
                      v-model="variableValues[detectedVariables[0]]"
                      type="textarea"
                      :rows="3"
                      :placeholder="`每行一个值，例如：\n鸭子\n兔子\n老虎`"
                      class="variable-textarea"
                      @input="updateVariableCount"
                    />
                    <span class="variable-count">{{ getVariableValueCount(detectedVariables[0]) }} 个值</span>
                  </div>
                </div>
                
                <div class="form-group">
                  <label class="form-label">生成数量</label>
                  <el-input-number 
                    v-model="imageCount" 
                    :min="1" 
                    :max="10" 
                    class="count-selector"
                    :disabled="hasVariables"
                  />
                  <span class="count-hint" v-if="!hasVariables">最多生成10张</span>
                  <span class="count-hint" v-else>使用变量时，数量由变量值决定（当前: {{ totalVariableCombinations }} 个）</span>
                </div>
              </template>
              
              <!-- 批量改图：参考图片上传（多图） -->
              <template v-if="activeTab === 'edit'">
                <div class="form-group">
                  <div class="upload-header">
                    <label class="form-label">参考图片</label>
                    <el-icon class="clear-icon" @click="clearAllImages"><RefreshLeft /></el-icon>
                  </div>

                  <MultiImageUpload
                    v-model:files="uploadedFiles"
                    @files-change="handleBatchFileChange"
                  />
                </div>
              </template>

              <!-- 视频生成 -->
              <template v-if="activeTab === 'video'">
                <!-- 大模型选择器 -->
                <div class="form-group">
                  <div class="model-selector-header">
                    <label class="form-label">大模型</label>
                    <el-button
                      type="text"
                      class="api-config-link"
                      @click="showApiConfigDialog = true"
                    >
                      <el-icon><Setting /></el-icon>
                      API Key 配置
                    </el-button>
                  </div>
                  <el-select
                    v-model="selectedVideoModel"
                    class="model-selector"
                    placeholder="选择视频模型"
                    @change="handleVideoModelChange"
                  >
                    <el-option
                      v-for="model in availableVideoModels"
                      :key="model.value"
                      :label="model.label"
                      :value="model.value"
                      :disabled="model.disabled"
                    >
                      <div class="model-option">
                        <span>{{ model.label }}</span>
                        <span class="model-status" :class="model.statusClass">
                          <el-icon v-if="model.statusIcon"><component :is="model.statusIcon" /></el-icon>
                          <span>{{ model.statusText }}</span>
                        </span>
                      </div>
                    </el-option>
                  </el-select>
                </div>

                <div class="form-group">
                  <label class="form-label">生成模式</label>
                  <el-select
                    v-model="videoMode"
                    class="model-selector"
                    placeholder="选择视频生成模式"
                  >
                    <el-option label="文生视频" value="text" />
                    <el-option label="首帧生视频" value="first_frame" />
                    <el-option label="首尾帧生视频" value="first_last_frame" />
                    <el-option label="多模态参考（含视频编辑/延长）" value="multimodal" />
                  </el-select>
                </div>

                <div class="form-group">
                  <label class="form-label">视频描述 Prompt</label>
                  <el-input
                    v-model="videoPrompt"
                    type="textarea"
                    :rows="4"
                    :placeholder="videoPromptPlaceholder"
                    class="prompt-input"
                  />
                </div>

                <div v-if="videoMode === 'first_frame'" class="form-group">
                  <div class="upload-header">
                    <label class="form-label">首帧图片</label>
                    <el-icon class="clear-icon" @click="clearVideoFirstFrame"><RefreshLeft /></el-icon>
                  </div>

                  <MultiImageUpload
                    :files="videoFirstFrameFiles"
                    accept="image/*"
                    upload-text="Upload First Frame"
                    preview-mode="image"
                    :max-count="1"
                    @files-change="handleVideoFirstFrameFilesChange"
                  />
                </div>

                <template v-if="videoMode === 'first_last_frame'">
                  <div class="form-group">
                    <div class="upload-header">
                      <label class="form-label">首帧图片</label>
                      <el-icon class="clear-icon" @click="clearVideoFirstFrame"><RefreshLeft /></el-icon>
                    </div>

                    <MultiImageUpload
                      :files="videoFirstFrameFiles"
                      accept="image/*"
                      upload-text="Upload First Frame"
                      preview-mode="image"
                      :max-count="1"
                      @files-change="handleVideoFirstFrameFilesChange"
                    />
                  </div>

                  <div class="form-group">
                    <div class="upload-header">
                      <label class="form-label">尾帧图片</label>
                      <el-icon class="clear-icon" @click="clearVideoLastFrame"><RefreshLeft /></el-icon>
                    </div>

                    <MultiImageUpload
                      :files="videoLastFrameFiles"
                      accept="image/*"
                      upload-text="Upload Last Frame"
                      preview-mode="image"
                      :max-count="1"
                      @files-change="handleVideoLastFrameFilesChange"
                    />
                  </div>
                </template>

                <template v-if="videoMode === 'multimodal'">
                  <div class="form-group">
                    <div class="upload-header">
                      <label class="form-label">参考图片（0-9）</label>
                      <el-icon class="clear-icon" @click="clearVideoReferenceImages"><RefreshLeft /></el-icon>
                    </div>

                    <MultiImageUpload
                      :files="videoReferenceFiles"
                      accept="image/*"
                      upload-text="Upload Reference Images"
                      preview-mode="image"
                      :max-count="9"
                      @files-change="handleVideoReferenceFilesChange"
                    />
                  </div>

                  <div class="form-group">
                    <div class="upload-header">
                      <label class="form-label">参考视频（0-3）</label>
                      <el-icon class="clear-icon" @click="clearVideoReferenceVideos"><RefreshLeft /></el-icon>
                    </div>

                    <MultiImageUpload
                      :files="videoReferenceVideoFiles"
                      accept="video/mp4,video/quicktime"
                      upload-text="Upload Reference Videos"
                      preview-mode="video"
                      :max-count="3"
                      @files-change="handleVideoReferenceVideoFilesChange"
                    />
                  </div>

                  <div class="form-group">
                    <div class="upload-header">
                      <label class="form-label">参考音频（0-3）</label>
                      <el-icon class="clear-icon" @click="clearVideoReferenceAudios"><RefreshLeft /></el-icon>
                    </div>

                    <MultiImageUpload
                      :files="videoReferenceAudioFiles"
                      accept="audio/mpeg,audio/mp3,audio/wav"
                      upload-text="Upload Reference Audios"
                      preview-mode="file"
                      :max-count="3"
                      @files-change="handleVideoReferenceAudioFilesChange"
                    />
                  </div>
                </template>

                <div class="form-group">
                  <label class="form-label">输出参数</label>
                  <div class="video-options-grid">
                    <el-select v-model="videoSettings.resolution" placeholder="分辨率">
                      <el-option label="480p" value="480p" />
                      <el-option label="720p" value="720p" />
                    </el-select>
                    <el-select v-model="videoSettings.ratio" placeholder="宽高比">
                      <el-option label="adaptive" value="adaptive" />
                      <el-option label="16:9" value="16:9" />
                      <el-option label="4:3" value="4:3" />
                      <el-option label="1:1" value="1:1" />
                      <el-option label="3:4" value="3:4" />
                      <el-option label="9:16" value="9:16" />
                      <el-option label="21:9" value="21:9" />
                    </el-select>
                    <el-select v-model="videoSettings.duration" placeholder="时长">
                      <el-option label="自动 (-1)" :value="-1" />
                      <el-option
                        v-for="seconds in videoDurationOptions"
                        :key="seconds"
                        :label="`${seconds} 秒`"
                        :value="seconds"
                      />
                    </el-select>
                    <el-input-number
                      v-model="videoSettings.seed"
                      :min="-1"
                      :max="4294967295"
                      :step="1"
                      controls-position="right"
                    />
                  </div>
                  <div class="video-option-switches">
                    <el-switch v-model="videoSettings.generateAudio" active-text="生成有声视频" />
                    <el-switch v-model="videoSettings.watermark" active-text="添加水印" />
                  </div>
                </div>
              </template>
            </div>
            
            <!-- 开始按钮 -->
            <div class="start-button-container">
              <el-button 
                type="primary" 
                class="start-button"
                :loading="isBatchGenerating"
                @click="handleStartTask"
                :disabled="isStartButtonDisabled"
              >
                开始
              </el-button>
            </div>
          </div>
        </div>
        
        <!-- 分隔线 -->
        <div class="divider"></div>
        
        <!-- 右侧结果面板 -->
        <div class="right-panel">
          <BatchTaskManager ref="taskManagerRef" />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowDown, RefreshLeft, Plus, Setting, Check, Warning } from '@element-plus/icons-vue'

// 图标组件映射
const iconComponents = {
  Check,
  Warning
}
import axios from 'axios'
import MultiImageUpload from './components/MultiImageUpload.vue'
import BatchTaskManager from './components/BatchTaskManager.vue'
import ApiConfigDialog from './components/ApiConfigDialog.vue'
import {
  isApiConfigInitialized,
  migrateOldDataFormat,
  getApiConfig,
  isApiConfigured,
  getAvailableModels,
  getApiTypeFromModel,
  getApiKey as getApiKeyUtil,
  getBaseUrl as getBaseUrlUtil,
  getCustomModelName
} from './utils/apiConfig'
import {
  extractApiType,
  isConfiguredApiKey,
  shouldAttachApiKey
} from './utils/requestAuth'

// —— session id 隔离 ——
function getOrCreateSessionId() {
  let sessionId = localStorage.getItem('session_id')
  if (!sessionId) {
    if (window.crypto && window.crypto.randomUUID) {
      sessionId = window.crypto.randomUUID()
    } else {
      sessionId = Math.random().toString(36).substring(2) + Date.now().toString(36)
    }
    localStorage.setItem('session_id', sessionId)
  }
  return sessionId
}

const sessionId = getOrCreateSessionId()
axios.defaults.headers.common['X-Session-ID'] = sessionId

// API key管理函数（兼容新旧格式）
// 注意：现在必须使用用户自己的API key，不再使用服务器配置
function getApiKey(apiType) {
  // 优先使用新格式
  const key = getApiKeyUtil(apiType)
  if (key && key.trim() && 
      key.trim() !== 'your_gemini_api_key_here' && 
      key.trim() !== 'your_doubao_api_key_here' &&
      key.trim() !== 'your_sora_api_key_here') {
    return key.trim()
  }
  
  // 兼容旧格式
  let oldKey = null
  if (apiType === 'gemini') {
    oldKey = localStorage.getItem('gemini_api_key')
  } else if (apiType === 'doubao') {
    oldKey = localStorage.getItem('doubao_api_key')
  } else if (apiType === 'sora') {
    oldKey = localStorage.getItem('sora_api_key')
  }
  // 如果key是空字符串、null或占位符，返回null（不再使用服务器配置）
  if (!oldKey || !oldKey.trim() || 
      oldKey.trim() === 'your_gemini_api_key_here' || 
      oldKey.trim() === 'your_doubao_api_key_here' ||
      oldKey.trim() === 'your_sora_api_key_here') {
    return null
  }
  return oldKey.trim()
}

// Base URL管理函数（兼容新旧格式）
function getBaseUrl(apiType) {
  // 优先使用新格式
  const url = getBaseUrlUtil(apiType)
  if (url) return url
  
  // 兼容旧格式
  let oldUrl = null
  if (apiType === 'gemini') {
    oldUrl = localStorage.getItem('gemini_base_url')
  } else if (apiType === 'doubao') {
    oldUrl = localStorage.getItem('doubao_base_url')
  } else if (apiType === 'sora') {
    oldUrl = localStorage.getItem('sora_base_url')
  }
  // 如果base_url是空字符串或null，返回null
  if (!oldUrl || !oldUrl.trim()) {
    return null
  }
  return oldUrl.trim()
}

// 拦截器：添加Session ID、API Key 和 Auth Token
axios.interceptors.request.use(config => {
  config.headers['X-Session-ID'] = sessionId
  
  // 已移除认证体系，不再添加 Authorization header
  
  const apiType = extractApiType(config)
  if (!shouldAttachApiKey(config)) {
    return config
  }
  
  console.log('[API Debug] apiType:', apiType)
  
  const apiKey = getApiKey(apiType)
  console.log('[API Debug] apiKey for', apiType, ':', apiKey ? '存在' : '不存在')
  
  // 必须提供API key，不再使用服务器配置
  if (!isConfiguredApiKey(apiKey)) {
    const apiName = apiType === 'gemini' ? 'Gemini' : apiType === 'sora' ? 'Sora' : '豆包'
    console.error(`[API Debug] ${apiName} API Key 未配置或无效`)
    ElMessage.error(`请先配置 ${apiName} API Key 才能使用`)
    return Promise.reject(new Error(`${apiName} API Key 未配置`))
  }
  config.headers['X-API-Key'] = apiKey.trim()
  config.headers['X-API-Type'] = apiType

  // 添加 base_url（如果存在）
  const baseUrl = getBaseUrl(apiType)
  if (baseUrl) {
    if (apiType === 'gemini') {
      config.headers['X-Gemini-Base-URL'] = baseUrl
    } else if (apiType === 'doubao') {
      config.headers['X-Doubao-Base-URL'] = baseUrl
    } else if (apiType === 'sora') {
      config.headers['X-Sora-Base-URL'] = baseUrl
    }
  }

  // 如果是 FormData，也添加 base_url 到 formData
  if (config.data instanceof FormData && baseUrl) {
    if (apiType === 'gemini') {
      config.data.append('gemini_base_url', baseUrl)
    } else if (apiType === 'doubao') {
      config.data.append('doubao_base_url', baseUrl)
    } else if (apiType === 'sora') {
      config.data.append('sora_base_url', baseUrl)
    }
  }
  
  return config
})

// 响应拦截器：处理API key和认证相关的错误
axios.interceptors.response.use(
  response => response,
  error => {
    // 处理401错误（未登录或token过期）
    if (error.response && error.response.status === 401) {
      const errorMsg = error.response.data?.error || error.response.data?.message || ''
      if (errorMsg.includes('token') || errorMsg.includes('登录') || errorMsg.includes('认证')) {
        // 清除本地认证信息
        // 已移除认证体系
        ElMessage.warning('登录已过期，请重新登录')
        // 可以触发登录对话框，但这里先不自动打开，让用户手动点击
      }
    }
    
    // 已移除积分体系
    if (error.response && error.response.status === 402) {
      const errorMsg = error.response.data?.error || '积分不足'
      ElMessage.error(errorMsg)
    }
    
    // 处理400错误（可能是API key问题）
    if (error.response && error.response.status === 400) {
      const errorMsg = error.response.data?.error || error.response.data?.message || ''
      if (errorMsg.includes('API key not valid') || errorMsg.includes('API_KEY_INVALID') || errorMsg.includes('API Key')) {
        // 清除可能无效的localStorage中的key
        const apiType = error.config?.headers?.['X-API-Type'] || 'gemini'
        const keyName = apiType === 'gemini' ? 'gemini_api_key' : 'doubao_api_key'
        const storedKey = localStorage.getItem(keyName)
        if (storedKey && (storedKey.trim() === '' || storedKey.includes('your_'))) {
          localStorage.removeItem(keyName)
        }
        ElMessage.error('API Key 无效，已清除本地配置，将使用服务器配置的key。请刷新页面重试。')
      }
    }
    // 如果是403错误，可能是API key问题
    if (error.response && error.response.status === 403) {
      const errorMsg = error.response.data?.error || error.response.data?.message || 'API Key 验证失败'
      if (errorMsg.includes('API Key') || errorMsg.includes('api_key') || errorMsg.includes('未提供')) {
        ElMessage.error('API Key 无效或未配置，请检查配置')
      }
    }
    return Promise.reject(error)
  }
)

export default {
  name: 'App',
  components: {
    MultiImageUpload,
    BatchTaskManager,
    ApiConfigDialog,
    ArrowDown,
    RefreshLeft,
    Plus,
    Setting
  },
  setup() {
    const taskManagerRef = ref(null)
    
    // API配置相关状态
    const showApiConfigDialog = ref(false)
    const isFirstTime = ref(false)
    const highlightApiType = ref(null)
    const apiConfigVersion = ref(0) // 用于触发计算属性更新
    
    // 认证相关状态
    // 注意：已移除用户认证和积分体系，用户只需提供自己的 API Key 即可使用
    
    // 批量改图相关状态
    const uploadedFiles = ref([])
    
    // 批量生图相关状态
    const referenceImage = ref(null)
    const referenceImageList = ref([])
    const imageCount = ref(3) // 默认生成3张
    
    // 变量功能相关状态
    const detectedVariables = ref([])  // 检测到的变量名列表
    const variableValues = ref({})     // 变量值对象 { "动物": "鸭子\n兔子\n老虎" }
    
    // 通用状态
    const batchPrompt = ref('')
    const isBatchGenerating = ref(false)
    const selectedApi = ref('gemini') // 默认使用Gemini
    const activeTab = ref('generate') // 默认选中批量生图
    const selectedModel = ref('gemini-2.5-flash-image') // 默认模型
    
    // 图片模型列表
    const imageModelsList = [
      {
        value: 'gemini-2.5-flash-image',
        label: 'Gemini 2.5 Flash Image',
        apiType: 'gemini'
      },
      {
        value: 'gemini-3-pro-image-preview',
        label: 'Gemini 3 Pro Image Preview',
        apiType: 'gemini'
      },
      {
        value: 'doubao-seedream-4-0-250828',
        label: '豆包 Seedream 4.0',
        apiType: 'doubao'
      }
    ]

    // 视频模型列表
    const videoModelsList = [
      {
        value: 'doubao-seedance-2-0-260128',
        label: '豆包 Seedance 2.0',
        apiType: 'doubao'
      },
      {
        value: 'doubao-seedance-2-0-fast-260128',
        label: '豆包 Seedance 2.0 Fast',
        apiType: 'doubao'
      }
    ]

    // 视频生成相关状态
    const videoReferenceFiles = ref([])
    const videoReferenceVideoFiles = ref([])
    const videoReferenceAudioFiles = ref([])
    const videoFirstFrameFiles = ref([])
    const videoLastFrameFiles = ref([])
    const videoPrompt = ref('')
    const videoMode = ref('text')
    const selectedVideoModel = ref('doubao-seedance-2-0-260128')
    const videoSettings = ref({
      resolution: '720p',
      ratio: 'adaptive',
      duration: 5,
      seed: -1,
      watermark: false,
      generateAudio: true
    })
    const videoDurationOptions = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    
    // 可用图片模型列表（计算属性，根据已配置API动态过滤）
    const availableImageModels = computed(() => {
      // 依赖 apiConfigVersion 来触发更新
      apiConfigVersion.value // 读取以建立依赖
      return imageModelsList.map(model => {
        const configured = isApiConfigured(model.apiType)
        return {
          ...model,
          disabled: !configured,
          statusClass: configured ? 'status-configured' : 'status-not-configured',
          statusIcon: configured ? Check : Warning,
          statusText: configured ? '已配置' : '未配置'
        }
      })
    })

    // 可用视频模型列表（计算属性，根据已配置API动态过滤）
    const availableVideoModels = computed(() => {
      // 依赖 apiConfigVersion 来触发更新
      apiConfigVersion.value // 读取以建立依赖
      return videoModelsList.map(model => {
        const configured = isApiConfigured(model.apiType)
        return {
          ...model,
          disabled: !configured,
          statusClass: configured ? 'status-configured' : 'status-not-configured',
          statusIcon: configured ? Check : Warning,
          statusText: configured ? '已配置' : '未配置'
        }
      })
    })

    // 当前可用的模型列表（根据tab切换）
    const availableModels = computed(() => {
      if (activeTab.value === 'video') {
        return availableVideoModels.value
      }
      return availableImageModels.value
    })

    // Tab描述计算属性
    const activeTabDescription = computed(() => {
      switch (activeTab.value) {
        case 'generate':
          return '批量生图会用同一份提示词（可带参考图）重复生成多张图'
        case 'edit':
          return '批量改图会对多张图用同一份提示词来生图'
        case 'video':
          return '视频生成支持文生、首帧、首尾帧、多模态参考，以及参考视频驱动的视频编辑/延长'
        default:
          return ''
      }
    })

    const videoPromptPlaceholder = computed(() => {
      if (videoMode.value === 'text') {
        return '输入视频描述，例如：一只小猫在阳光下抬头眨眼，镜头轻微推进，真实摄影风格'
      }
      if (videoMode.value === 'multimodal') {
        return '可选。可结合 [图1] / [视频1] / [音频1] 描述参考素材的作用，用于编辑或延长视频'
      }
      return '可选。上传参考素材后，可用提示词进一步约束动作、镜头和风格'
    })

    // 计算属性：开始按钮是否禁用
    const isStartButtonDisabled = computed(() => {
      if (activeTab.value === 'video') {
        if (videoMode.value === 'text') {
          return !videoPrompt.value.trim()
        }
        if (videoMode.value === 'first_frame') {
          return videoFirstFrameFiles.value.length === 0
        }
        if (videoMode.value === 'first_last_frame') {
          return videoFirstFrameFiles.value.length === 0 || videoLastFrameFiles.value.length === 0
        }
        if (videoMode.value === 'multimodal') {
          const hasMedia = videoReferenceFiles.value.length > 0 ||
            videoReferenceVideoFiles.value.length > 0
          const hasAudioOnly = videoReferenceAudioFiles.value.length > 0 && !hasMedia
          if (hasAudioOnly) return true
          return !hasMedia && !videoPrompt.value.trim()
        }
        return false
      }
      if (!batchPrompt.value.trim()) return true

      if (activeTab.value === 'generate') {
        // 批量生图：只需要prompt，参考图可选
        return false
      } else {
        // 批量改图：需要上传的图片
        return uploadedFiles.value.length === 0
      }
    })

    // 处理批量改图文件变化
    const handleBatchFileChange = (files) => {
      uploadedFiles.value = files
    }

    // 视频生成参考图处理（多图）
    const handleVideoReferenceFilesChange = (files) => {
      videoReferenceFiles.value = files
    }

    const handleVideoReferenceVideoFilesChange = (files) => {
      videoReferenceVideoFiles.value = files
    }

    const handleVideoReferenceAudioFilesChange = (files) => {
      videoReferenceAudioFiles.value = files
    }

    const handleVideoFirstFrameFilesChange = (files) => {
      videoFirstFrameFiles.value = files
    }

    const handleVideoLastFrameFilesChange = (files) => {
      videoLastFrameFiles.value = files
    }

    const clearVideoReferenceImages = () => {
      videoReferenceFiles.value = []
      ElMessage.success('已清空所有参考图')
    }

    const clearVideoReferenceVideos = () => {
      videoReferenceVideoFiles.value = []
      ElMessage.success('已清空所有参考视频')
    }

    const clearVideoReferenceAudios = () => {
      videoReferenceAudioFiles.value = []
      ElMessage.success('已清空所有参考音频')
    }

    const clearVideoFirstFrame = () => {
      videoFirstFrameFiles.value = []
      ElMessage.success('已清空首帧图片')
    }

    const clearVideoLastFrame = () => {
      videoLastFrameFiles.value = []
      ElMessage.success('已清空尾帧图片')
    }

    // 处理批量生图参考图变化
    const handleReferenceImageChange = (file) => {
      referenceImage.value = file.raw
      referenceImageList.value = [file]
    }

    // 移除参考图
    const handleReferenceImageRemove = () => {
      referenceImage.value = null
      referenceImageList.value = []
    }

    // 清空所有批量改图的图片
    const clearAllImages = () => {
      uploadedFiles.value = []
      ElMessage.success('已清空所有图片')
    }

    // 清空批量生图的参考图
    const clearReferenceImage = () => {
      referenceImage.value = null
      referenceImageList.value = []
      ElMessage.success('已清空参考图')
    }

    // 根据模型名称获取API类型（使用工具函数）
    const getApiTypeFromModelName = (modelName) => {
      return getApiTypeFromModel(modelName)
    }
    
    // 检查 API Key 是否已配置
    const checkApiKeyConfigured = () => {
      const apiType = getApiTypeFromModelName(selectedModel.value)
      return isApiConfigured(apiType)
    }
    
    // 已移除积分相关代码
    const getCreditsPerImage = (modelName) => {
      // 已移除积分体系，此函数保留仅为兼容性
      return 0
      if (modelName === 'gemini-2.5-flash-image') {
        return 38
      } else if (modelName === 'gemini-3-pro-image-preview') {
        return 125
      } else if (modelName === 'doubao-seedream-4-0-250828') {
        return 38
      }
      
      return 38 // 默认值
    }

    // 变量相关函数
    // 检测Prompt中的变量
    const detectVariables = (prompt) => {
      const regex = /\{([^}]+)\}/g
      const matches = [...prompt.matchAll(regex)]
      const vars = matches.map(m => m[1].trim())
      return [...new Set(vars)]  // 去重
    }

    // 监听Prompt变化，自动检测变量
    const handlePromptChange = () => {
      if (activeTab.value === 'generate') {
        const vars = detectVariables(batchPrompt.value)
        // 只支持一个变量，取第一个
        detectedVariables.value = vars.length > 0 ? [vars[0]] : []
        
        // 为新检测到的变量初始化空值
        detectedVariables.value.forEach(varName => {
          if (!variableValues.value[varName]) {
            variableValues.value[varName] = ''
          }
        })
        
        // 移除不再存在的变量
        Object.keys(variableValues.value).forEach(key => {
          if (!detectedVariables.value.includes(key)) {
            delete variableValues.value[key]
          }
        })
      }
    }

    // 获取变量值列表（按行分割）
    const getVariableValuesList = (varName) => {
      const text = variableValues.value[varName] || ''
      return text.split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0)
    }

    // 获取变量值数量
    const getVariableValueCount = (varName) => {
      return getVariableValuesList(varName).length
    }

    // 更新变量数量（用于实时显示）
    const updateVariableCount = () => {
      // 触发视图更新
    }

    // 计算总的生成数量（变量组合）
    const totalVariableCombinations = computed(() => {
      if (detectedVariables.value.length === 0) {
        return imageCount.value
      }
      
      // 只支持单变量，直接返回第一个变量的值数量
      const varName = detectedVariables.value[0]
      const count = getVariableValueCount(varName)
      return Math.min(count, 10)  // 最多10个
    })

    // 是否有变量
    const hasVariables = computed(() => {
      return detectedVariables.value.length > 0 && 
             detectedVariables.value.some(v => getVariableValueCount(v) > 0)
    })
    
    // 检查API key（不再强制要求，可以使用服务器配置的）
    const checkApiKey = () => {
      // 不再强制要求API key，服务器有配置的fallback
      return true
    }
    
    // 处理API配置确认
    const handleApiConfigConfirmed = (config) => {
      // API key已保存到localStorage，无需额外处理
      isFirstTime.value = false
      highlightApiType.value = null
      
      // 触发计算属性更新
      apiConfigVersion.value++
      
      // 等待一下让localStorage更新完成
      setTimeout(() => {
        // 检查当前选择的模型是否仍然可用
        if (activeTab.value === 'video') {
          const videoApiType = getApiTypeFromModelName(selectedVideoModel.value)
          if (!isApiConfigured(videoApiType)) {
            const firstAvailableVideo = availableVideoModels.value.find(model => !model.disabled)
            if (firstAvailableVideo) {
              selectedVideoModel.value = firstAvailableVideo.value
            } else {
              ElMessage.warning('请至少配置一个视频模型 API 才能使用视频生成功能')
            }
          }
        } else {
          // 检查图片模型
          const apiType = getApiTypeFromModelName(selectedModel.value)
          if (!isApiConfigured(apiType)) {
            // 当前模型不可用，切换到第一个可用模型
            const firstAvailable = availableImageModels.value.find(m => !m.disabled)
            if (firstAvailable) {
              selectedModel.value = firstAvailable.value
              ElMessage.info(`已自动切换到 ${firstAvailable.label}`)
            } else {
              // 如果没有可用模型，提示用户
              ElMessage.warning('请至少配置一个 API 才能使用')
            }
          }
        }
      }, 100)
    }
    
    // 处理模型切换
    const handleModelChange = (modelValue) => {
      const apiType = getApiTypeFromModelName(modelValue)

      // 检查对应API是否已配置
      if (!isApiConfigured(apiType)) {
        // 未配置，显示提示并打开配置对话框
        ElMessage.warning(`请先配置 ${apiType === 'gemini' ? 'Gemini' : apiType === 'doubao' ? '豆包' : 'Sora'} API`)
        highlightApiType.value = apiType

        // 恢复之前的选择（在打开对话框之前）
        const previousModel = imageModelsList.find(m => {
          const prevApiType = getApiTypeFromModelName(m.value)
          return isApiConfigured(prevApiType) && m.value !== modelValue
        })
        if (previousModel) {
          selectedModel.value = previousModel.value
        }

        // 打开配置对话框
        showApiConfigDialog.value = true
      } else {
        highlightApiType.value = null
      }
    }

    // 处理视频模型切换
    const handleVideoModelChange = (modelValue) => {
      const apiType = getApiTypeFromModelName(modelValue)

      // 检查对应API是否已配置
      if (!isApiConfigured(apiType)) {
        const apiName = apiType === 'sora' ? 'Sora' : '豆包'
        ElMessage.warning(`请先配置 ${apiName} API`)
        highlightApiType.value = apiType
        const previousModel = videoModelsList.find(model => {
          return model.value !== modelValue && isApiConfigured(model.apiType)
        })
        if (previousModel) {
          selectedVideoModel.value = previousModel.value
        }

        showApiConfigDialog.value = true
      } else {
        highlightApiType.value = null
      }
    }

    // 生成所有变量组合的Prompt列表
    const generatePromptVariants = () => {
      if (detectedVariables.value.length === 0) {
        return [batchPrompt.value]
      }
      
      // 只支持单变量
      const varName = detectedVariables.value[0]
      const values = getVariableValuesList(varName)
      
      // 如果变量没有值，返回原始prompt
      if (values.length === 0) {
        return [batchPrompt.value]
      }
      
      // 替换变量生成prompt列表
      const prompts = values.map(value => {
        return batchPrompt.value.replace(new RegExp(`\\{${varName}\\}`, 'g'), value)
      }).slice(0, 10)  // 最多10个
      
      console.log('生成的prompt列表:', prompts)
      return prompts
    }

    // 创建并设置本地任务的公共方法
    const createAndSetLocalTask = (items, referenceImageUrl = null) => {
      const localTaskId = 'local_' + Date.now()
      const localTask = {
        task_id: localTaskId,
        status: 'processing',
        total_images: items.length,
        processed_images: 0,
        progress: 0,
        prompt: items[0]?.prompt || '',
        items: items,
        reference_image_url: referenceImageUrl
      }
      
      // 立即设置本地任务，让UI显示出来
      if (taskManagerRef.value && taskManagerRef.value.setLocalTask) {
        taskManagerRef.value.setLocalTask(localTask)
      }
      
      return localTask
    }

    // 统一的开始任务处理
    const handleStartTask = async () => {
      console.log('========== 点击开始按钮 ==========')
      console.log('activeTab:', activeTab.value)
      console.log('selectedModel:', selectedModel.value)
      console.log('batchPrompt:', batchPrompt.value)
      console.log('isBatchGenerating:', isBatchGenerating.value)

      if (activeTab.value === 'video') {
        await handleVideoGenerate()
        return
      }

      // 检查 API Key 是否已配置
      if (!checkApiKeyConfigured()) {
        ElMessage.warning('请先配置 API Key 后再生成图片')
        showApiConfigDialog.value = true
        return
      }

      // 计算图片数量
      const count = activeTab.value === 'generate'
        ? (hasVariables.value ? totalVariableCombinations.value : imageCount.value)
        : uploadedFiles.value.length

      if (activeTab.value === 'generate') {
        await handleBatchGenerate()
      } else {
        await handleBatchEdit()
      }

      // 已移除积分体系，无需刷新用户信息
    }

    // 批量生图处理
    const handleBatchGenerate = async () => {
      console.log('=== 开始批量生图 ===')
      console.log('selectedModel:', selectedModel.value)
      console.log('batchPrompt:', batchPrompt.value)
      console.log('imageCount:', imageCount.value)
      console.log('referenceImage:', referenceImage.value ? '有参考图' : '无参考图')
      
      if (!batchPrompt.value.trim()) {
        ElMessage.warning('请输入生成提示词')
        return
      }

      // 检查变量是否都有值
      if (hasVariables.value) {
        for (const varName of detectedVariables.value) {
          if (getVariableValueCount(varName) === 0) {
            ElMessage.warning(`请为变量 {${varName}} 输入至少一个值`)
            return
          }
        }
      }

      isBatchGenerating.value = true
      
      try {
        // 生成所有变量组合的prompt
        const promptVariants = generatePromptVariants()
        const actualCount = hasVariables.value ? promptVariants.length : imageCount.value
        
        if (actualCount > 10) {
          ElMessage.warning('生成数量超过10张，将只生成前10张')
        }
        
        // 如果有变量，使用新接口一次性提交所有prompt
        if (hasVariables.value) {
          console.log('变量模式，prompt变体:', promptVariants)
          const actualCount = Math.min(promptVariants.length, 10)
          const limitedVariants = promptVariants.slice(0, actualCount)
          console.log('将创建任务数:', actualCount)
          ElMessage.info(`检测到 ${limitedVariants.length} 个变量值，开始生成...`)
          
          // 先创建本地任务对象，立即显示给用户
          const referenceImageUrl = referenceImage.value ? URL.createObjectURL(referenceImage.value) : null
          const items = limitedVariants.map((prompt, index) => ({
            index: index,
            prompt: prompt,
            status: 'pending',
            reference_image_url: referenceImageUrl  // 所有item共享一个参考图
          }))
          createAndSetLocalTask(items, null)
          
          // 使用新接口，一次性提交所有prompt
          const formData = new FormData()
          
          // 添加参考图片（如果有）
          if (referenceImage.value) {
            formData.append('file', referenceImage.value)
          }
          
          // 添加所有prompt（JSON格式）
          formData.append('prompts', JSON.stringify(limitedVariants))
          const apiType = getApiTypeFromModelName(selectedModel.value)
          formData.append('api_type', apiType)
          const modelName = getCustomModelName(apiType, selectedModel.value)
          formData.append('model_name', modelName)
          
          const response = await axios.post('/api/batch/generate-with-prompts', formData, {
            headers: {
              'Content-Type': 'multipart/form-data'
            },
            timeout: 180000
          })
          
          if (response.data.success) {
            // 用后端返回的真实task_id更新本地任务
            if (taskManagerRef.value && taskManagerRef.value.updateLocalTaskId && response.data.task_id) {
              taskManagerRef.value.updateLocalTaskId(response.data.task_id)
            }
            // 显示积分扣除信息
            if (response.data.task_data?.credits_deducted) {
              ElMessage.success(`已扣除 ${response.data.task_data.credits_deducted} 积分，剩余 ${response.data.task_data.remaining_credits} 积分`)
            }
            // 刷新用户信息
            // 已移除积分体系，无需刷新用户信息
          } else {
            ElMessage.error('创建批量生图任务失败: ' + response.data.error)
          }
        } else {
          // 无变量，使用原有逻辑
          // 先创建本地任务对象，立即显示给用户
          const referenceImageUrl = referenceImage.value ? URL.createObjectURL(referenceImage.value) : null
          const items = Array.from({length: imageCount.value}, (_, index) => ({
            index: index,
            prompt: batchPrompt.value,
            status: 'pending',
            reference_image_url: referenceImageUrl  // 所有item共享一个参考图
          }))
          createAndSetLocalTask(items, null)
          
          const formData = new FormData()
          
          // 添加参考图片（如果有）
          if (referenceImage.value) {
            formData.append('file', referenceImage.value)
          }
          
          // 添加提示词、数量和API类型
          formData.append('prompt', batchPrompt.value)
          formData.append('image_count', imageCount.value)
          const apiType = getApiTypeFromModelName(selectedModel.value)
          formData.append('api_type', apiType)
          const modelName = getCustomModelName(apiType, selectedModel.value)
          formData.append('model_name', modelName)
          
          // 打印 FormData 内容（用于调试）
          console.log('发送请求参数:')
          for (const [key, value] of formData.entries()) {
            if (key === 'file') {
              console.log(`  ${key}: [文件, ${value.name || 'N/A'}, ${value.size || 0} 字节]`)
            } else {
              console.log(`  ${key}: ${value}`)
            }
          }
          
          console.log('发送请求到: /api/batch/generate-from-image')
          const response = await axios.post('/api/batch/generate-from-image', formData, {
            headers: {
              'Content-Type': 'multipart/form-data'
            },
            timeout: 180000
          })
          console.log('收到响应:', response.data)
          
          if (response.data.success) {
            // 用后端返回的真实task_id更新本地任务
            if (taskManagerRef.value && taskManagerRef.value.updateLocalTaskId && response.data.task_id) {
              taskManagerRef.value.updateLocalTaskId(response.data.task_id)
            }
            // 显示积分扣除信息
            if (response.data.task_data?.credits_deducted) {
              ElMessage.success(`已扣除 ${response.data.task_data.credits_deducted} 积分，剩余 ${response.data.task_data.remaining_credits} 积分`)
            }
            // 刷新用户信息
            // 已移除积分体系，无需刷新用户信息
          } else {
            ElMessage.error('创建批量生图任务失败: ' + response.data.error)
          }
        }
        
        // 不清空参考图和提示词，让用户可以继续使用或修改
        
      } catch (error) {
        console.error('========== 批量生图错误 ==========')
        console.error('错误对象:', error)
        console.error('错误类型:', error.name)
        console.error('错误信息:', error.message)
        console.error('错误代码:', error.code)
        console.error('请求URL:', error.config?.url)
        console.error('请求方法:', error.config?.method)
        console.error('请求头:', error.config?.headers)
        console.error('响应状态:', error.response?.status)
        console.error('响应数据:', error.response?.data)
        console.error('错误堆栈:', error.stack)
        console.error('================================')
        ElMessage.error('批量生图失败: ' + (error.response?.data?.error || error.message))
      } finally {
        isBatchGenerating.value = false
        console.log('批量生图处理完成')
      }
    }

    // 批量改图处理
    const handleBatchEdit = async () => {
      if (uploadedFiles.value.length === 0) {
        ElMessage.warning('请先上传图片')
        return
      }
      
      if (!batchPrompt.value.trim()) {
        ElMessage.warning('请输入生成提示词')
        return
      }

      isBatchGenerating.value = true
      
      try {
        // 先创建本地任务对象，立即显示给用户
        const items = uploadedFiles.value.map((fileObj, index) => ({
          index: index,
          prompt: batchPrompt.value,
          status: 'pending',
          reference_image_url: URL.createObjectURL(fileObj.file)
        }))
        createAndSetLocalTask(items)
        
        const formData = new FormData()
        
        // 添加所有文件
        uploadedFiles.value.forEach(fileObj => {
          formData.append('files', fileObj.file)
        })
        
        // 添加提示词和API类型
        formData.append('prompt', batchPrompt.value)
        const apiType = getApiTypeFromModelName(selectedModel.value)
        formData.append('api_type', apiType)
        const modelName = getCustomModelName(apiType, selectedModel.value)
        formData.append('model_name', modelName)
        
        const response = await axios.post('/api/batch/generate', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          timeout: 180000  // 增加到3分钟
        })
        
        if (response.data.success) {
          // 用后端返回的真实task_id更新本地任务
          if (taskManagerRef.value && taskManagerRef.value.updateLocalTaskId && response.data.task_id) {
            taskManagerRef.value.updateLocalTaskId(response.data.task_id)
          }
          // 显示积分扣除信息
          if (response.data.task_data?.credits_deducted) {
            ElMessage.success(`已扣除 ${response.data.task_data.credits_deducted} 积分，剩余 ${response.data.task_data.remaining_credits} 积分`)
          }
          // 刷新用户信息
          await refreshUserInfo()
        } else {
          ElMessage.error('创建批量改图任务失败: ' + response.data.error)
        }
      } catch (error) {
        console.error('批量改图错误:', error)
        ElMessage.error('批量改图失败: ' + (error.response?.data?.error || error.message))
      } finally {
        isBatchGenerating.value = false
      }
    }

    // 视频生成处理
    const handleVideoGenerate = async () => {
      if (videoMode.value === 'text' && !videoPrompt.value.trim()) {
        ElMessage.warning('文生视频需要输入视频描述')
        return
      }
      if (videoMode.value === 'first_frame' && videoFirstFrameFiles.value.length === 0) {
        ElMessage.warning('请上传首帧图片')
        return
      }
      if (videoMode.value === 'first_last_frame' && (
        videoFirstFrameFiles.value.length === 0 || videoLastFrameFiles.value.length === 0
      )) {
        ElMessage.warning('请上传首帧和尾帧图片')
        return
      }
      if (videoMode.value === 'multimodal') {
        const hasMedia = videoReferenceFiles.value.length > 0 || videoReferenceVideoFiles.value.length > 0
        if (videoReferenceAudioFiles.value.length > 0 && !hasMedia) {
          ElMessage.warning('参考音频不能单独上传，请至少补充参考图片或参考视频')
          return
        }
        if (!hasMedia && !videoPrompt.value.trim()) {
          ElMessage.warning('请提供提示词或参考素材')
          return
        }
      }

      const videoApiType = getApiTypeFromModelName(selectedVideoModel.value)
      if (!isApiConfigured(videoApiType)) {
        const apiName = videoApiType === 'sora' ? 'Sora' : '豆包'
        ElMessage.warning(`请先配置 ${apiName} API Key 才能生成视频`)
        highlightApiType.value = videoApiType
        showApiConfigDialog.value = true
        return
      }

      isBatchGenerating.value = true

      try {
        // 先创建本地任务对象
        const items = [{
          index: 0,
          prompt: videoPrompt.value,
          status: 'pending',
          is_video: true
        }]
        createAndSetLocalTask(items)

        const formData = new FormData()

        // 添加提示词
        formData.append('prompt', videoPrompt.value)
        // 根据选择的模型确定 api_type
        formData.append('api_type', videoApiType)
        formData.append('model_name', selectedVideoModel.value)
        formData.append('video_mode', videoMode.value)
        formData.append('resolution', videoSettings.value.resolution)
        formData.append('ratio', videoSettings.value.ratio)
        formData.append('duration', String(videoSettings.value.duration))
        formData.append('seed', String(videoSettings.value.seed))
        formData.append('watermark', String(videoSettings.value.watermark))
        formData.append('generate_audio', String(videoSettings.value.generateAudio))

        if (videoMode.value === 'first_frame') {
          if (videoFirstFrameFiles.value[0]) {
            formData.append('first_frame_file', videoFirstFrameFiles.value[0].file)
          }
        } else if (videoMode.value === 'first_last_frame') {
          if (videoFirstFrameFiles.value[0]) {
            formData.append('first_frame_file', videoFirstFrameFiles.value[0].file)
          }
          if (videoLastFrameFiles.value[0]) {
            formData.append('last_frame_file', videoLastFrameFiles.value[0].file)
          }
        } else if (videoMode.value === 'multimodal') {
          videoReferenceFiles.value.forEach(fileObj => {
            formData.append('reference_image_files', fileObj.file)
          })
          videoReferenceVideoFiles.value.forEach(fileObj => {
            formData.append('reference_video_files', fileObj.file)
          })
          videoReferenceAudioFiles.value.forEach(fileObj => {
            formData.append('reference_audio_files', fileObj.file)
          })
        }

        const response = await axios.post('/api/batch/generate-video', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          timeout: 300000 // 视频生成时间可能较长，设置为5分钟
        })

        if (response.data.success) {
          // 用后端返回的真实task_id更新本地任务
          if (taskManagerRef.value && taskManagerRef.value.updateLocalTaskId && response.data.task_id) {
            taskManagerRef.value.updateLocalTaskId(response.data.task_id)
          }
          ElMessage.success('视频生成任务已创建')
        } else {
          ElMessage.error('创建视频生成任务失败: ' + response.data.error)
        }
      } catch (error) {
        console.error('视频生成错误:', error)
        ElMessage.error('视频生成失败: ' + (error.response?.data?.error || error.message))
      } finally {
        isBatchGenerating.value = false
      }
    }

    // 组件挂载时加载用户信息和检查首次使用
    onMounted(() => {
      // 已移除用户认证体系，无需加载用户信息

      // 执行数据迁移（如果存在旧格式数据）
      migrateOldDataFormat()

      // 检查是否首次使用
      const initialized = isApiConfigInitialized()
      if (!initialized) {
        // 首次使用，强制显示配置对话框
        isFirstTime.value = true
        showApiConfigDialog.value = true
      } else {
        // 检查是否有可用的图片模型
        const availableImage = availableImageModels.value.filter(m => !m.disabled)
        if (availableImage.length === 0) {
          // 没有可用模型，提示配置
          ElMessage.warning('请先配置至少一个 API 才能使用')
          isFirstTime.value = true
          showApiConfigDialog.value = true
        } else {
          // 检查当前选择的模型是否可用
          const apiType = getApiTypeFromModelName(selectedModel.value)
          if (!isApiConfigured(apiType)) {
            // 当前模型不可用，切换到第一个可用模型
            selectedModel.value = availableImage[0].value
          }
        }
      }
    })
    
    // 监听API配置变化，更新模型列表
    // 注意：由于localStorage变化不会触发响应式更新，我们通过apiConfigVersion来触发
    // 这个watch主要用于其他场景的配置变化检测
    
    return {
      taskManagerRef,
      uploadedFiles,
      referenceImage,
      referenceImageList,
      imageCount,
      batchPrompt,
      isBatchGenerating,
      selectedApi,
      activeTab,
      selectedModel,
      availableModels,
      isStartButtonDisabled,
      handleBatchFileChange,
      handleReferenceImageChange,
      handleReferenceImageRemove,
      handleStartTask,
      handleBatchGenerate,
      handleBatchEdit,
      clearAllImages,
      clearReferenceImage,
      getApiTypeFromModel: getApiTypeFromModelName,
      getCreditsPerImage,
      // 变量相关
      detectedVariables,
      variableValues,
      handlePromptChange,
      getVariableValueCount,
      updateVariableCount,
      totalVariableCombinations,
      hasVariables,
      createAndSetLocalTask,
      // API配置相关
      showApiConfigDialog,
      handleApiConfigConfirmed,
      handleModelChange,
      checkApiKeyConfigured,
      isFirstTime,
      highlightApiType,
      // Tab描述
      activeTabDescription,
      // 视频生成相关
      videoMode,
      videoPrompt,
      videoPromptPlaceholder,
      videoReferenceFiles,
      videoReferenceVideoFiles,
      videoReferenceAudioFiles,
      videoFirstFrameFiles,
      videoLastFrameFiles,
      videoSettings,
      videoDurationOptions,
      selectedVideoModel,
      availableVideoModels,
      handleVideoModelChange,
      handleVideoReferenceFilesChange,
      handleVideoReferenceVideoFilesChange,
      handleVideoReferenceAudioFilesChange,
      handleVideoFirstFrameFilesChange,
      handleVideoLastFrameFilesChange,
      clearVideoReferenceImages,
      clearVideoReferenceVideos,
      clearVideoReferenceAudios,
      clearVideoFirstFrame,
      clearVideoLastFrame
    }
  }
}
</script>

<style>
/* 全局样式重置 */
body {
  margin: 0 !important;
  padding: 0 !important;
}

html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  overflow: hidden;
}

/* 用户信息栏样式 */
.user-bar {
  position: fixed;
  top: 0;
  right: 0;
  padding: 10px 20px;
  background: white;
  border-bottom: 1px solid #eeeeee;
  border-left: 1px solid #eeeeee;
  border-radius: 0 0 0 8px;
  display: flex;
  align-items: center;
  gap: 15px;
  z-index: 1000;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.username {
  font-weight: 600;
  color: #333333;
}

.credits {
  color: #04a864;
  font-weight: 600;
}
</style>

<style scoped>
#app {
  font-family: 'PingFang SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #333333;
  background-color: #efefef;
  height: 100vh;
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.app-container {
  padding: 8px;
  height: 100vh;
  box-sizing: border-box;
}

.main-content {
  display: flex;
  background: white;
  border: 1px solid #eeeeee;
  border-radius: 12px;
  overflow: hidden;
  height: calc(100vh - 16px);
}

/* 左侧面板 */
.left-panel {
  width: 440px;
  flex-shrink: 0;
  border-right: 1px solid #eeeeee;
  background: white;
  display: flex;
  flex-direction: column;
}

.panel-content {
  padding: 20px 32px;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  overflow-y: auto;
}

/* 顶部标题区域 */
.header-section {
  padding-bottom: 20px;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 10px 0;
}

.logo-icon {
  width: 32px;
  height: 32px;
  position: relative;
}

.icon-stack {
  position: relative;
  width: 100%;
  height: 100%;
}

.icon-layer {
  position: absolute;
  background: white;
  border: 1.62px solid #333333;
  border-radius: 1.62px;
  width: 22.86px;
  height: 16.92px;
}

.icon-layer:nth-child(1) {
  top: 3.78px;
  left: 0.9px;
}

.icon-layer:nth-child(2) {
  top: 7.74px;
  left: 4.86px;
}

.icon-layer:nth-child(3) {
  top: 11.7px;
  left: 8.64px;
}

.app-title {
  font-size: 24px;
  font-weight: 600;
  color: #333333;
  margin: 0;
}

.app-subtitle {
  font-size: 16px;
  color: #333333;
  margin: 0;
}

/* 标签切换 */
.tab-switcher {
  display: flex;
  background: #eeeeee;
  border-radius: 6px;
  padding: 2px;
  gap: 2px;
}

.tab-item {
  flex: 1;
  padding: 3px 28px;
  text-align: center;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-item.active {
  background: white;
  border: 1px solid #dddddd;
}

.tab-item span {
  font-size: 14px;
  color: #333333;
}

.tab-description {
  font-size: 14px;
  color: #999999;
  margin: 0;
  padding-top: 10px;
}

/* 操作区域 */
.operation-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 16px;
  font-weight: 600;
  color: #333333;
  margin: 0;
}

.model-selector-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.api-config-link {
  padding: 0;
  font-size: 14px;
  color: #04a864;
  display: flex;
  align-items: center;
  gap: 4px;
}

.api-config-link:hover {
  color: #038a56;
}

.api-config-link :deep(.el-icon) {
  font-size: 16px;
}

.model-selector {
  width: 100%;
}

.model-selector :deep(.el-input__wrapper) {
  border: 1px solid #dddddd;
  border-radius: 6px;
  padding: 8px 12px;
}

.model-selector :deep(.el-input__inner) {
  font-size: 14px;
  color: #333333;
}

.model-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.model-status {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  margin-left: 12px;
}

.model-status.status-configured {
  color: #065f46;
}

.model-status.status-not-configured {
  color: #92400e;
}

.model-status .el-icon {
  font-size: 14px;
}

.prompt-input {
  border-radius: 6px;
}

.prompt-input :deep(.el-textarea__inner) {
  border: 1px solid #dddddd;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 14px;
  color: #333333;
}

.prompt-input :deep(.el-textarea__inner)::placeholder {
  color: #bbbbbb;
}

.upload-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.clear-icon {
  font-size: 16px;
  color: #333333;
  cursor: pointer;
}

.video-options-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.video-option-switches {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 4px;
}

.video-options-grid :deep(.el-input__wrapper),
.video-options-grid :deep(.el-select__wrapper),
.video-options-grid :deep(.el-input-number) {
  width: 100%;
}

/* 开始按钮 */
.start-button-container {
  margin-top: auto;
  padding-top: 10px;
}

.start-button {
  width: 100%;
  height: 40px;
  background: #04a864;
  border: 1px solid #dddddd;
  border-radius: 6px;
  font-size: 14px;
  color: white;
}

.start-button:hover {
  background: #038a56;
}

.start-button:disabled {
  background: #cccccc;
  color: #999999;
}

/* 分隔线 */
.divider {
  width: 1px;
  background: #eeeeee;
  flex-shrink: 0;
}

/* 右侧面板 */
.right-panel {
  flex: 1;
  background: white;
  padding: 20px 32px;
}

/* 批量生图相关样式 */
.reference-upload {
  width: 100%;
}

.reference-upload :deep(.el-upload) {
  width: 148px;
  height: 148px;
  border: 1px dashed #dddddd;
  border-radius: 6px;
}

.reference-upload :deep(.el-upload:hover) {
  border-color: #04a864;
}

.reference-upload :deep(.el-upload-list__item) {
  width: 148px;
  height: 148px;
  border-radius: 6px;
}

.count-selector {
  width: 100%;
}

.count-selector :deep(.el-input-number__decrease),
.count-selector :deep(.el-input-number__increase) {
  background: white;
  border: 1px solid #dddddd;
}

.count-selector :deep(.el-input__inner) {
  border: 1px solid #dddddd;
  border-radius: 6px;
  text-align: center;
}

.count-hint {
  display: block;
  font-size: 12px;
  color: #999999;
  margin-top: 8px;
}

/* 变量功能样式 */
.variable-section {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 16px;
  margin: 12px 0;
}

.variable-header {
  margin-bottom: 12px;
}

.variable-header .form-label {
  color: #04a864;
  font-weight: 600;
}

.variable-input-group {
  margin-bottom: 16px;
}

.variable-input-group:last-child {
  margin-bottom: 0;
}

.variable-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #495057;
  margin-bottom: 8px;
  font-family: 'Courier New', monospace;
}

.variable-textarea {
  width: 100%;
}

.variable-textarea :deep(.el-textarea__inner) {
  border: 1px solid #dddddd;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 14px;
  color: #333333;
  background: white;
  line-height: 1.6;
}

.variable-textarea :deep(.el-textarea__inner)::placeholder {
  color: #bbbbbb;
}

.variable-count {
  display: block;
  font-size: 12px;
  color: #6c757d;
  margin-top: 6px;
  font-style: italic;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .left-panel {
    width: 380px;
  }
  
  .panel-content {
    padding: 16px 24px;
  }
}

@media (max-width: 768px) {
  .main-content {
    flex-direction: column;
  }
  
  .left-panel {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #eeeeee;
  }
  
  .divider {
    width: 100%;
    height: 1px;
  }
  
  .right-panel {
    padding: 16px 24px;
  }
}
</style>
