from celery import current_task
from celery_config import celery_app
import sys
import os
from google import genai
from PIL import Image
import io
import uuid
import time
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 从环境变量读取配置
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-image')
RESULT_FOLDER = os.getenv('RESULT_FOLDER', 'results')

@celery_app.task(bind=True)
def generate_single_image(self, file_data, filename, prompt, task_id):
    """
    生成单张图片的Celery任务
    
    Args:
        file_data: 图片文件的二进制数据
        filename: 文件名
        prompt: 生成提示词
        task_id: 任务ID
    
    Returns:
        dict: 包含生成结果的字典
    """
    try:
        # 更新任务状态
        self.update_state(
            state='PROGRESS',
            meta={'status': 'processing', 'filename': filename}
        )
        
        # 注意：已移除服务器默认 API key，此函数已废弃
        # 现在所有生成都通过 AIImageGenerator 进行，必须使用用户提供的 API key
        raise ValueError("此函数已废弃，请使用批量生成接口")
        
        # 将二进制数据转换为PIL Image
        image = Image.open(io.BytesIO(file_data))
        
        # 调用Gemini API生成图片
        full_prompt = f"Create a picture of my image with the following changes: {prompt}"
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[full_prompt, image]
        )
        
        # 处理响应
        if response and hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        # 保存生成的图片
                        generated_filename = f"generated_{uuid.uuid4()}.png"
                        generated_path = os.path.join(RESULT_FOLDER, generated_filename)
                        
                        with open(generated_path, 'wb') as f:
                            f.write(part.inline_data.data)
                        
                        return {
                            'success': True,
                            'filename': filename,
                            'generated_filename': generated_filename,
                            'generated_url': f"/static/results/{generated_filename}",
                            'description': f"Successfully generated image for {filename}"
                        }
        
        # 如果没有生成图片，返回描述
        return {
            'success': True,
            'filename': filename,
            'generated_filename': None,
            'generated_url': None,
            'description': f"Processed {filename} but no image was generated"
        }
        
    except Exception as e:
        # 记录错误但不抛出异常，避免Celery错误处理问题
        print(f"Error generating image for {filename}: {str(e)}")
        return {
            'success': False,
            'filename': filename,
            'error': str(e)
        }

