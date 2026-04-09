import assert from 'node:assert/strict'

import {
  extractApiType,
  isConfiguredApiKey,
  shouldAttachApiKey
} from '../src/utils/requestAuth.js'

function testTaskRequestDoesNotRequireApiKey() {
  const config = {
    url: '/api/batch/tasks',
    method: 'get'
  }

  assert.equal(extractApiType(config), null)
  assert.equal(shouldAttachApiKey(config), false)
}

function testGenerateRequestRequiresApiKey() {
  const formData = new FormData()
  formData.append('api_type', 'gemini')
  formData.append('prompt', 'test')

  const config = {
    url: '/api/batch/generate',
    method: 'post',
    data: formData
  }

  assert.equal(extractApiType(config), 'gemini')
  assert.equal(shouldAttachApiKey(config), true)
}

function testPlaceholderKeyIsInvalid() {
  assert.equal(isConfiguredApiKey('your_gemini_api_key_here'), false)
  assert.equal(isConfiguredApiKey('  real-key  '), true)
}

testTaskRequestDoesNotRequireApiKey()
testGenerateRequestRequiresApiKey()
testPlaceholderKeyIsInvalid()

console.log('requestAuth tests passed')
