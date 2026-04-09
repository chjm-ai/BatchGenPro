# Seedance Video Models Design

**目标**

在现有视频生成功能基础上，移除 `Seedance 1.5 Pro`，接入并默认支持火山方舟当前官方视频模型 `Seedance 2.0` 与 `Seedance 2.0 fast`，同时把豆包视频生成调用切换到官方最新 `contents/generations/tasks` API。

**范围**

- 前端视频模型列表只保留：
  - `doubao-seedance-2-0-260128`
  - `doubao-seedance-2-0-fast-260128`
  - `sora-2`
- 前端视频页的 API 配置校验，必须根据所选视频模型的 `apiType` 动态判断，不能再写死 `sora`
- 后端豆包视频生成接口改为：
  - 创建任务：`POST /api/v3/contents/generations/tasks`
  - 查询任务：`GET /api/v3/contents/generations/tasks/{id}`
- 后端继续保留当前“上传参考图 -> 生成公网 URL -> 提交给模型”的调用方式

**不做**

- 不接入参考视频、参考音频、draft task
- 不改任务管理器的数据结构
- 不新增前端测试框架

**实现方案**

后端以 `backend/video_generator.py` 为唯一豆包视频接入点，修正接口路径、默认模型和查询逻辑；前端以 `frontend/src/App.vue` 和 `frontend/src/utils/apiConfig.js` 为主，更新视频模型列表与视频页 API 判断逻辑。保留现有 Sora 路径，不重构已有批量任务流程。

**验证**

- 后端单元测试覆盖豆包视频创建路径、查询路径、默认模型名
- 手动验证视频页：
  - 选择 `Seedance 2.0` 时提示配置豆包，而不是 Sora
  - 选择 `Seedance 2.0 fast` 时同上
  - 不再出现 `Seedance 1.5 Pro`
