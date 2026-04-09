from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import uuid
import sys
import redis
import base64
from google import genai
from PIL import Image
import io
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai_image_generator import create_image_generator

# 从环境变量读取配置
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-image')
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
RESULT_FOLDER = os.getenv('RESULT_FOLDER', 'results')
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 10 * 1024 * 1024))  # 默认10MB
ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'png,jpg,jpeg,gif,webp').split(','))
SUPPORTED_APIS = os.getenv('SUPPORTED_APIS', 'gemini,doubao').split(',')
VIDEO_ALLOWED_EXTENSIONS = {'mp4', 'mov'}
AUDIO_ALLOWED_EXTENSIONS = {'mp3', 'wav'}

# V2阶段：导入批量任务相关模块
from task_manager import task_manager, TaskStatus
from tasks import process_batch_task

# 导入每日限额管理器
from daily_limit_manager import daily_limit_manager

# 注意：已移除认证和积分体系，用户只需提供自己的 API Key 即可使用

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
CORS(app)  # 启用CORS支持

# 配置Gemini API - 使用新的google-genai包
# 注意：现在只使用用户提供的API key，不再使用配置文件中的
# client = genai.Client(api_key=GEMINI_API_KEY)  # 已禁用，只能使用用户配置的API key

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_media_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def parse_bool_form_value(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def save_uploaded_media_files(field_name, allowed_extensions, multiple=True):
    """保存上传媒体并返回可访问 URL 列表"""
    if multiple:
        files = request.files.getlist(field_name)
    else:
        single_file = request.files.get(field_name)
        files = [single_file] if single_file else []

    saved_urls = []
    for file in files:
        if not file or not file.filename:
            continue
        if not allowed_media_file(file.filename, allowed_extensions):
            continue

        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        new_filename = f"{file_id}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, new_filename)
        file.save(file_path)

        host = request.host_url.rstrip('/')
        saved_urls.append(f"{host}/static/uploads/{new_filename}")

    return saved_urls


def encode_uploaded_files_as_data_urls(field_name, allowed_extensions, mime_prefix, multiple=True):
    """将上传文件编码为 data URL，适合图片和音频直传模型"""
    if multiple:
        files = request.files.getlist(field_name)
    else:
        single_file = request.files.get(field_name)
        files = [single_file] if single_file else []

    encoded_values = []
    for file in files:
        if not file or not file.filename:
            continue
        if not allowed_media_file(file.filename, allowed_extensions):
            continue

        extension = file.filename.rsplit('.', 1)[1].lower()
        file_bytes = file.read()
        file.seek(0)
        encoded = base64.b64encode(file_bytes).decode('utf-8')
        encoded_values.append(f"data:{mime_prefix}/{extension};base64,{encoded}")

    return encoded_values

def generate_image_with_gemini(image_path, prompt, api_key=None):
    """使用Gemini API生成图片（已废弃，现在使用AIImageGenerator）"""
    # 这个函数已经不再使用，保留只是为了兼容性
    # 现在所有生成都通过 AIImageGenerator 进行
    return {
        "success": False,
        "error": "此接口已废弃，请使用批量生成接口"
    }

@app.route('/api/generate', methods=['POST'])
def generate_image():
    """单图生成接口"""
    try:
        # 获取模型名称（从form或header）
        model_name = request.form.get('model_name') or request.headers.get('X-Model-Name')
        if not model_name:
            model_name = 'gemini-2.5-flash-image'  # 默认模型
        
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        prompt = request.form.get('prompt', '')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        if not prompt.strip():
            return jsonify({'error': 'Prompt is required'}), 400
        
        # 保存上传的文件
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        # 调用Gemini API（使用统一的AIImageGenerator）
        # 获取API key（必须提供，不再使用服务器配置）
        api_key, api_type = get_api_key_from_request()
        
        from ai_image_generator import create_image_generator
        # 获取 base_url（可选）
        base_url = get_base_url_from_request('gemini')
        # 必须提供API key
        generator = create_image_generator('gemini', api_key, model_name, base_url)
        with open(file_path, 'rb') as f:
            file_data = f.read()
        result = generator.generate_image(file_data, prompt)
        
        if result['success']:
            response_data = {
                'success': True,
                'original_url': f'/static/uploads/{unique_filename}',
                'description': result['description'],
                'note': result['note']
            }
            
            # 如果有生成的图像，添加图像URL
            if 'generated_image_url' in result:
                response_data['generated_image_url'] = result['generated_image_url']
            else:
                # 保存结果描述到文件（如果没有生成图像）
                result_filename = f"result_{uuid.uuid4()}.txt"
                result_path = os.path.join(RESULT_FOLDER, result_filename)
                with open(result_path, 'w', encoding='utf-8') as f:
                    f.write(result['description'])
                response_data['result_url'] = f'/static/results/{result_filename}'
            
            return jsonify(response_data)
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
            
    except Exception as e:
        error_msg = str(e)
        app.logger.error(f"Generate image error: {error_msg}")
        return jsonify({'success': False, 'error': f'生成失败: {error_msg}'}), 500

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    """提供上传文件的访问"""
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/static/results/<filename>')
def result_file(filename):
    """提供结果文件的访问"""
    return send_from_directory(RESULT_FOLDER, filename)

@app.route('/api/health')
def health_check():
    """健康检查接口"""
    return jsonify({'status': 'healthy', 'message': 'BatchGen Pro MVP is running'})

# 注意：已移除认证和积分相关API，用户只需提供自己的 API Key 即可使用

def get_session_id_or_abort():
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        return None
    return session_id

def get_api_key_from_request():
    """从请求header中获取API key和类型"""
    api_key = request.headers.get('X-API-Key')
    # 必须提供API key，不再使用服务器配置的key
    if not api_key or not api_key.strip():
        raise ValueError("API Key 未提供，请先在设置中配置 API Key")
    api_key = api_key.strip()
    api_type = request.headers.get('X-API-Type', 'gemini')
    return api_key, api_type

def get_base_url_from_request(api_type="gemini"):
    """从请求中获取 base_url 配置"""
    # 根据 API 类型选择对应的 header
    if api_type == "gemini":
        header_name = 'X-Gemini-Base-URL'
        form_key = 'gemini_base_url'
    elif api_type == "doubao":
        header_name = 'X-Doubao-Base-URL'
        form_key = 'doubao_base_url'
    elif api_type == "sora":
        header_name = 'X-Sora-Base-URL'
        form_key = 'sora_base_url'
    else:
        return None
    
    # 优先从header获取
    base_url = request.headers.get(header_name)
    if not base_url:
        # 从form data获取
        base_url = request.form.get(form_key)
    
    # 如果base_url是空字符串，转换为None
    if base_url and base_url.strip():
        base_url = base_url.strip().rstrip('/')
    else:
        base_url = None
    
    return base_url

# ==================== V2阶段：批量生成API ====================

@app.route('/api/batch/generate', methods=['POST'])
def create_batch_task():
    """创建批量生成任务（需要登录）"""
    session_id = get_session_id_or_abort()
    if not session_id:
        return jsonify({'error': '缺少 Session-ID'}), 400
    
    # 获取API key（必须提供）
    try:
        api_key, api_type = get_api_key_from_request()
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    
    try:
        # 检查是否有文件
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        prompt = request.form.get('prompt', '')
        api_type = request.form.get('api_type', 'gemini')
        
        if not files or all(file.filename == '' for file in files):
            return jsonify({'error': 'No files selected'}), 400
        
        if not prompt.strip():
            return jsonify({'error': 'Prompt is required'}), 400
        
        if api_type not in SUPPORTED_APIS:
            return jsonify({'error': f'Unsupported API type: {api_type}'}), 400
        
        # 验证文件
        valid_files = []
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                valid_files.append(file)
        
        if not valid_files:
            return jsonify({'error': 'No valid files provided'}), 400
        
        # 获取模型名称
        model_name = request.form.get('model_name')
        if not model_name:
            model_name = 'gemini-2.5-flash-image'  # 默认模型
        
        # 准备图片数据
        image_count = len(valid_files)
        images_data = []
        for file in valid_files:
            filename = secure_filename(file.filename)
            file_id = str(uuid.uuid4())
            new_filename = f"{file_id}_{filename}"
            
            # 保存文件
            file_path = os.path.join(UPLOAD_FOLDER, new_filename)
            file.save(file_path)
            
            # 读取文件数据
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            images_data.append({
                'filename': filename,
                'file_data': file_data,
                'file_path': file_path
            })
        
        # 创建批量任务
        task_id, task_data = task_manager.create_task(session_id, images_data, prompt, api_type)
        
        # 添加items字段，让前端能够显示所有任务项
        task_data['items'] = []
        for i, image in enumerate(images_data):
            task_data['items'].append({
                'index': i,
                'prompt': prompt,
                'status': 'pending'
            })
        
        # 更新任务状态为处理中，并保存items
        task_manager.update_task_status(session_id, task_id, TaskStatus.PROCESSING, items=task_data['items'])
        
        # 获取API key和模型名称
        api_key, request_api_type = get_api_key_from_request()
        # 如果header中有api_type，优先使用header中的
        if request_api_type:
            api_type = request_api_type
        
        # 获取模型名称
        model_name = request.form.get('model_name')
        
        # 获取 base_url 配置（可选，用于第三方 API）
        base_url = get_base_url_from_request(api_type)
        
        # 暂时使用同步处理，避免Celery复杂性
        try:
            # 直接调用处理函数
            from tasks import process_batch_task_sync
            result = process_batch_task_sync(session_id, task_id, images_data, prompt, api_type, api_key, model_name, base_url)
            
            if result['success']:
                task_manager.update_task_status(session_id, task_id, TaskStatus.COMPLETED)
            else:
                task_manager.update_task_status(session_id, task_id, TaskStatus.FAILED)
        except Exception as e:
            app.logger.error(f"Batch processing error: {str(e)}")
            task_manager.update_task_status(session_id, task_id, TaskStatus.FAILED)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': f'批量任务已创建，共{len(images_data)}张图片',
            'task_data': task_data
        })
        
    except Exception as e:
        app.logger.error(f"Create batch task error: {str(e)}")
        return jsonify({'success': False, 'error': f'创建任务失败: {str(e)}'}), 500

