export function extractApiType(config) {
  if (config.data instanceof FormData) {
    return config.data.get('api_type') || null
  }

  if (config.params && config.params.api_type) {
    return config.params.api_type
  }

  return null
}

export function shouldAttachApiKey(config) {
  return !!extractApiType(config)
}

export function isConfiguredApiKey(apiKey) {
  if (!apiKey || !apiKey.trim()) return false

  const normalizedKey = apiKey.trim()
  const invalidPlaceholders = [
    'your_gemini_api_key_here',
    'your_doubao_api_key_here',
    'your_sora_api_key_here'
  ]

  return !invalidPlaceholders.includes(normalizedKey)
}
