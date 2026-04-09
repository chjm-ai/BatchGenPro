#!/usr/bin/env python3
"""
视频生成功能模块
支持 Sora 和豆包 Seedance
"""
import os
import uuid
import base64
import requests
import json
from dotenv import load_dotenv

load_dotenv()

RESULT_FOLDER = os.getenv('RESULT_FOLDER', 'results')


class VideoGenerator:
    """视频生成器基类"""

    def __init__(self, api_key, model_name, base_url=None):
        self.api_key = api_key
        self.model = model_name
        self.result_folder = RESULT_FOLDER
        os.makedirs(self.result_folder, exist_ok=True)

    def generate(self, prompt, media_inputs=None, options=None, duration=None):
        """生成视频 - 子类实现"""
        raise NotImplementedError


class SoraVideoGenerator(VideoGenerator):
    """Sora 视频生成器 (yunwu.ai)"""

    def __init__(self, api_key, model_name, base_url=None):
        super().__init__(api_key, model_name, base_url)
        self.base_url = base_url or "https://yunwu.ai"

        # 验证 API key
        if not self.api_key:
            raise ValueError("Sora API Key 未提供")

    def generate(self, prompt, media_inputs=None, options=None, duration=None):
        """生成视频"""
        try:
            print(f"  [Sora] 开始生成视频，prompt: {prompt[:50]}...")
            image_urls = self._extract_image_urls(media_inputs)

            model_name = self.model if self.model else "sora-2-all"
            request_data = {
                "model": model_name,
                "prompt": prompt,
                "orientation": "portrait",
                "size": "large",
                "duration": duration or 10,
                "watermark": False
            }

            if image_urls:
                request_data["images"] = image_urls
                print(f"  [Sora] 已添加 {len(image_urls)} 张参考图片")

            endpoint = f"{self.base_url}/v1/video/create"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            print(f"  [Sora] 发送请求到: {endpoint}")

            response = requests.post(
                endpoint,
                headers=headers,
                json=request_data,
                timeout=300
            )

            print(f"  [Sora] 响应状态: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                return self._process_response(result, prompt)
            else:
                error_msg = f"Sora API请求失败: {response.status_code}"
                error_details = f"URL: {endpoint}, Model: {model_name}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = f"{error_msg} - {error_data['error']}"
                    elif "message" in error_data:
                        error_msg = f"{error_msg} - {error_data['message']}"
                    else:
                        error_msg = f"{error_msg} - {response.text}"
                except:
                    error_msg = f"{error_msg} - {response.text}"

                print(f"  [Sora] {error_details}")
                return {"success": False, "error": f"{error_msg} ({error_details})", "api_type": "sora"}

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Sora API请求超时，视频生成可能需要更长时间",
                "api_type": "sora"
            }
        except Exception as e:
            print(f"  [Sora] 生成视频时发生错误: {str(e)}")
            return {"success": False, "error": f"生成视频失败: {str(e)}", "api_type": "sora"}

    def _extract_image_urls(self, media_inputs):
        """兼容旧的图片列表与新的多模态结构"""
        if not media_inputs:
            return []
        if isinstance(media_inputs, list):
            return media_inputs
        if isinstance(media_inputs, dict):
            return media_inputs.get("images", [])
        return []

    def _process_response(self, response_data, prompt):
        """处理响应"""
        try:
            if "data" in response_data and len(response_data["data"]) > 0:
                video_info = response_data["data"][0]

                if "url" in video_info:
                    return self._save_video(video_info["url"], prompt)
                elif "b64_json" in video_info:
                    video_bytes = base64.b64decode(video_info["b64_json"])
                    return self._save_video_bytes(video_bytes, prompt)

            elif "id" in response_data:
                video_id = response_data["id"]
                return {
                    "success": True,
                    "description": f"视频生成任务已提交: {prompt}",
                    "video_id": video_id,
                    "generated_video_url": None,
                    "api_type": "sora",
                    "note": "视频生成中，请稍后刷新查看结果",
                    "is_processing": True
                }

            return {
                "success": False,
                "error": "Sora API响应格式异常",
                "response": response_data,
                "api_type": "sora"
            }

        except Exception as e:
            return {"success": False, "error": f"处理响应失败: {str(e)}", "api_type": "sora"}

    def _save_video(self, video_url, prompt):
        """下载并保存视频"""
        try:
            print(f"  [Sora] 正在下载视频: {video_url[:60]}...")
            response = requests.get(video_url, timeout=60)
            if response.status_code == 200:
                return self._save_video_bytes(response.content, prompt)
            else:
                return {"success": False, "error": f"下载视频失败: {response.status_code}", "api_type": "sora"}
        except Exception as e:
            return {"success": False, "error": f"下载视频失败: {str(e)}", "api_type": "sora"}

    def _save_video_bytes(self, video_bytes, prompt):
        """保存视频字节到文件"""
        try:
            filename = f"sora_generated_{uuid.uuid4()}.mp4"
            filepath = os.path.join(self.result_folder, filename)

            with open(filepath, 'wb') as f:
                f.write(video_bytes)

            print(f"  [Sora] 视频已保存: {filepath}")

            return {
                "success": True,
                "description": f"成功生成视频: {prompt}",
                "generated_video_url": f"/static/results/{filename}",
                "api_type": "sora",
                "note": "视频已生成"
            }
        except Exception as e:
            return {"success": False, "error": f"保存视频失败: {str(e)}", "api_type": "sora"}