@app.route('/api/batch/generate-from-image', methods=['POST'])
def create_batch_generate_task():
    """创建批量生图任务（同一参考图重复生成N次，需要登录）"""
    import time
    request_time = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[{request_time}] ========== 收到批量生图请求 ==========")
    
    session_id = get_session_id_or_abort()
    if not session_id:
        return jsonify({'error': '缺少 Session-ID'}), 400
    
    # 获取API key（必须提供）
    try:
        api_key, api_type = get_api_key_from_request()
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    
    try:
        prompt = request.form.get('prompt', '')
        image_count = int(request.form.get('image_count', 1))
        api_type = request.form.get('api_type', 'gemini')
        
        print(f"  请求参数:")
        print(f"    session_id: {session_id}")
        print(f"    api_type: {api_type}")
        print(f"    prompt: {prompt[:50]}...")
        print(f"    image_count: {image_count}")
        
        if not prompt.strip():
            return jsonify({'error': 'Prompt is required'}), 400
        
        if image_count < 1 or image_count > 10:
            return jsonify({'error': 'Image count must be between 1 and 10'}), 400
        
        if api_type not in SUPPORTED_APIS:
            return jsonify({'error': f'Unsupported API type: {api_type}'}), 400
        
        # 获取模型名称
        model_name = request.form.get('model_name')
        if not model_name:
            model_name = 'gemini-2.5-flash-image'  # 默认模型
        
        # 参考图是可选的
        reference_image_data = None
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename and allowed_file(file.filename):
                # 保存参考图片
                filename = secure_filename(file.filename)
                file_id = str(uuid.uuid4())
                new_filename = f"{file_id}_{filename}"
                file_path = os.path.join(UPLOAD_FOLDER, new_filename)
                file.save(file_path)
                
                # 读取参考图数据
                with open(file_path, 'rb') as f:
                    reference_image_data = f.read()
        
        # 创建虚拟的images_data用于任务管理
        images_data = [{'filename': f'generated_{i+1}.png'} for i in range(image_count)]
        
        # 创建批量任务
        task_id, task_data = task_manager.create_task(session_id, images_data, prompt, api_type)
        
        # 添加items字段，让前端能够显示所有任务项
        task_data['items'] = []
        for i in range(image_count):
            task_data['items'].append({
                'index': i,
                'prompt': prompt,
                'status': 'pending'
            })
        
        # 更新任务状态为处理中，并保存items
        task_manager.update_task_status(session_id, task_id, TaskStatus.PROCESSING, items=task_data['items'])
        
        # 获取API key和模型名称
        api_key, request_api_type = get_api_key_from_request()
        # 如果header中有api_type，优先使用header中的
        if request_api_type:
            api_type = request_api_type
        
        # 获取模型名称
        model_name = request.form.get('model_name')
        print(f"    model_name: {model_name}")
        
        # 获取 base_url 配置（可选，用于第三方 API）
        base_url = get_base_url_from_request(api_type)
        print(f"    base_url: {base_url}")
        print(f"    api_key: {api_key[:30] + '...' if api_key else 'None'}")
        
        # 同步处理批量生图
        try:
            print(f"  开始处理任务...")
            from tasks import process_batch_generate_sync
            result = process_batch_generate_sync(session_id, task_id, reference_image_data, prompt, image_count, api_type, api_key, model_name, base_url)
            print(f"  处理结果: success={result.get('success')}")
            
            if result['success']:
                task_manager.update_task_status(session_id, task_id, TaskStatus.COMPLETED)
            else:
                task_manager.update_task_status(session_id, task_id, TaskStatus.FAILED)
        except Exception as e:
            app.logger.error(f"Batch generate processing error: {str(e)}")
            task_manager.update_task_status(session_id, task_id, TaskStatus.FAILED)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': f'批量生图任务已创建，将生成{image_count}张图片',
            'task_data': task_data
        })
        
    except Exception as e:
        app.logger.error(f"Create batch generate task error: {str(e)}")
        return jsonify({'success': False, 'error': f'创建任务失败: {str(e)}'}), 500

