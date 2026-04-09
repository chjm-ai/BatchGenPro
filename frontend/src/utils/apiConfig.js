/**
 * API配置管理工具函数
 */

// 模型与API的映射关系
export const MODEL_API_MAPPING = {
  'gemini-2.5-flash-image': {
    apiType: 'gemini',
    displayName: 'Gemini 2.5 Flash Image'
  },
  'gemini-3-pro-image-preview': {
    apiType: 'gemini',
    displayName: 'Gemini 3 Pro Image Preview'
  },
  'doubao-seedream-4-0-250828': {
    apiType: 'doubao',
    displayName: '豆包 Seedream 4.0'
  },
  'sora-2': {
    apiType: 'sora',
    displayName: 'Sora 2'
  },
  'doubao-seedance-2-0-260128': {
    apiType: 'doubao',
    displayName: '豆包 Seedance 2.0'
  },
  'doubao-seedance-2-0-fast-260128': {
    apiType: 'doubao',
    displayName: '豆包 Seedance 2.0 Fast'
  }
}

/**
 * 检查是否已完成首次配置
 */
export function isApiConfigInitialized() {
  return localStorage.getItem('api_config_initialized') === 'true'
}

/**
 * 获取API配置
 * @param {string} apiType - API类型 ('gemini' 或 'doubao')
 * @returns {object|null} API配置对象
 */
export function getApiConfig(apiType) {
  try {
    const configStr = localStorage.getItem(`${apiType}_api_config`)
    if (!configStr) return null
    return JSON.parse(configStr)
  } catch (error) {
    console.error(`获取 ${apiType} API配置失败:`, error)
    return null
  }
}

/**
 * 保存API配置
 * @param {string} apiType - API类型
 * @param {object} config - 配置对象
 */
export function saveApiConfig(apiType, config) {
  try {
    localStorage.setItem(`${apiType}_api_config`, JSON.stringify(config))
    // 标记为已初始化
    localStorage.setItem('api_config_initialized', 'true')
  } catch (error) {
    console.error(`保存 ${apiType} API配置失败:`, error)
    throw error
  }
}

/**
 * 检查API是否已配置
 * @param {string} apiType - API类型
 * @returns {boolean}
 */
export function isApiConfigured(apiType) {
  const config = getApiConfig(apiType)
  if (!config) return false
  
  // 检查配置是否有效
  if (config.type === 'official') {
    // 官方API：需要API Key
    return !!(config.api_key && config.api_key.trim())
  } else if (config.type === 'third_party') {
    // 第三方API：需要Base URL
    return !!(config.base_url && config.base_url.trim())
  }
  
  return false
}

/**
 * 获取可用模型列表（根据已配置的API）
 * @returns {array} 可用模型列表
 */
export function getAvailableModels() {
  const allModels = [
    { value: 'gemini-2.5-flash-image', apiType: 'gemini', label: 'Gemini 2.5 Flash Image' },
    { value: 'gemini-3-pro-image-preview', apiType: 'gemini', label: 'Gemini 3 Pro Image Preview' },
    { value: 'doubao-seedream-4-0-250828', apiType: 'doubao', label: '豆包 Seedream 4.0' }
  ]
  
  return allModels.filter(model => isApiConfigured(model.apiType))
}

/**
 * 根据模型名称获取API类型
 * @param {string} modelName - 模型名称
 * @returns {string} API类型
 */
export function getApiTypeFromModel(modelName) {
  const mapping = MODEL_API_MAPPING[modelName]
  return mapping ? mapping.apiType : 'gemini'
}

/**
 * 验证URL格式
 * @param {string} url - URL字符串
 * @returns {boolean}
 */
export function isValidUrl(url) {
  if (!url || !url.trim()) return false
  try {
    const urlObj = new URL(url.trim())
    return urlObj.protocol === 'http:' || urlObj.protocol === 'https:'
  } catch {
    return false
  }
}

/**
 * 验证API配置
 * @param {string} apiType - API类型
 * @param {object} config - 配置对象
 * @returns {object} { valid: boolean, error: string }
 */