class DoubaoVideoGenerator(VideoGenerator):
    """豆包 Seedance 视频生成器 (火山方舟)"""

    def __init__(self, api_key, model_name, base_url=None):
        super().__init__(api_key, model_name, base_url)
        self.base_url = base_url or "https://ark.cn-beijing.volces.com/api/v3"

        # 验证 API key
        if not self.api_key:
            raise ValueError("豆包 API Key 未提供")

    def generate(self, prompt, media_inputs=None, options=None, duration=None):
        """生成视频任务"""
        try:
            print(f"  [Seedance] 开始生成视频，prompt: {prompt[:50]}...")
            print(f"  [Seedance] base_url: {self.base_url}")

            model_name = self.model if self.model else "doubao-seedance-2-0-260128"
            normalized_media = self._normalize_media_inputs(media_inputs)
            normalized_options = self._normalize_options(options, duration)
            request_data = {
                "model": model_name,
                "content": self._build_content(prompt, normalized_media),
                **normalized_options,
            }

            endpoint = f"{self.base_url}/contents/generations/tasks"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            print(f"  [Seedance] 发送请求到: {endpoint}")
            print(f"  [Seedance] 模型: {model_name}")

            response = requests.post(
                endpoint,
                headers=headers,
                json=request_data,
                timeout=300
            )

            print(f"  [Seedance] 响应状态: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                return self._process_response(result, prompt, max_retries=30, retry_interval=10)
            else:
                error_msg = f"豆包 Seedance API请求失败: {response.status_code}"
                error_details = f"URL: {endpoint}, Model: {model_name}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = f"{error_msg} - {error_data['error']}"
                    elif "message" in error_data:
                        error_msg = f"{error_msg} - {error_data['message']}"
                    else:
                        error_msg = f"{error_msg} - {response.text}"
                except:
                    error_msg = f"{error_msg} - {response.text}"

                print(f"  [Seedance] {error_details}")
                return {"success": False, "error": f"{error_msg} ({error_details})", "api_type": "doubao"}

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Seedance API请求超时，视频生成可能需要更长时间",
                "api_type": "doubao"
            }
        except Exception as e:
            print(f"  [Seedance] 生成视频时发生错误: {str(e)}")
            return {"success": False, "error": f"生成视频失败: {str(e)}", "api_type": "doubao"}

    def _process_response(self, response_data, prompt, max_retries=30, retry_interval=10):
        """处理响应，支持轮询查询任务状态"""
        try:
            print(f"  [Seedance] 响应数据: {response_data}")

            # 检查是否有任务 ID
            if "id" not in response_data:
                return {
                    "success": False,
                    "error": "Seedance API响应格式异常，缺少任务ID",
                    "response": response_data,
                    "api_type": "doubao"
                }

            task_id = response_data["id"]
            status = response_data.get("status", "queued")

            # 如果任务已完成，直接返回
            if status == "succeeded":
                video_url = self._extract_video_url(response_data)
                if video_url:
                    return self._save_video(video_url, prompt)

                return {
                    "success": True,
                    "description": f"视频生成完成: {prompt}",
                    "task_id": task_id,
                    "api_type": "doubao",
                    "note": "视频已生成但URL获取失败"
                }

            # 任务未完成，需要轮询查询状态
            print(f"  [Seedance] 任务 {task_id} 当前状态: {status}，开始轮询...")

            import time
            for attempt in range(max_retries):
                time.sleep(retry_interval)

                # 查询任务状态
                query_result = self._query_task_status(task_id)

                if not query_result.get("success"):
                    return query_result

                status = query_result.get("status", "unknown")
                print(f"  [Seedance] 轮询 {attempt + 1}/{max_retries}，状态: {status}")

                if status == "succeeded":
                    video_url = query_result.get("video_url")
                    if video_url:
                        result = self._save_video(video_url, prompt)
                        if query_result.get("last_frame_url"):
                            result["last_frame_url"] = query_result["last_frame_url"]
                        for key in ("resolution", "ratio", "duration", "frames", "generate_audio"):
                            if key in query_result:
                                result[key] = query_result[key]
                        return result
                    else:
                        return {
                            "success": True,
                            "description": f"视频生成完成: {prompt}",
                            "task_id": task_id,
                            "api_type": "doubao",
                            "note": "视频已生成但URL获取失败"
                        }
                elif status == "failed":
                    error_msg = query_result.get("error", "任务执行失败")
                    return {
                        "success": False,
                        "error": f"视频生成失败: {error_msg}",
                        "task_id": task_id,
                        "api_type": "doubao"
                    }

            # 轮询次数耗尽
            return {
                "success": True,
                "description": f"视频生成任务已提交: {prompt}",
                "task_id": task_id,
                "status": status,
                "generated_video_url": None,
                "api_type": "doubao",
                "note": f"轮询次数耗尽，当前状态: {status}，请稍后手动刷新查看结果",
                "is_processing": True
            }

        except Exception as e:
            return {"success": False, "error": f"处理响应失败: {str(e)}", "api_type": "doubao"}

    def _query_task_status(self, task_id):
        """查询任务状态"""
        try:
            endpoint = f"{self.base_url}/contents/generations/tasks/{task_id}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            response = requests.get(endpoint, headers=headers, timeout=30)

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"查询任务状态失败: {response.status_code} - {response.text}"
                }

            result = response.json()
            status = result.get("status", "unknown")

            output_data = {
                "success": True,
                "status": status
            }

            if status == "succeeded":
                output_data["video_url"] = self._extract_video_url(result)
                output_data["last_frame_url"] = self._extract_last_frame_url(result)
                for key in ("resolution", "ratio", "duration", "frames", "generate_audio"):
                    if key in result:
                        output_data[key] = result[key]
            elif status == "failed":
                output_data["error"] = result.get("error", "未知错误")

            return output_data

        except Exception as e:
            return {"success": False, "error": f"查询任务状态异常: {str(e)}"}

    def _extract_video_url(self, response_data):
        """兼容不同返回结构提取视频地址"""
        if response_data.get("content", {}).get("video_url"):
            return response_data["content"]["video_url"]

        if response_data.get("output", {}).get("video_url"):
            return response_data["output"]["video_url"]

        return response_data.get("video_url")

    def _extract_last_frame_url(self, response_data):
        """兼容不同返回结构提取尾帧地址"""
        if response_data.get("content", {}).get("last_frame_url"):
            return response_data["content"]["last_frame_url"]

        if response_data.get("output", {}).get("last_frame_url"):
            return response_data["output"]["last_frame_url"]

        return response_data.get("last_frame_url")

    def _normalize_media_inputs(self, media_inputs):
        """统一视频输入结构，兼容旧版只传图片列表的调用方式"""
        if not media_inputs:
            return {"mode": "text", "images": [], "videos": [], "audios": []}

        if isinstance(media_inputs, list):
            return {
                "mode": "multimodal" if media_inputs else "text",
                "images": media_inputs,
                "videos": [],
                "audios": [],
            }

        normalized = {
            "mode": media_inputs.get("mode", "text"),
            "images": media_inputs.get("images", []),
            "videos": media_inputs.get("videos", []),
            "audios": media_inputs.get("audios", []),
            "first_frame": media_inputs.get("first_frame"),
            "last_frame": media_inputs.get("last_frame"),
        }
        return normalized

    def _normalize_options(self, options, duration):
        """统一并过滤 Seedance 2.0 可用参数"""
        normalized = {
            "resolution": "720p",
            "ratio": "adaptive",
            "duration": 5,
            "watermark": False,
            "generate_audio": True,
        }

        if isinstance(options, dict):
            normalized.update({
                key: value for key, value in options.items()
                if value is not None and key in {
                    "resolution", "ratio", "duration", "seed", "watermark", "generate_audio"
                }
            })

        if duration is not None and "duration" not in (options or {}):
            normalized["duration"] = duration

        return normalized

    def _build_content(self, prompt, media_inputs):
        """根据前端选择的模式构建 Seedance content 列表"""
        mode = media_inputs.get("mode", "text")
        content = []

        if mode == "first_frame" and media_inputs.get("first_frame"):
            content.append(self._build_image_item(media_inputs["first_frame"], "first_frame"))
        elif mode == "first_last_frame":
            if media_inputs.get("first_frame"):
                content.append(self._build_image_item(media_inputs["first_frame"], "first_frame"))
            if media_inputs.get("last_frame"):
                content.append(self._build_image_item(media_inputs["last_frame"], "last_frame"))
        else:
            for url in media_inputs.get("images", []):
                content.append(self._build_image_item(url, "reference_image"))
            for url in media_inputs.get("videos", []):
                content.append({
                    "type": "video_url",
                    "video_url": {"url": url},
                    "role": "reference_video"
                })
            for url in media_inputs.get("audios", []):
                content.append({
                    "type": "audio_url",
                    "audio_url": {"url": url},
                    "role": "reference_audio"
                })

        if prompt.strip():
            content.append({
                "type": "text",
                "text": prompt
            })

        return content

    def _build_image_item(self, url, role):
        return {
            "type": "image_url",
            "image_url": {"url": url},
            "role": role
        }

    def _save_video(self, video_url, prompt):
        """下载并保存视频"""
        try:
            print(f"  [Seedance] 正在下载视频...")
            response = requests.get(video_url, timeout=60)
            if response.status_code == 200:
                return self._save_video_bytes(response.content, prompt)
            else:
                return {"success": False, "error": f"下载视频失败: {response.status_code}", "api_type": "doubao"}
        except Exception as e:
            return {"success": False, "error": f"下载视频失败: {str(e)}", "api_type": "doubao"}

    def _save_video_bytes(self, video_bytes, prompt):
        """保存视频字节到文件"""
        try:
            filename = f"seedance_generated_{uuid.uuid4()}.mp4"
            filepath = os.path.join(self.result_folder, filename)

            with open(filepath, 'wb') as f:
                f.write(video_bytes)

            print(f"  [Seedance] 视频已保存: {filepath}")

            return {
                "success": True,
                "description": f"成功生成视频: {prompt}",
                "generated_video_url": f"/static/results/{filename}",
                "api_type": "doubao",
                "note": "视频已生成"
            }
        except Exception as e:
            return {"success": False, "error": f"保存视频失败: {str(e)}", "api_type": "doubao"}


def create_video_generator(api_type, api_key, model_name, base_url=None):
    """
    创建视频生成器工厂函数

    Args:
        api_type: 'sora' 或 'doubao'
        api_key: API 密钥
        model_name: 模型名称
        base_url: 自定义 base URL（可选）

    Returns:
        VideoGenerator: 视频生成器实例
    """
    if api_type == "doubao":
        return DoubaoVideoGenerator(api_key, model_name, base_url)
    else:
        return SoraVideoGenerator(api_key, model_name, base_url)