@app.route('/api/batch/generate-with-prompts', methods=['POST'])
def create_batch_generate_multi_prompt_task():
    """创建批量生图任务（支持多个不同的prompt，需要登录）"""
    session_id = get_session_id_or_abort()
    if not session_id:
        return jsonify({'error': '缺少 Session-ID'}), 400
    
    # 获取API key（必须提供）
    try:
        api_key, api_type = get_api_key_from_request()
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    
    try:
        import json
        
        # 获取prompts列表
        prompts_str = request.form.get('prompts', '')
        api_type = request.form.get('api_type', 'gemini')
        
        if not prompts_str:
            return jsonify({'error': 'Prompts are required'}), 400
        
        try:
            prompts = json.loads(prompts_str)
        except:
            return jsonify({'error': 'Invalid prompts format'}), 400
        
        if not isinstance(prompts, list) or len(prompts) == 0:
            return jsonify({'error': 'Prompts must be a non-empty list'}), 400
        
        if len(prompts) > 10:
            return jsonify({'error': 'Maximum 10 prompts allowed'}), 400
        
        if api_type not in SUPPORTED_APIS:
            return jsonify({'error': f'Unsupported API type: {api_type}'}), 400
        
        # 获取模型名称
        model_name = request.form.get('model_name')
        if not model_name:
            model_name = 'gemini-2.5-flash-image'  # 默认模型
        
        image_count = len(prompts)
        
        # 参考图是可选的
        reference_image_data = None
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename and allowed_file(file.filename):
                # 保存参考图片
                filename = secure_filename(file.filename)
                file_id = str(uuid.uuid4())
                new_filename = f"{file_id}_{filename}"
                file_path = os.path.join(UPLOAD_FOLDER, new_filename)
                file.save(file_path)
                
                # 读取参考图数据
                with open(file_path, 'rb') as f:
                    reference_image_data = f.read()
        
        # 创建虚拟的images_data用于任务管理
        images_data = [{'filename': f'generated_{i+1}.png'} for i in range(len(prompts))]
        
        # 创建批量任务（使用第一个prompt作为任务prompt）
        task_id, task_data = task_manager.create_task(session_id, images_data, prompts[0], api_type)
        
        # 立即添加每个item的prompt信息，让前端能够显示
        task_data['items'] = []
        for i, prompt in enumerate(prompts):
            task_data['items'].append({
                'index': i,
                'prompt': prompt,
                'status': 'pending'
            })
        
        # 保存items到Redis
        task_manager.update_task_status(session_id, task_id, TaskStatus.PROCESSING, items=task_data['items'])
        
        # 获取API key和模型名称
        api_key, request_api_type = get_api_key_from_request()
        # 如果header中有api_type，优先使用header中的
        if request_api_type:
            api_type = request_api_type
        
        # 获取模型名称
        model_name = request.form.get('model_name')
        
        # 获取 base_url 配置（可选，用于第三方 API）
        base_url = get_base_url_from_request(api_type)
        
        # 同步处理批量生图（使用多个prompt）
        try:
            from tasks import process_batch_generate_multi_prompt_sync
            result = process_batch_generate_multi_prompt_sync(session_id, task_id, reference_image_data, prompts, api_type, api_key, model_name, base_url)
            
            if result['success']:
                task_manager.update_task_status(session_id, task_id, TaskStatus.COMPLETED)
            else:
                task_manager.update_task_status(session_id, task_id, TaskStatus.FAILED)
        except Exception as e:
            app.logger.error(f"Batch generate multi-prompt processing error: {str(e)}")
            task_manager.update_task_status(session_id, task_id, TaskStatus.FAILED)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': f'批量生图任务已创建，将生成{len(prompts)}张图片',
            'task_data': task_data
        })
        
    except Exception as e:
        app.logger.error(f"Create batch generate multi-prompt task error: {str(e)}")
        return jsonify({'success': False, 'error': f'创建任务失败: {str(e)}'}), 500