export function validateApiConfig(apiType, config) {
  if (!config.type) {
    return { valid: false, error: '请选择API类型' }
  }
  
  if (config.type === 'official') {
    // 官方API：API Key必填
    if (!config.api_key || !config.api_key.trim()) {
      return { valid: false, error: '官方API需要填写API Key' }
    }
  } else if (config.type === 'third_party') {
    // 第三方API：Base URL必填
    if (!config.base_url || !config.base_url.trim()) {
      return { valid: false, error: '第三方API需要填写Base URL' }
    }
    // 验证URL格式
    if (!isValidUrl(config.base_url)) {
      return { valid: false, error: 'Base URL格式不正确，请输入有效的URL（如：https://example.com）' }
    }
  }
  
  return { valid: true, error: '' }
}

/**
 * 迁移旧格式数据到新格式
 */
export function migrateOldDataFormat() {
  // 检查是否已经迁移过
  if (isApiConfigInitialized()) {
    return
  }

  try {
    // 读取旧格式数据
    const geminiApiKey = localStorage.getItem('gemini_api_key')
    const geminiBaseUrl = localStorage.getItem('gemini_base_url')
    const doubaoApiKey = localStorage.getItem('doubao_api_key')
    const doubaoBaseUrl = localStorage.getItem('doubao_base_url')
    const soraApiKey = localStorage.getItem('sora_api_key')
    const soraBaseUrl = localStorage.getItem('sora_base_url')

    // 迁移Gemini配置
    if (geminiApiKey || geminiBaseUrl) {
      const geminiConfig = {
        type: geminiBaseUrl ? 'third_party' : 'official',
        api_key: geminiApiKey || '',
        base_url: geminiBaseUrl || '',
        configured: !!(geminiApiKey || geminiBaseUrl)
      }
      saveApiConfig('gemini', geminiConfig)
    }

    // 迁移豆包配置
    if (doubaoApiKey || doubaoBaseUrl) {
      const doubaoConfig = {
        type: doubaoBaseUrl ? 'third_party' : 'official',
        api_key: doubaoApiKey || '',
        base_url: doubaoBaseUrl || '',
        configured: !!(doubaoApiKey || doubaoBaseUrl)
      }
      saveApiConfig('doubao', doubaoConfig)
    }

    // 迁移Sora配置
    if (soraApiKey || soraBaseUrl) {
      const soraConfig = {
        type: soraBaseUrl ? 'third_party' : 'official',
        api_key: soraApiKey || '',
        base_url: soraBaseUrl || '',
        configured: !!(soraApiKey || soraBaseUrl)
      }
      saveApiConfig('sora', soraConfig)
    }

    // 如果至少有一个API配置，标记为已初始化
    if (geminiApiKey || geminiBaseUrl || doubaoApiKey || doubaoBaseUrl || soraApiKey || soraBaseUrl) {
      localStorage.setItem('api_config_initialized', 'true')
    }
  } catch (error) {
    console.error('数据迁移失败:', error)
  }
}

/**
 * 获取API Key（兼容旧代码）
 * @param {string} apiType - API类型
 * @returns {string|null}
 */
export function getApiKey(apiType) {
  const config = getApiConfig(apiType)
  if (config && config.api_key && config.api_key.trim()) {
    return config.api_key.trim()
  }
  // 兼容旧格式
  const oldKey = localStorage.getItem(`${apiType}_api_key`)
  if (oldKey && oldKey.trim() && oldKey.trim() !== `your_${apiType}_api_key_here`) {
    return oldKey.trim()
  }
  return null
}

/**
 * 获取Base URL（兼容旧代码）
 * @param {string} apiType - API类型
 * @returns {string|null}
 */
export function getBaseUrl(apiType) {
  const config = getApiConfig(apiType)
  if (config && config.base_url && config.base_url.trim()) {
    return config.base_url.trim()
  }
  // 兼容旧格式
  const oldUrl = localStorage.getItem(`${apiType}_base_url`)
  if (oldUrl && oldUrl.trim()) {
    return oldUrl.trim()
  }
  return null
}

/**
 * 获取自定义模型名称（仅在自定义端点时使用）
 * @param {string} apiType - API类型
 * @param {string} defaultModelName - 默认模型名称
 * @returns {string} 自定义模型名称或默认模型名称
 */
export function getCustomModelName(apiType, defaultModelName) {
  const config = getApiConfig(apiType)
  if (config && config.type === 'third_party' && config.custom_model_name && config.custom_model_name.trim()) {
    return config.custom_model_name.trim()
  }
  return defaultModelName
}