@celery_app.task(bind=True)
def process_batch_task(self, batch_data):
    """
    处理批量任务的Celery任务
    
    Args:
        batch_data: 批量任务数据
    
    Returns:
        dict: 批量任务结果
    """
    try:
        task_id = batch_data['task_id']
        images = batch_data['images']
        prompt = batch_data['prompt']
        
        results = []
        total_images = len(images)
        
        # 更新任务状态为处理中
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 0,
                'current_image': 0,
                'total_images': total_images
            }
        )
        
        for i, image_data in enumerate(images):
            # 更新进度
            progress = (i / total_images) * 100
            self.update_state(
                state='PROGRESS',
                meta={
                    'status': 'processing',
                    'progress': progress,
                    'current_image': i + 1,
                    'total_images': total_images,
                    'filename': image_data['filename']
                }
            )
            
            # 调用单图片生成任务
            result = generate_single_image.delay(
                image_data['file_data'],
                image_data['filename'],
                prompt,
                task_id
            ).get()
            
            results.append(result)
            
            # 短暂延迟，避免API限制
            time.sleep(1)
        
        # 异步更新任务结果
        update_task_results.delay(task_id, results)
        
        return {
            'success': True,
            'task_id': task_id,
            'results': results,
            'total_images': total_images,
            'completed_images': len(results)
        }
        
    except Exception as e:
        print(f"Error processing batch task: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

@celery_app.task(bind=True)
def update_task_results(self, task_id, results):
    """
    更新任务结果的Celery任务
    
    Args:
        task_id: 任务ID
        results: 任务结果列表
    
    Returns:
        dict: 更新结果
    """
    try:
        from task_manager import task_manager
        
        # 更新任务状态为处理中
        task_manager.update_task_status(task_id, 'processing')
        
        # 处理每个结果
        for result in results:
            if result['success']:
                task_manager.add_task_result(task_id, result['filename'], result)
            else:
                task_manager.add_task_result(task_id, result['filename'], result)
        
        # 更新任务状态为完成
        task_manager.update_task_status(task_id, 'completed')
        
        return {
            'success': True,
            'task_id': task_id,
            'message': 'Task results updated successfully'
        }
        
    except Exception as e:
        print(f"Error updating task results: {str(e)}")
        from task_manager import task_manager
        task_manager.update_task_status(task_id, 'failed')
        return {
            'success': False,
            'error': str(e)
        }

def process_batch_task_sync(session_id, task_id, images_data, prompt, api_type="gemini", api_key=None, model_name=None, base_url=None):
    """
    同步处理批量任务（不使用Celery）
    
    Args:
        task_id: 任务ID
        images_data: 图片数据列表
        prompt: 生成提示词
        api_type: API类型 ("gemini" 或 "doubao")
        api_key: API密钥（可选）
        model_name: 模型名称（可选）
        base_url: 自定义 base URL（可选，用于第三方 API）
    
    Returns:
        dict: 批量任务结果
    """
    try:
        from task_manager import task_manager
        
        results = []
        total_images = len(images_data)
        
        for i, image_data in enumerate(images_data):
            # 更新进度
            progress = (i / total_images) * 100
            task_manager.update_task_progress(session_id, task_id, progress, i + 1)
            
            # 使用统一的API生成器
            from ai_image_generator import create_image_generator
            # 必须使用用户提供的API key，不再使用服务器配置
            generator = create_image_generator(api_type, api_key, model_name, base_url)
            result = generator.generate_image(image_data['file_data'], prompt)
            
            results.append(result)
            
            # 更新任务结果
            task_manager.add_task_result(session_id, task_id, image_data['filename'], result)
            
            # 短暂延迟，避免API限制
            time.sleep(1)
        
        return {
            'success': True,
            'task_id': task_id,
            'results': results,
            'total_images': total_images,
            'completed_images': len(results)
        }
        
    except Exception as e:
        print(f"Error processing batch task sync: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def generate_single_image_sync(file_data, filename, prompt, task_id):
    """
    同步生成单张图片（不使用Celery）
    
    Args:
        file_data: 图片文件的二进制数据
        filename: 文件名
        prompt: 生成提示词
        task_id: 任务ID
    
    Returns:
        dict: 包含生成结果的字典
    """
    try:
        # 注意：已移除服务器默认 API key，此函数已废弃
        # 现在所有生成都通过 AIImageGenerator 进行，必须使用用户提供的 API key
        raise ValueError("此函数已废弃，请使用批量生成接口")
        
        # 将二进制数据转换为PIL Image
        image = Image.open(io.BytesIO(file_data))
        
        # 调用Gemini API生成图片
        full_prompt = f"Create a picture of my image with the following changes: {prompt}"
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[full_prompt, image]
        )
        
        # 处理响应
        if response and hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        # 保存生成的图片
                        generated_filename = f"generated_{uuid.uuid4()}.png"
                        generated_path = os.path.join(RESULT_FOLDER, generated_filename)
                        
                        with open(generated_path, 'wb') as f:
                            f.write(part.inline_data.data)
                        
                        return {
                            'success': True,
                            'filename': filename,
                            'generated_filename': generated_filename,
                            'generated_url': f"/static/results/{generated_filename}",
                            'description': f"Successfully generated image for {filename}"
                        }
        
        # 如果没有生成图片，返回描述
        return {
            'success': True,
            'filename': filename,
            'generated_filename': None,
            'generated_url': None,
            'description': f"Processed {filename} but no image was generated"
        }
        
    except Exception as e:
        print(f"Error generating image for {filename}: {str(e)}")
        return {
            'success': False,
            'filename': filename,
            'error': str(e)
        }

def process_batch_generate_sync(session_id, task_id, reference_image_data, prompt, image_count, api_type="gemini", api_key=None, model_name=None, base_url=None):
    """
    批量生图：使用同一张参考图和prompt重复生成多张图片
    
    Args:
        task_id: 任务ID
        reference_image_data: 参考图片的二进制数据
        prompt: 生成提示词
        image_count: 生成图片数量
        api_type: API类型 ("gemini" 或 "doubao")
        api_key: API密钥（可选）
        model_name: 模型名称（可选）
        base_url: 自定义 base URL（可选，用于第三方 API）
    
    Returns:
        dict: 批量任务结果
    """
    try:
        from task_manager import task_manager
        
        results = []
        total_images = image_count
        
        for i in range(image_count):
            # 更新进度
            progress = (i / total_images) * 100
            task_manager.update_task_progress(session_id, task_id, progress, i + 1)
            
            # 生成文件名
            filename = f"generated_{i+1}.png"
            
            print(f"  [任务处理] 使用 {api_type}，模型: {model_name}, base_url: {base_url}")
            
            # 使用统一的API生成器
            from ai_image_generator import create_image_generator
            # 如果没有提供API key，传递None，让create_image_generator使用服务器配置的
            print(f"  [任务处理] 创建生成器: api_type={api_type}, model={model_name}, base_url={base_url}")
            generator = create_image_generator(api_type, api_key, model_name, base_url)
            print(f"  [任务处理] 生成器类型: {type(generator).__name__}")
            print(f"  [任务处理] 开始生成图片...")
            result = generator.generate_image(reference_image_data, prompt)
            print(f"  [任务处理] 生成结果: success={result.get('success')}, error={result.get('error', 'N/A')}")
            
            # 添加文件名信息
            if result['success']:
                result['filename'] = filename
            else:
                result['filename'] = filename
            
            results.append(result)
            
            # 更新任务结果
            task_manager.add_task_result(session_id, task_id, filename, result)
            
            # 短暂延迟，避免API限制
            time.sleep(1)
        
        return {
            'success': True,
            'task_id': task_id,
            'results': results,
            'total_images': total_images,
            'completed_images': len(results)
        }
        
    except Exception as e:
        print(f"Error processing batch generate sync: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def process_batch_generate_multi_prompt_sync(session_id, task_id, reference_image_data, prompts, api_type="gemini", api_key=None, model_name=None, base_url=None):
    """
    批量生图：使用同一张参考图，但每个prompt生成一张图片（用于变量功能）
    
    Args:
        task_id: 任务ID
        reference_image_data: 参考图片的二进制数据（可选）
        prompts: 提示词列表
        api_type: API类型 ("gemini" 或 "doubao")
        api_key: API密钥（可选）
        model_name: 模型名称（可选）
        base_url: 自定义 base URL（可选，用于第三方 API）
    
    Returns:
        dict: 批量任务结果
    """
    try:
        from task_manager import task_manager
        
        results = []
        total_images = len(prompts)
        
        for i, prompt in enumerate(prompts):
            # 更新进度
            progress = (i / total_images) * 100
            task_manager.update_task_progress(session_id, task_id, progress, i + 1)
            
            # 生成文件名
            filename = f"generated_{i+1}.png"
            
            print(f"  [任务处理] 使用 {api_type}，模型: {model_name}, base_url: {base_url}")
            
            # 使用统一的API生成器
            from ai_image_generator import create_image_generator
            # 如果没有提供API key，传递None，让create_image_generator使用服务器配置的
            print(f"  [任务处理] 创建生成器: api_type={api_type}, model={model_name}, base_url={base_url}")
            generator = create_image_generator(api_type, api_key, model_name, base_url)
            print(f"  [任务处理] 生成器类型: {type(generator).__name__}")
            print(f"  [任务处理] 开始生成图片...")
            result = generator.generate_image(reference_image_data, prompt)
            print(f"  [任务处理] 生成结果: success={result.get('success')}, error={result.get('error', 'N/A')}")
            
            # 添加文件名信息和prompt
            if result['success']:
                result['filename'] = filename
            else:
                result['filename'] = filename
            
            result['prompt'] = prompt  # 保存每个item的具体prompt
            
            results.append(result)
            
            # 更新任务结果
            task_manager.add_task_result(session_id, task_id, filename, result)
            
            # 短暂延迟，避免API限制
            time.sleep(1)
        
        return {
            'success': True,
            'task_id': task_id,
            'results': results,
            'total_images': total_images,
            'completed_images': len(results)
        }
        
    except Exception as e:
        print(f"Error processing batch generate multi-prompt sync: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def process_video_generate_sync(
    session_id,
    task_id,
    media_inputs,
    prompt,
    api_type="sora",
    api_key=None,
    model_name=None,
    base_url=None,
    duration=None,
    options=None,
):
    """
    同步处理视频生成任务

    Args:
        session_id: 会话ID
        task_id: 任务ID
        media_inputs: 视频生成输入素材
        prompt: 视频生成提示词
        api_type: API类型（'sora' 或 'doubao'）
        api_key: API密钥
        model_name: 模型名称
        base_url: 自定义 base URL（可选）

    Returns:
        dict: 视频生成任务结果
    """
    try:
        from task_manager import task_manager

        api_name = "豆包" if api_type == "doubao" else "Sora"
        print(f"  [视频生成任务] 使用 {api_name} API，模型: {model_name}, api_type: {api_type}, base_url: {base_url}")
        media_summary = media_inputs if isinstance(media_inputs, dict) else {"images": media_inputs or []}
        print(
            "  [视频生成任务] 输入素材:"
            f" 图片={len(media_summary.get('images', []))}"
            f", 视频={len(media_summary.get('videos', []))}"
            f", 音频={len(media_summary.get('audios', []))}"
            f", 模式={media_summary.get('mode', 'legacy')}"
        )

        # 更新进度
        task_manager.update_task_progress(session_id, task_id, 10, 0)

        # 使用视频生成器
        from video_generator import create_video_generator
        generator = create_video_generator(api_type, api_key, model_name, base_url)

        # 更新进度
        task_manager.update_task_progress(session_id, task_id, 30, 0)

        # 生成视频
        print(f"  [视频生成任务] 开始生成视频...")
        result = generator.generate(prompt, media_inputs=media_inputs, options=options, duration=duration)
        print(f"  [视频生成任务] 生成结果: success={result.get('success')}, error={result.get('error', 'N/A')}")

        # 更新进度
        task_manager.update_task_progress(session_id, task_id, 90, 1)

        filename = "video_1.mp4"

        # 添加文件名信息
        result['filename'] = filename
        result['is_video'] = True
        result['prompt'] = prompt

        # 更新任务结果
        task_manager.add_task_result(session_id, task_id, filename, result)

        # 更新进度为100%
        task_manager.update_task_progress(session_id, task_id, 100, 1)

        return {
            'success': result.get('success', False),
            'task_id': task_id,
            'results': [result],
            'total_videos': 1,
            'completed_videos': 1,
            'error': result.get('error')
        }

    except Exception as e:
        print(f"Error processing video generate sync: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