@app.route('/api/batch/tasks', methods=['GET'])
def get_batch_tasks():
    """获取所有批量任务列表"""
    session_id = get_session_id_or_abort()
    if not session_id:
        return jsonify({'success': False, 'error': '缺少 Session-ID'}), 400
    try:
        tasks = task_manager.get_all_tasks(session_id)
        return jsonify({
            'success': True,
            'tasks': tasks
        })
    except redis.ConnectionError as e:
        app.logger.error(f"Redis connection error: {str(e)}")
        return jsonify({'success': False, 'error': 'Redis连接失败，请检查Redis服务是否运行'}), 500
    except Exception as e:
        app.logger.error(f"Get batch tasks error: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': f'获取任务列表失败: {str(e)}'}), 500

@app.route('/api/batch/tasks/<task_id>', methods=['GET'])
def get_batch_task(task_id):
    """获取特定任务详情"""
    session_id = get_session_id_or_abort()
    if not session_id:
        return jsonify({'success': False, 'error': '缺少 Session-ID'}), 400
    try:
        task_data = task_manager.get_task(session_id, task_id)
        if task_data:
            return jsonify({
                'success': True,
                'task': task_data
            })
        else:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
    except Exception as e:
        app.logger.error(f"Get batch task error: {str(e)}")
        return jsonify({'success': False, 'error': f'获取任务详情失败: {str(e)}'}), 500

@app.route('/api/batch/tasks/<task_id>/status', methods=['GET'])
def get_batch_task_status(task_id):
    """获取任务状态"""
    session_id = get_session_id_or_abort()
    if not session_id:
        return jsonify({'success': False, 'error': '缺少 Session-ID'}), 400
    try:
        task_data = task_manager.get_task(session_id, task_id)
        if task_data:
            return jsonify({
                'success': True,
                'status': task_data['status'],
                'progress': task_data['progress'],
                'processed_images': task_data['processed_images'],
                'total_images': task_data['total_images']
            })
        else:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
    except Exception as e:
        app.logger.error(f"Get batch task status error: {str(e)}")
        return jsonify({'success': False, 'error': f'获取任务状态失败: {str(e)}'}), 500

@app.route('/api/batch/generate-video', methods=['POST'])
def create_video_generate_task():
    """创建视频生成任务"""
    import time
    request_time = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[{request_time}] ========== 收到视频生成请求 ==========")

    session_id = get_session_id_or_abort()
    if not session_id:
        return jsonify({'error': '缺少 Session-ID'}), 400

    # 获取API key（必须提供）
    try:
        api_key, api_type = get_api_key_from_request()
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

    try:
        prompt = request.form.get('prompt', '')
        api_type = request.form.get('api_type', 'doubao')
        model_name = request.form.get('model_name', 'doubao-seedance-2-0-260128')
        duration = request.form.get('duration', type=int)
        video_mode = request.form.get('video_mode', 'text')
        resolution = request.form.get('resolution') or '720p'
        ratio = request.form.get('ratio') or 'adaptive'
        seed = request.form.get('seed', type=int)
        watermark = parse_bool_form_value(request.form.get('watermark'), default=False)
        generate_audio = parse_bool_form_value(request.form.get('generate_audio'), default=True)
        video_options = {
            'resolution': resolution,
            'ratio': ratio,
            'duration': duration,
            'seed': seed,
            'watermark': watermark,
            'generate_audio': generate_audio
        }

        print(f"  请求参数:")
        print(f"    session_id: {session_id}")
        print(f"    api_type: {api_type}")
        print(f"    model_name: {model_name}")
        print(f"    video_mode: {video_mode}")
        print(f"    duration: {duration}")
        print(f"    prompt: {prompt[:50]}...")

        if api_type not in SUPPORTED_APIS:
            return jsonify({'error': f'Unsupported API type: {api_type}'}), 400

        legacy_image_urls = encode_uploaded_files_as_data_urls('files', ALLOWED_EXTENSIONS, 'image', multiple=True)
        first_frame_urls = encode_uploaded_files_as_data_urls('first_frame_file', ALLOWED_EXTENSIONS, 'image', multiple=False)
        last_frame_urls = encode_uploaded_files_as_data_urls('last_frame_file', ALLOWED_EXTENSIONS, 'image', multiple=False)
        reference_image_urls = encode_uploaded_files_as_data_urls('reference_image_files', ALLOWED_EXTENSIONS, 'image', multiple=True)
        reference_video_urls = save_uploaded_media_files('reference_video_files', VIDEO_ALLOWED_EXTENSIONS, multiple=True)
        reference_audio_urls = encode_uploaded_files_as_data_urls('reference_audio_files', AUDIO_ALLOWED_EXTENSIONS, 'audio', multiple=True)

        if legacy_image_urls and not reference_image_urls and video_mode in {'text', 'multimodal'}:
            reference_image_urls = legacy_image_urls

        media_inputs = {
            'mode': video_mode,
            'images': reference_image_urls,
            'videos': reference_video_urls,
            'audios': reference_audio_urls,
            'first_frame': first_frame_urls[0] if first_frame_urls else None,
            'last_frame': last_frame_urls[0] if last_frame_urls else None,
        }

        if video_mode == 'first_frame' and not media_inputs['first_frame'] and reference_image_urls:
            media_inputs['first_frame'] = reference_image_urls[0]
        if video_mode == 'first_last_frame':
            if not media_inputs['first_frame'] and len(reference_image_urls) >= 1:
                media_inputs['first_frame'] = reference_image_urls[0]
            if not media_inputs['last_frame'] and len(reference_image_urls) >= 2:
                media_inputs['last_frame'] = reference_image_urls[1]

        if video_mode == 'first_frame' and not media_inputs['first_frame']:
            return jsonify({'success': False, 'error': '首帧生视频需要上传 1 张首帧图片'}), 400
        if video_mode == 'first_last_frame' and (not media_inputs['first_frame'] or not media_inputs['last_frame']):
            return jsonify({'success': False, 'error': '首尾帧生视频需要上传首帧和尾帧图片'}), 400
        if video_mode == 'multimodal' and not (
            media_inputs['images'] or media_inputs['videos'] or media_inputs['first_frame']
        ) and not prompt.strip():
            return jsonify({'success': False, 'error': '多模态参考至少需要提示词或参考素材'}), 400
        if media_inputs['audios'] and not (media_inputs['images'] or media_inputs['videos']):
            return jsonify({'success': False, 'error': '不能单独上传音频，至少需要参考图片或参考视频'}), 400
        if not prompt.strip() and not (
            media_inputs['first_frame'] or media_inputs['last_frame'] or media_inputs['images'] or media_inputs['videos']
        ):
            return jsonify({'success': False, 'error': '请输入视频描述或上传参考素材'}), 400

        # 创建任务数据（视频生成只生成1个）
        images_data = [{'filename': 'video_1.mp4', 'is_video': True}]

        # 创建批量任务
        task_id, task_data = task_manager.create_task(session_id, images_data, prompt, api_type)

        # 添加items字段
        task_data['items'] = [{
            'index': 0,
            'prompt': prompt,
            'status': 'pending',
            'is_video': True
        }]

        # 更新任务状态为处理中
        task_manager.update_task_status(session_id, task_id, TaskStatus.PROCESSING, items=task_data['items'])

        # 获取 base_url 配置
        base_url = get_base_url_from_request(api_type)
        print(f"    base_url: {base_url}")

        # 同步处理视频生成
        try:
            print(f"  开始处理视频生成任务...")
            from tasks import process_video_generate_sync
            result = process_video_generate_sync(
                session_id,
                task_id,
                media_inputs,
                prompt,
                api_type,
                api_key,
                model_name,
                base_url,
                duration,
                video_options
            )
            print(f"  处理结果: success={result.get('success')}")

            if result['success']:
                task_manager.update_task_status(session_id, task_id, TaskStatus.COMPLETED)
            else:
                task_manager.update_task_status(session_id, task_id, TaskStatus.FAILED)
        except Exception as e:
            app.logger.error(f"Video generation processing error: {str(e)}")
            task_manager.update_task_status(session_id, task_id, TaskStatus.FAILED)

        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '视频生成任务已创建',
            'task_data': task_data
        })

    except Exception as e:
        app.logger.error(f"Create video generate task error: {str(e)}")
        return jsonify({'success': False, 'error': f'创建任务失败: {str(e)}'}), 500

