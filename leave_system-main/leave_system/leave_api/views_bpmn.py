"""
BPMN 流程管理视图

提供 BPMN 流程的增删改查、部署等功能
"""

import os
import json
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings


# BPMN 流程模型根目录
PROCESS_MODELS_DIR = Path(settings.BASE_DIR).parent / 'process_models'


def get_all_bpmn_files():
    """
    扫描并返回所有 BPMN 文件信息
    """
    bpmn_files = []
    
    if not PROCESS_MODELS_DIR.exists():
        return bpmn_files
    
    # 递归扫描所有 .bpmn 文件
    for bpmn_file in PROCESS_MODELS_DIR.rglob('*.bpmn'):
        # 读取同目录下的 process_model.json 获取元数据
        process_json = bpmn_file.parent / 'process_model.json'
        metadata = {}
        
        if process_json.exists():
            try:
                with open(process_json, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except Exception as e:
                print(f"读取 {process_json} 失败: {e}")
        
        # 生成流程 ID（使用相对路径）
        relative_path = bpmn_file.relative_to(PROCESS_MODELS_DIR)
        process_id = str(relative_path).replace('\\', '/').replace('.bpmn', '')
        
        bpmn_files.append({
            'id': process_id,
            'name': metadata.get('display_name', bpmn_file.stem),
            'description': metadata.get('description', ''),
            'path': str(bpmn_file),
            'relative_path': str(relative_path),
            'metadata': metadata
        })
    
    return bpmn_files


@csrf_exempt
def processes_list_create(request):
    """
    处理流程列表和创建
    
    GET /api/bpmn/processes/ - 获取所有流程列表
    POST /api/bpmn/processes/ - 创建新流程
    """
    if request.method == 'GET':
        return list_processes(request)
    elif request.method == 'POST':
        return create_process(request)
    else:
        return JsonResponse({'error': '不支持的请求方法'}, status=405)


def list_processes(request):
    """获取所有 BPMN 流程列表"""
    try:
        processes = get_all_bpmn_files()
        return JsonResponse({
            'processes': processes,
            'count': len(processes)
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


def create_process(request):
    """创建新的 BPMN 流程"""
    try:
        data = json.loads(request.body)
        name = data.get('name')
        description = data.get('description', '')
        group = data.get('group', 'custom')
        xml = data.get('xml')
        
        if not name or not xml:
            return JsonResponse({
                'error': '缺少必要参数: name 和 xml'
            }, status=400)
        
        # 生成流程目录名（使用名称的拼音或英文）
        process_name = name.lower().replace(' ', '_')
        process_dir = PROCESS_MODELS_DIR / group / process_name
        process_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存 BPMN 文件
        bpmn_path = process_dir / f"{process_name}.bpmn"
        with open(bpmn_path, 'w', encoding='utf-8') as f:
            f.write(xml)
        
        # 保存元数据
        metadata = {
            'display_name': name,
            'description': description,
            'id': process_name
        }
        
        metadata_path = process_dir / 'process_model.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # 生成流程 ID
        relative_path = bpmn_path.relative_to(PROCESS_MODELS_DIR)
        process_id = str(relative_path).replace('\\', '/').replace('.bpmn', '')
        
        return JsonResponse({
            'id': process_id,
            'name': name,
            'path': str(bpmn_path),
            'message': '流程创建成功'
        }, status=201)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
def process_detail(request, process_id):
    """
    处理单个流程的详情、更新和删除
    
    GET /api/bpmn/processes/<process_id>/ - 获取流程详情
    PUT /api/bpmn/processes/<process_id>/ - 更新流程
    DELETE /api/bpmn/processes/<process_id>/ - 删除流程
    """
    if request.method == 'GET':
        return get_process(request, process_id)
    elif request.method == 'PUT':
        return update_process(request, process_id)
    elif request.method == 'DELETE':
        return delete_process(request, process_id)
    else:
        return JsonResponse({'error': '不支持的请求方法'}, status=405)
def get_process(request, process_id):
    """获取指定 BPMN 流程的 XML 内容"""
    try:
        # 构建 BPMN 文件路径
        bpmn_path = PROCESS_MODELS_DIR / f"{process_id}.bpmn"
        
        if not bpmn_path.exists():
            return JsonResponse({
                'error': '流程文件不存在'
            }, status=404)
        
        # 读取 BPMN XML
        with open(bpmn_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # 读取元数据
        process_json = bpmn_path.parent / 'process_model.json'
        metadata = {}
        if process_json.exists():
            with open(process_json, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        
        return JsonResponse({
            'id': process_id,
            'name': metadata.get('display_name', bpmn_path.stem),
            'description': metadata.get('description', ''),
            'xml': xml_content,
            'metadata': metadata
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


def update_process(request, process_id):
    """更新 BPMN 流程"""
    try:
        data = json.loads(request.body)
        xml = data.get('xml')
        
        if not xml:
            return JsonResponse({
                'error': '缺少必要参数: xml'
            }, status=400)
        
        # 构建 BPMN 文件路径
        bpmn_path = PROCESS_MODELS_DIR / f"{process_id}.bpmn"
        
        if not bpmn_path.exists():
            return JsonResponse({
                'error': '流程文件不存在'
            }, status=404)
        
        # 更新 BPMN 文件
        with open(bpmn_path, 'w', encoding='utf-8') as f:
            f.write(xml)
        
        # 更新元数据（如果提供）
        if 'name' in data or 'description' in data:
            metadata_path = bpmn_path.parent / 'process_model.json'
            metadata = {}
            
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            if 'name' in data:
                metadata['display_name'] = data['name']
            if 'description' in data:
                metadata['description'] = data['description']
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return JsonResponse({
            'message': '流程更新成功'
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


def delete_process(request, process_id):
    """删除 BPMN 流程"""
    try:
        # 构建 BPMN 文件路径
        bpmn_path = PROCESS_MODELS_DIR / f"{process_id}.bpmn"
        
        if not bpmn_path.exists():
            return JsonResponse({
                'error': '流程文件不存在'
            }, status=404)
        
        # 删除 BPMN 文件
        bpmn_path.unlink()
        
        # 删除元数据文件
        metadata_path = bpmn_path.parent / 'process_model.json'
        if metadata_path.exists():
            metadata_path.unlink()
        
        # 如果目录为空，删除目录
        if not any(bpmn_path.parent.iterdir()):
            bpmn_path.parent.rmdir()
        
        return JsonResponse({
            'message': '流程删除成功'
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def deploy_process(request, process_id):
    """
    部署 BPMN 流程到工作流引擎
    
    POST /api/bpmn/processes/<process_id>/deploy/
    
    返回:
    {
        "message": "流程部署成功",
        "deployment_id": "xxx"
    }
    """
    try:
        # 构建 BPMN 文件路径
        bpmn_path = PROCESS_MODELS_DIR / f"{process_id}.bpmn"
        
        if not bpmn_path.exists():
            return JsonResponse({
                'error': '流程文件不存在'
            }, status=404)
        
        # TODO: 这里应该调用 SpiffWorkflow 或其他工作流引擎的部署 API
        # 目前只是返回成功消息
        
        return JsonResponse({
            'message': '流程部署成功',
            'deployment_id': process_id,
            'note': '当前为模拟部署，实际部署需要集成工作流引擎'
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def validate_process(request, process_id):
    """
    验证 BPMN 流程的正确性
    
    GET /api/bpmn/processes/<process_id>/validate/
    
    返回:
    {
        "valid": true,
        "errors": [],
        "warnings": []
    }
    """
    try:
        # 构建 BPMN 文件路径
        bpmn_path = PROCESS_MODELS_DIR / f"{process_id}.bpmn"
        
        if not bpmn_path.exists():
            return JsonResponse({
                'error': '流程文件不存在'
            }, status=404)
        
        # TODO: 这里应该使用 BPMN 验证库进行验证
        # 目前只是简单检查文件是否为有效的 XML
        
        with open(bpmn_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # 简单的 XML 格式检查
        import xml.etree.ElementTree as ET
        try:
            ET.fromstring(xml_content)
            return JsonResponse({
                'valid': True,
                'errors': [],
                'warnings': [],
                'message': 'BPMN 流程格式正确'
            })
        except ET.ParseError as e:
            return JsonResponse({
                'valid': False,
                'errors': [str(e)],
                'warnings': []
            })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)
