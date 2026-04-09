from enum import Enum
from datetime import datetime
import uuid
import json
import redis
import os

# Redis连接
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = int(os.getenv('REDIS_PORT', 6379))
redis_password = os.getenv('REDIS_PASSWORD', None)
redis_client = redis.Redis(host=redis_host, port=redis_port, password=redis_password, db=0, decode_responses=True)

class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class BatchTaskManager:
    """多用户隔离的批量任务管理器，通过 session_id 区分每个用户的任务"""
    def __init__(self):
        self.redis_client = redis_client
        self.task_prefix = "batch_task:"

    def _make_task_key(self, session_id, task_id):
        return f"{self.task_prefix}{session_id}:{task_id}"
    def _make_all_tasks_key(self, session_id):
        return f"{self.task_prefix}{session_id}:*"

    def create_task(self, session_id, images_data, prompt, api_type="gemini"):
        task_id = str(uuid.uuid4())
        task_data = {
            "task_id": task_id,
            "session_id": session_id,
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "total_images": len(images_data),
            "processed_images": 0,
            "failed_images": 0,
            "progress": 0.0,
            "prompt": prompt,
            "api_type": api_type,
            "images": [],
            "results": {
                "success_count": 0,
                "failed_count": 0,
                "generated_images": []
            }
        }
        for image_data in images_data:
            image_info = {
                "file_id": str(uuid.uuid4()),
                "filename": image_data.get('filename', ''),
                "status": TaskStatus.PENDING.value,
                "result_url": None,
                "error": None
            }
            task_data["images"].append(image_info)
        self.redis_client.setex(
            self._make_task_key(session_id, task_id),
            3600,  # 1小时过期
            json.dumps(task_data)
        )
        return task_id, task_data

    def get_task(self, session_id, task_id):
        task_data = self.redis_client.get(self._make_task_key(session_id, task_id))
        if task_data:
            return json.loads(task_data)
        return None

    def update_task_status(self, session_id, task_id, status, **kwargs):
        task_data = self.get_task(session_id, task_id)
        if task_data:
            task_data["status"] = status.value if isinstance(status, TaskStatus) else status
            task_data["updated_at"] = datetime.now().isoformat()
            for key, value in kwargs.items():
                task_data[key] = value
            self.redis_client.setex(
                self._make_task_key(session_id, task_id),
                3600,
                json.dumps(task_data)
            )
            return task_data
        return None

    def update_task_progress(self, session_id, task_id, progress, current_image=None):
        task_data = self.get_task(session_id, task_id)
        if task_data:
            task_data["progress"] = progress
            task_data["processed_images"] = int((progress / 100) * task_data["total_images"])
            if current_image:
                task_data["current_image"] = current_image
            task_data["updated_at"] = datetime.now().isoformat()
            self.redis_client.setex(
                self._make_task_key(session_id, task_id),
                3600,
                json.dumps(task_data)
            )
            return task_data
        return None

    def add_task_result(self, session_id, task_id, image_filename, result):
        task_data = self.get_task(session_id, task_id)
        if task_data:
            for image in task_data["images"]:
                if image["filename"] == image_filename:
                    if result["success"]:
                        image["status"] = TaskStatus.COMPLETED.value
                        result_url = result.get("generated_image_url") or result.get("generated_video_url")
                        image["result_url"] = result_url
                        task_data["results"]["success_count"] += 1
                        generated_image = {
                            "filename": image_filename,
                            "generated_url": result_url,
                            "generated_filename": result.get("generated_filename"),
                            "prompt": result.get("prompt"),
                            "is_video": result.get("is_video", False),
                            "last_frame_url": result.get("last_frame_url"),
                            "resolution": result.get("resolution"),
                            "ratio": result.get("ratio"),
                            "duration": result.get("duration"),
                            "generate_audio": result.get("generate_audio"),
                        }
                        task_data["results"]["generated_images"].append(generated_image)
                    else:
                        image["status"] = TaskStatus.FAILED.value
                        image["error"] = result.get("error")
                        task_data["results"]["failed_count"] += 1
                        # 将失败结果也加入 generated_images，便于前端统一合并渲染
                        failed_image_entry = {
                            "filename": image_filename,
                            "generated_url": None,
                            "generated_filename": None,
                            "error": result.get("error"),
                            "prompt": result.get("prompt"),
                            "is_video": result.get("is_video", False)
                        }
                        task_data["results"]["generated_images"].append(failed_image_entry)
                    break
            completed_count = task_data["results"]["success_count"] + task_data["results"]["failed_count"]
            if completed_count >= task_data["total_images"]:
                task_data["status"] = TaskStatus.COMPLETED.value
                task_data["progress"] = 100.0
            else:
                task_data["progress"] = (completed_count / task_data["total_images"]) * 100
            task_data["updated_at"] = datetime.now().isoformat()
            self.redis_client.setex(
                self._make_task_key(session_id, task_id),
                3600,
                json.dumps(task_data)
            )
            return task_data
        return None

    def cancel_task(self, session_id, task_id):
        return self.update_task_status(session_id, task_id, TaskStatus.CANCELLED)

    def get_all_tasks(self, session_id):
        tasks = []
        try:
            keys = self.redis_client.keys(self._make_all_tasks_key(session_id))
            for key in keys:
                try:
                    task_data = self.redis_client.get(key)
                    if task_data:
                        tasks.append(json.loads(task_data))
                except (json.JSONDecodeError, Exception) as e:
                    # 如果某个任务数据损坏，跳过它
                    print(f"Error parsing task data for key {key}: {str(e)}")
                    continue
            return sorted(tasks, key=lambda x: x.get("created_at", ""), reverse=True)
        except Exception as e:
            # Redis连接错误或其他错误
            print(f"Error getting tasks from Redis: {str(e)}")
            return []

    def delete_task(self, session_id, task_id):
        return self.redis_client.delete(self._make_task_key(session_id, task_id))

# 全局任务管理器实例
task_manager = BatchTaskManager()