@app.route('/api/batch/tasks/<task_id>', methods=['DELETE'])
def cancel_batch_task(task_id):
    """取消任务"""
    session_id = get_session_id_or_abort()
    if not session_id:
        return jsonify({'success': False, 'error': '缺少 Session-ID'}), 400
    try:
        task_data = task_manager.cancel_task(session_id, task_id)
        if task_data:
            return jsonify({
                'success': True,
                'message': '任务已取消',
                'task': task_data
            })
        else:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
    except Exception as e:
        app.logger.error(f"Cancel batch task error: {str(e)}")
        return jsonify({'success': False, 'error': f'取消任务失败: {str(e)}'}), 500

@app.route('/api/batch/tasks/<task_id>/results', methods=['GET'])
def get_batch_task_results(task_id):
    """获取任务结果"""
    session_id = get_session_id_or_abort()
    if not session_id:
        return jsonify({'success': False, 'error': '缺少 Session-ID'}), 400
    try:
        task_data = task_manager.get_task(session_id, task_id)
        if task_data:
            return jsonify({
                'success': True,
                'results': task_data['results'],
                'images': task_data['images']
            })
        else:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
    except Exception as e:
        app.logger.error(f"Get batch task results error: {str(e)}")
        return jsonify({'success': False, 'error': f'获取任务结果失败: {str(e)}'}), 500

if __name__ == '__main__':
    # 检查是否为Docker环境
    is_docker = os.path.exists('/.dockerenv')
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    
    app.run(
        debug=debug_mode, 
        host='0.0.0.0', 
        port=int(os.getenv('PORT', 5001))
    )
