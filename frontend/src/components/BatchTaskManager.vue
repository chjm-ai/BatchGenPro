<template>
  <div class="batch-task-manager">
    <!-- 任务列表头部 -->
    <div class="task-header">
      <div class="header-left">
        <h3 class="task-title">任务列表</h3>
        <span v-if="currentTask" class="task-progress">{{ getTaskProgress() }}</span>
      </div>
      <el-button 
        v-if="currentTask && (currentTask.status === 'completed' || (currentTask.status === 'cancelled' && currentTask.results && currentTask.results.generated_images && currentTask.results.generated_images.length > 0))" 
        @click="downloadResults(currentTask)" 
        type="primary" 
        size="small"
        class="download-all-btn"
      >
        下载全部
      </el-button>
      <el-button 
        v-if="currentTask && (currentTask.status === 'processing' || currentTask.status === 'pending')" 
        @click="cancelTask(currentTask.task_id)" 
        type="danger" 
        size="small"
        class="cancel-btn"
      >
        取消任务
      </el-button>
    </div>
    
    <!-- 进度条 -->
    <div v-if="currentTask && currentTask.status === 'processing'" class="progress-bar">
      <div class="progress-fill" :style="{ width: currentTask.progress + '%' }"></div>
    </div>
    
    <!-- 任务列表 -->
    <div v-if="currentTask && getTaskItems().length > 0" class="task-list">
      <div 
        v-for="(item, index) in getTaskItems()" 
        :key="item.id || index" 
        class="task-item"
      >
        <!-- 任务信息栏 -->
        <div class="task-info-row">
          <div class="task-info-left">
            <span class="task-number">#{{ index + 1 }}</span>
            <span class="task-prompt">{{ getTaskPromptForItem(index) }}</span>
          </div>
          <el-tag :type="getStatusTagType(item.status)" size="small" class="task-status-tag">
            {{ getStatusText(item.status) }}
          </el-tag>
        </div>
        
        <!-- 参考图（如果有） -->
        <div v-if="item.reference_image_url" class="reference-section">
          <span class="reference-label">参考图：</span>
          <el-image
            :src="item.reference_image_url"
            :preview-src-list="[item.reference_image_url]"
            fit="cover"
            class="reference-image"
            lazy
          />
        </div>
        
        <!-- 生成结果 -->
        <div class="result-section">
          <span class="result-label">生成结果：</span>
          <video
            v-if="item.generated_url && item.is_video"
            :src="item.generated_url"
            class="generated-video"
            controls
          ></video>
          <el-image
            v-else-if="item.generated_url"
            :src="item.generated_url"
            :preview-src-list="[item.generated_url]"
            fit="cover"
            class="generated-image"
            lazy
          >
            <template #error>
              <div class="image-placeholder">
                <el-icon><Picture /></el-icon>
              </div>
            </template>
          </el-image>
          <div v-else class="image-placeholder">
            <el-icon><Loading /></el-icon>
            <span>{{ item.status === 'pending' ? '待开始' : item.status === 'processing' ? '生成中...' : '无结果' }}</span>
          </div>
        </div>

        <div v-if="item.last_frame_url" class="result-section">
          <span class="result-label">尾帧：</span>
          <el-image
            :src="item.last_frame_url"
            :preview-src-list="[item.last_frame_url]"
            fit="cover"
            class="generated-image"
            lazy
          />
        </div>
        
        <!-- 下载按钮 -->
        <div v-if="item.generated_url" class="task-actions">
          <el-button 
            size="small" 
            @click="downloadSingleResult(item.generated_url, item.filename)"
            icon="Download"
          >
            下载
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 无任务状态 -->
    <div v-else-if="!currentTask" class="no-task">
      <div class="empty-state">
        <el-icon size="60" class="empty-icon"><Document /></el-icon>
        <p class="empty-text">暂无任务</p>
      </div>
    </div>
    
    <!-- 任务进行中但无结果 -->
    <div v-else-if="currentTask && !currentTask.items && (!currentTask.results || !currentTask.results.generated_images || currentTask.results.generated_images.length === 0)" class="processing-state">
      <div class="processing-info">
        <el-icon size="40" class="processing-icon"><Loading /></el-icon>
        <p class="processing-text">正在处理中...</p>
        <p class="processing-detail">{{ getTaskProgress() }}</p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { Picture, Download, Document, Loading } from '@element-plus/icons-vue'

