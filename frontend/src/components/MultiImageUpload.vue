<template>
  <div class="multi-image-upload">
    <!-- 上传区域 -->
    <div class="upload-area" @click="triggerUpload" @dragover.prevent @drop.prevent="handleDrop">
      <el-icon class="upload-icon"><Upload /></el-icon>
      <span class="upload-text">{{ uploadText }}</span>
    </div>
    
    <!-- 文件列表 -->
    <div v-if="files.length > 0" class="files-list">
      <div 
        v-for="(file, index) in files" 
        :key="index" 
        class="file-item"
      >
        <div class="file-thumbnail">
          <el-image
            v-if="previewMode === 'image'"
            :src="file.previewUrl"
            fit="cover"
            class="thumbnail-image"
          />
          <video
            v-else-if="previewMode === 'video'"
            :src="file.previewUrl"
            class="thumbnail-video"
            muted
            controls
          ></video>
          <div v-else class="thumbnail-placeholder">
            <el-icon><Document /></el-icon>
          </div>
        </div>
        <span class="filename">{{ file.name }}</span>
        <el-icon class="delete-icon" @click="removeFile(index)"><Close /></el-icon>
      </div>
    </div>
    
    <!-- 隐藏的文件输入 -->
    <input
      ref="fileInput"
      type="file"
      multiple
      :accept="accept"
      @change="handleFileChange"
      style="display: none"
    />
  </div>
</template>

<script>
import { ref, watch } from 'vue'
import { Upload, Close, Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

export default {
  name: 'MultiImageUpload',
  props: {
    files: {
      type: Array,
      default: () => []
    },
    accept: {
      type: String,
      default: 'image/*'
    },
    uploadText: {
      type: String,
      default: 'Upload Images'
    },
    previewMode: {
      type: String,
      default: 'image'
    },
    maxCount: {
      type: Number,
      default: 99
    }
  },
  emits: ['files-change'],
  components: {
    Upload,
    Close,
    Document
  },
  setup(props, { emit }) {
    const files = ref([...props.files])
    const fileInput = ref(null)

    const triggerUpload = () => {
      fileInput.value?.click()
    }

    const handleFileChange = (event) => {
      const selectedFiles = Array.from(event.target.files)
      addFiles(selectedFiles)
      // 清空input值，允许重复选择相同文件
      event.target.value = ''
    }

    const handleDrop = (event) => {
      const droppedFiles = Array.from(event.dataTransfer.files)
      addFiles(droppedFiles)
    }

    const addFiles = (newFiles) => {
      newFiles.forEach(newFile => {
        if (files.value.length >= props.maxCount) {
          ElMessage.warning(`最多上传 ${props.maxCount} 个文件`)
          return
        }
        // 检查是否已存在相同文件
        const exists = files.value.some(f => f.name === newFile.name && f.size === newFile.size)
        if (exists) {
          ElMessage.warning('文件已存在')
          return
        }
        
        // 创建预览URL
        const previewUrl = URL.createObjectURL(newFile)
        
        // 添加到文件列表
        files.value.push({
          file: newFile,
          name: newFile.name,
          size: newFile.size,
          previewUrl: previewUrl
        })
      })
      
      emit('files-change', files.value)
    }

    const removeFile = (index) => {
      // 释放预览URL
      URL.revokeObjectURL(files.value[index].previewUrl)
      
      // 从列表中移除
      files.value.splice(index, 1)
      
      emit('files-change', files.value)
    }

    const clearAll = () => {
      // 释放所有预览URL
      files.value.forEach(file => {
        URL.revokeObjectURL(file.previewUrl)
      })
      
      // 清空列表
      files.value = []
      
      emit('files-change', files.value)
    }

    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    // 监听props变化
    watch(() => props.files, (newFiles) => {
      files.value = [...newFiles]
    }, { deep: true })

    return {
      files,
      fileInput,
      triggerUpload,
      handleFileChange,
      handleDrop,
      removeFile,
      clearAll,
      formatFileSize
    }
  }
}
</script>

<style scoped>
.multi-image-upload {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 上传区域 */
.upload-area {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  height: 92px;
  background: #fafafa;
  border: 1px dashed #dddddd;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-area:hover {
  border-color: #04a864;
  background: #f0f9f5;
}

.upload-icon {
  font-size: 20px;
  color: #333333;
}

.upload-text {
  font-size: 14px;
  color: #333333;
}

/* 文件列表 */
.files-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px 0;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0;
}

.file-thumbnail {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  background: #d9d9d9;
  border-radius: 4px;
  overflow: hidden;
}

.thumbnail-image {
  width: 100%;
  height: 100%;
}

.thumbnail-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumbnail-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666666;
  background: #f5f5f5;
}

.filename {
  flex: 1;
  font-size: 14px;
  color: #333333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.delete-icon {
  font-size: 16px;
  color: #333333;
  cursor: pointer;
  flex-shrink: 0;
}

.delete-icon:hover {
  color: #f56c6c;
}
</style>