export default {
  name: 'BatchTaskManager',
  components: {
    Picture,
    Download,
    Document,
    Loading
  },
  setup() {
    const currentTask = ref(null)
    const isLoadingTasks = ref(false)
    let refreshInterval = null
    // 已提示过失败原因的结果集合，避免重复弹窗
    const notifiedFailures = new Set()

    // 获取任务进度文本
    const getTaskProgress = () => {
      if (!currentTask.value) return ''
      const processed = currentTask.value.processed_images || 0
      const total = currentTask.value.total_images || 0
      return `${processed}/${total}`
    }

    // 获取最新任务
    const fetchLatestTask = async () => {
      try {
        // 只有在没有当前任务时才显示loading
        if (!currentTask.value) {
          isLoadingTasks.value = true
        }
        const response = await axios.get('/api/batch/tasks')
        
        if (response.data.success && response.data.tasks && response.data.tasks.length > 0) {
          const latestTask = response.data.tasks[0]
          
          // 如果当前有local task，且后端返回的任务ID匹配，则只更新必要字段（避免重新渲染）
          if (currentTask.value && currentTask.value.items && 
              currentTask.value.task_id && currentTask.value.task_id === latestTask.task_id) {
            // 只更新状态和进度，保留items和reference_image_url
            currentTask.value.status = latestTask.status
            currentTask.value.progress = latestTask.progress
            currentTask.value.processed_images = latestTask.processed_images
            currentTask.value.updated_at = latestTask.updated_at
            
            // 更新results，但不覆盖items
            if (latestTask.results) {
              currentTask.value.results = latestTask.results
              
              // 更新items中的状态和图片URL
              if (latestTask.results.generated_images) {
                latestTask.results.generated_images.forEach((result, index) => {
                  if (currentTask.value.items[index]) {
                    currentTask.value.items[index].status = getItemStatus(result)
                    if (result.generated_url) {
                      currentTask.value.items[index].generated_url = result.generated_url
                    }
                    if (result.filename) {
                      currentTask.value.items[index].filename = result.filename
                    }
                    currentTask.value.items[index].is_video = !!result.is_video
                    currentTask.value.items[index].last_frame_url = result.last_frame_url || null
                    // 失败项弹出错误信息（仅提示一次）
                    if (result.error) {
                      const key = `${currentTask.value.task_id || 'task'}:${result.filename || index}`
                      if (!notifiedFailures.has(key)) {
                        const msg = typeof result.error === 'string' ? result.error : JSON.stringify(result.error)
                        ElMessage.error(`第 ${index + 1} 张生成失败：${msg.substring(0, 160)}`)
                        notifiedFailures.add(key)
                      }
                    }
                    // 保留原有的prompt和reference_image_url（前端临时生成的blob URL）
                  }
                })
              }
            }
          } else {
            // 首次加载或task_id不匹配，直接使用后端返回的任务
            // 但保留本地items中的reference_image_url（前端临时生成的blob URL）
            if (currentTask.value && currentTask.value.items && latestTask.items) {
              // 合并items，保留本地设置的reference_image_url
              currentTask.value.items.forEach((localItem, index) => {
                if (latestTask.items[index] && localItem.reference_image_url) {
                  latestTask.items[index].reference_image_url = localItem.reference_image_url
                }
              })
            }
            currentTask.value = latestTask
            // 首次加载/切换任务后，同步提示已失败的项
            if (currentTask.value && currentTask.value.results && currentTask.value.results.generated_images) {
              currentTask.value.results.generated_images.forEach((result, index) => {
                if (result && result.error) {
                  const key = `${currentTask.value.task_id || 'task'}:${result.filename || index}`
                  if (!notifiedFailures.has(key)) {
                    const msg = typeof result.error === 'string' ? result.error : JSON.stringify(result.error)
                    ElMessage.error(`第 ${index + 1} 张生成失败：${msg.substring(0, 160)}`)
                    notifiedFailures.add(key)
                  }
                }
              })
            }
          }
        } else {
          // 只有在没有local task时才清空
          if (!currentTask.value || !currentTask.value.items) {
            currentTask.value = null
          }
        }
      } catch (error) {
        console.error('获取任务失败:', error)
        ElMessage.error('获取任务失败')
      } finally {
        isLoadingTasks.value = false
      }
    }

    // 刷新任务
    const refreshTasks = () => {
      fetchLatestTask()
    }

    // 取消任务
    const cancelTask = async (taskId) => {
      try {
        await ElMessageBox.confirm('确定要取消这个任务吗？', '确认取消', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        
        const response = await axios.delete(`/api/batch/tasks/${taskId}`)
        if (response.data.success) {
          ElMessage.success('任务已取消')
          fetchLatestTask()
        } else {
          ElMessage.error('取消任务失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('取消任务失败:', error)
          ElMessage.error('取消任务失败')
        }
      }
    }

    // 下载结果 (批量)
    const downloadResults = async (task) => {
      try {
        const response = await axios.get(`/api/batch/tasks/${task.task_id}/results`)
        if (response.data.success) {
          const results = response.data.results
          
          let downloadCount = 0
          
          // 从 results.generated_images 中下载
          if (results.generated_images && results.generated_images.length > 0) {
            for (let i = 0; i < results.generated_images.length; i++) {
              const resultInfo = results.generated_images[i]
              if (resultInfo.generated_url) {
                const link = document.createElement('a')
                link.href = resultInfo.generated_url
                link.download = resultInfo.generated_filename || resultInfo.filename || `generated_${task.task_id.substring(0, 8)}_${i + 1}`
                document.body.appendChild(link)
                link.click()
                document.body.removeChild(link)
                downloadCount++
              }
            }
          }
          
          if (downloadCount > 0) {
            ElMessage.success(`已开始下载 ${downloadCount} 个结果`)
          } else {
            ElMessage.warning('没有可下载的结果')
          }
        } else {
          ElMessage.error('获取结果失败')
        }
      } catch (error) {
        ElMessage.error('下载结果失败')
        console.error('下载结果失败:', error)
      }
    }

    // 下载单个结果
    const downloadSingleResult = (resultUrl, filename) => {
      try {
        const link = document.createElement('a')
        link.href = resultUrl
        link.download = filename || 'generated_result'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        ElMessage.success('开始下载结果')
      } catch (error) {
        ElMessage.error('下载失败')
        console.error('下载失败:', error)
      }
    }

    // 获取状态标签类型
    const getStatusTagType = (status) => {
      switch (status) {
        case 'pending': return 'info'
        case 'processing': return 'warning'
        case 'completed': return 'success'
        case 'failed': return 'danger'
        case 'cancelled': return 'info'
        default: return 'info'
      }
    }

    // 获取状态文本
    const getStatusText = (status) => {
      switch (status) {
        case 'pending': return '未开始'
        case 'processing': return '生成中'
        case 'completed': return '已完成'
        case 'failed': return '生成失败'
        case 'cancelled': return '已取消'
        default: return '未知'
      }
    }

    // 获取任务状态样式类
    const getTaskStatusClass = (status) => {
      return `task-status-${status}`
    }

    // 格式化时间
    const formatTime = (timeString) => {
      if (!timeString) return '未知时间'
      const date = new Date(timeString)
      return date.toLocaleString('zh-CN')
    }

    // 获取任务中每个item的prompt（如果是批量生图带变量，可能需要展示不同的prompt）
    const getTaskPromptForItem = (index) => {
      if (!currentTask.value) return ''
      const items = getTaskItems()
      if (items[index] && items[index].prompt) {
        return items[index].prompt
      }
      return currentTask.value.prompt || '无'
    }

    // 获取每个item的状态
    const getItemStatus = (result) => {
      if (!result) return 'pending'
      if (result.generated_url) return 'completed'
      if (result.error) return 'failed'
      return 'processing'
    }

    // 获取任务列表项（统一格式）
    const getTaskItems = () => {
      if (!currentTask.value) return []
      
      const items = []
      const total = currentTask.value.total_images || 0
      
      // 优先使用task_data中的items字段（多prompt模式）
      if (currentTask.value.items && currentTask.value.items.length > 0) {
        currentTask.value.items.forEach((item) => {
          items.push({
            id: `item_${item.index}`,
            status: 'pending',
            prompt: item.prompt,
            generated_url: null,
            filename: null,
            reference_image_url: item.reference_image_url || null,
            is_video: !!item.is_video,
            last_frame_url: null
          })
        })
        
        // 如果有results，合并结果
        if (currentTask.value.results && currentTask.value.results.generated_images) {
          currentTask.value.results.generated_images.forEach((result, index) => {
            if (items[index]) {
              items[index].status = getItemStatus(result)
              items[index].generated_url = result.generated_url
              items[index].filename = result.filename
              items[index].is_video = !!result.is_video
              items[index].last_frame_url = result.last_frame_url || null
            }
          })
        }
        
        return items
      }
      
      // 如果有results.generated_images，使用它
      if (currentTask.value.results && currentTask.value.results.generated_images) {
        currentTask.value.results.generated_images.forEach((result, index) => {
          items.push({
            id: result.filename || `item_${index}`,
            status: getItemStatus(result),
            prompt: result.prompt || currentTask.value.prompt,  // 优先使用result中的prompt
            generated_url: result.generated_url,
            filename: result.filename,
            is_video: !!result.is_video,
            last_frame_url: result.last_frame_url || null
          })
        })
      } else {
        // 否则根据total_images创建空项
        for (let i = 0; i < total; i++) {
          items.push({
            id: `item_${i}`,
            status: 'pending',
            prompt: currentTask.value.prompt,
            generated_url: null,
            filename: null,
            is_video: false,
            last_frame_url: null
          })
        }
      }
      
      return items
    }

    // 设置本地任务（用于立即显示）
    const setLocalTask = (localTask) => {
      currentTask.value = localTask
    }
    
    const updateLocalTaskId = (taskId) => {
      if (currentTask.value) {
        currentTask.value.task_id = taskId
      }
    }

    onMounted(() => {
      fetchLatestTask()
      // 每3秒刷新一次任务状态
      refreshInterval = setInterval(fetchLatestTask, 3000)
    })

    onUnmounted(() => {
      if (refreshInterval) {
        clearInterval(refreshInterval)
      }
    })

    return {
      currentTask,
      isLoadingTasks,
      fetchLatestTask,
      refreshTasks,
      cancelTask,
      downloadResults,
      downloadSingleResult,
      getTaskProgress,
      getStatusTagType,
      getStatusText,
      getTaskStatusClass,
      formatTime,
      getTaskPromptForItem,
      getItemStatus,
      getTaskItems,
      setLocalTask,
      updateLocalTaskId
    }
  }
}
</script>

<style scoped>
.batch-task-manager {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* 任务头部 */
.task-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  margin-bottom: 8px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-title {
  font-size: 16px;
  font-weight: 600;
  color: #333333;
  margin: 0;
}

.task-progress {
  font-size: 16px;
  font-weight: 600;
  color: #333333;
}

.download-all-btn {
  background: #04a864;
  border: 1px solid #dddddd;
  border-radius: 6px;
  font-size: 14px;
  color: white;
  padding: 5px 16px;
}

.download-all-btn:hover {
  background: #038a56;
}

.cancel-btn {
  background: #f56c6c;
  border: 1px solid #dddddd;
  border-radius: 6px;
  font-size: 14px;
  color: white;
  padding: 5px 16px;
}

.cancel-btn:hover {
  background: #e63939;
}

/* 进度条 */
.progress-bar {
  height: 8px;
  background: #d9d9d9;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 20px;
}

.progress-fill {
  height: 100%;
  background: #04a864;
  border-radius: 4px;
  transition: width 0.3s ease;
}

/* 结果网格 */
/* 任务列表样式 */
.task-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 16px 0;
  overflow-y: auto;
  flex: 1;
}

.task-item {
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.2s;
}

.task-item:hover {
  border-color: #04a864;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* 任务信息行 */
.task-info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.task-info-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.task-number {
  font-weight: 600;
  color: #04a864;
  font-size: 16px;
}

.task-prompt {
  font-size: 14px;
  color: #333333;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-status-tag {
  flex-shrink: 0;
}

/* 参考图和结果图区域 */
.reference-section,
.result-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.reference-label,
.result-label {
  font-size: 13px;
  color: #666666;
  font-weight: 500;
  min-width: 70px;
}

.reference-image,
.generated-image {
  width: 80px;
  height: 80px;
  border-radius: 6px;
  overflow: hidden;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
}

.generated-video {
  width: 160px;
  height: 90px;
  border-radius: 6px;
  background: #000000;
  border: 1px solid #e0e0e0;
}

.image-placeholder {
  width: 80px;
  height: 80px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  color: #999999;
  font-size: 12px;
  gap: 4px;
}

.image-placeholder .el-icon {
  font-size: 20px;
}

/* 任务操作按钮 */
.task-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 4px;
  border-top: 1px solid #f0f0f0;
}

/* 无任务状态 */
.no-task {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-state {
  text-align: center;
}

.empty-icon {
  color: #c0c4cc;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 16px;
  color: #909399;
  margin: 0;
}

/* 处理中状态 */
.processing-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.processing-info {
  text-align: center;
}

.processing-icon {
  color: #04a864;
  margin-bottom: 16px;
  animation: spin 1s linear infinite;
}

.processing-text {
  font-size: 16px;
  color: #333333;
  margin: 0 0 8px 0;
}

.processing-detail {
  font-size: 14px;
  color: #666666;
  margin: 0;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .results-grid {
    gap: 16px;
  }
  
  .result-image {
    width: 140px;
    height: 140px;
  }
  
  .result-filename {
    max-width: 140px;
  }
}

@media (max-width: 768px) {
  .results-grid {
    gap: 12px;
    padding: 16px 0;
  }
  
  .result-image {
    width: 120px;
    height: 120px;
  }
  
  .result-filename {
    max-width: 120px;
    font-size: 12px;
  }
  
  .task-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>
