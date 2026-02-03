import os
import base64
from pathlib import Path
from openai import OpenAI
from typing import Dict
import io
import tempfile
from urllib.parse import urlparse
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# 安装依赖: pip install Pillow
try:
    from PIL import Image
    from PIL.ExifTags import TAGS
except ImportError:
    print("请先安装依赖: pip install Pillow")


# 工具参数定义
class ParseImageParams(BaseModel):
    """解析图像文件的参数"""
    image_path: str = Field(description="图像文件的完整路径或上传文件的URL（如 http://localhost:5000/files/xxx.jpg）")
    analyze_content: bool = Field(default=True, description="是否使用大模型分析图像内容，默认True")
    extract_metadata: bool = Field(default=True, description="是否提取图像元数据（EXIF等），默认True")
    save_to_file: bool = Field(default=False, description="是否将结果保存到文件，默认False")
    output_path: str = Field(default="", description="输出文件路径，如果save_to_file为True则必填")


# 辅助函数
def _image_to_base64(image_bytes: bytes, max_size: int = 1920, quality: int = 85) -> str:
    """将图像字节转换为base64编码，并进行压缩优化"""
    img = Image.open(io.BytesIO(image_bytes))
    
    # 转换RGBA到RGB
    if img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    # 压缩图像尺寸
    if img.width > max_size or img.height > max_size:
        ratio = min(max_size / img.width, max_size / img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # 转换为base64
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=quality, optimize=True)
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    return img_base64


def _analyze_image_with_llm(img_base64: str, filename: str = "") -> str:
    """使用大模型分析图像内容"""
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    
    prompt = f"""请详细分析这张图像的内容。

文件名: {filename}

请提取并描述：
1. 图像类型（照片、截图、图表、设计图、图标等）
2. 图像的主要内容和主题
3. 图像中的所有可见文字内容（包括标题、标签、说明等）
4. 图像中的关键视觉元素（人物、物体、场景、颜色、构图等）
5. 图像中的数据信息（如有图表、表格等）
6. 图像的用途和应用场景

请用简洁清晰的语言描述，重点关注信息提取和内容理解。"""

    content = [
        {"type": "text", "text": prompt},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}
        }
    ]
    
    try:
        completion = client.chat.completions.create(
            model="qwen-vl-max",
            messages=[{"role": "user", "content": content}],
            stream=False,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"[图像分析失败: {str(e)}]"


def _extract_image_metadata(img: Image.Image) -> Dict:
    """提取图像元数据"""
    metadata = {
        'basic_info': {
            'format': img.format,
            'mode': img.mode,
            'size': img.size,
            'width': img.width,
            'height': img.height,
        },
        'exif': {}
    }
    
    # 提取EXIF数据
    try:
        exif_data = img._getexif()
        if exif_data:
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                # 只保留常见的可读元数据
                if isinstance(tag, str) and isinstance(value, (str, int, float)):
                    metadata['exif'][tag] = value
    except:
        pass
    
    # 计算文件信息
    metadata['color_info'] = {
        'mode': img.mode,
        'palette': img.palette.mode if img.palette else None,
    }
    
    return metadata


def _parse_image_complete(image_path: str, analyze_content: bool = True, extract_metadata: bool = True) -> Dict:
    """
    完整解析图像文件，提取基本信息、元数据和内容分析
    
    Args:
        image_path: 图像文件路径或URL（如 http://localhost:5000/files/xxx.jpg）
        analyze_content: 是否使用大模型分析图像内容，默认True
        extract_metadata: 是否提取元数据，默认True
    
    Returns:
        包含完整图像信息的字典
    """
    # 处理 URL 格式的路径
    if image_path.startswith('http://') or image_path.startswith('https://'):
        # 从 URL 中提取文件名
        parsed_url = urlparse(image_path)
        filename = os.path.basename(parsed_url.path)
        # 构建临时文件夹的完整路径
        local_image_path = os.path.join(tempfile.gettempdir(), filename)
        print(f"检测到URL格式，转换为本地路径: {local_image_path}")
    else:
        local_image_path = image_path
    
    if not Path(local_image_path).exists():
        raise FileNotFoundError(f"图像文件不存在: {local_image_path}")
    
    print(f"开始解析图像: {local_image_path}")
    
    # 打开图像
    with Image.open(local_image_path) as img:
        result = {
            'file_path': image_path,
            'file_name': Path(local_image_path).name,
            'file_size': Path(local_image_path).stat().st_size,
        }
        
        # 基本信息
        print(f"  格式: {img.format}")
        print(f"  尺寸: {img.size[0]}x{img.size[1]}")
        print(f"  颜色模式: {img.mode}")
        
        result['basic_info'] = {
            'format': img.format,
            'size': img.size,
            'width': img.width,
            'height': img.height,
            'mode': img.mode,
        }
        
        # 提取元数据
        if extract_metadata:
            print("  提取元数据...")
            result['metadata'] = _extract_image_metadata(img)
        
        # 读取图像字节用于分析
        with open(local_image_path, 'rb') as f:
            image_bytes = f.read()
        
        # 内容分析
        if analyze_content:
            print("  使用大模型分析图像内容...")
            img_base64 = _image_to_base64(image_bytes)
            analysis = _analyze_image_with_llm(img_base64, Path(local_image_path).name)
            result['content_analysis'] = analysis
        else:
            result['content_analysis'] = "[未启用内容分析]"
    
    print(f"\n{'='*80}")
    print("图像解析完成！")
    print(f"{'='*80}")
    
    return result


def _format_result(result: Dict) -> str:
    """格式化解析结果为可读文本"""
    lines = []
    
    lines.append(f"文件名: {result['file_name']}")
    lines.append(f"文件路径: {result['file_path']}")
    lines.append(f"文件大小: {result['file_size']:,} 字节 ({result['file_size'] / 1024:.2f} KB)")
    lines.append("")
    
    lines.append("【基本信息】")
    basic = result['basic_info']
    lines.append(f"  格式: {basic['format']}")
    lines.append(f"  尺寸: {basic['width']} x {basic['height']} 像素")
    lines.append(f"  颜色模式: {basic['mode']}")
    lines.append("")
    
    if 'metadata' in result and result['metadata'].get('exif'):
        lines.append("【元数据 (EXIF)】")
        for key, value in result['metadata']['exif'].items():
            lines.append(f"  {key}: {value}")
        lines.append("")
    
    if result.get('content_analysis'):
        lines.append("【内容分析】")
        lines.append(result['content_analysis'])
        lines.append("")
    
    return '\n'.join(lines)


def _save_result_to_file(result: Dict, output_path: str):
    """将解析结果保存到文件"""
    content = _format_result(result)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n结果已保存到: {output_path}")


# 定义langchain工具

@tool(args_schema=ParseImageParams)
def parse_image_file(
    image_path: str,
    analyze_content: bool = True,
    extract_metadata: bool = True,
    save_to_file: bool = False,
    output_path: str = ""
) -> str:
    """
    完整解析图像文件，提取基本信息、元数据并使用视觉大模型分析图像内容。
    
    适用场景:
    - 分析图片内容和主题
    - 识别图像中的文字、物体、场景
    - 提取图像元数据（EXIF信息）
    - 获取图像基本属性（尺寸、格式、颜色模式等）
    - 理解图表、截图、设计图等专业图像
    - 分析照片拍摄信息（相机型号、拍摄参数等）
    - 提取图像中的数据和信息
    
    功能特点:
    - 支持常见图像格式（JPG、PNG、BMP、GIF、WEBP等）
    - 提取图像基本信息（格式、尺寸、颜色模式）
    - 提取EXIF元数据（拍摄参数、GPS信息等）
    - 使用qwen-vl-max模型深度分析图像内容
    - 识别图像中的文字、物体、场景
    - 理解图表、表格等数据可视化内容
    - 自动优化图像大小和质量
    - 可选保存结果到文件
    - 支持本地路径和上传文件URL（自动从临时文件夹获取）
    
    参数说明:
    - image_path: 图像文件的完整路径或上传文件的URL（如 http://localhost:5000/files/xxx.jpg）
    - analyze_content: 是否使用大模型分析图像内容（需要DASHSCOPE_API_KEY环境变量）
    - extract_metadata: 是否提取图像元数据（EXIF等）
    - save_to_file: 是否将结果保存到文件
    - output_path: 输出文件路径（当save_to_file为True时必填）
    
    注意事项:
    - 需要安装Pillow库
    - 图像内容分析需要配置DASHSCOPE_API_KEY环境变量
    - 大尺寸图像会自动压缩以优化分析速度
    
    返回:
    - 包含图像完整信息的文本，包括基本属性、元数据和内容分析结果
    """
    try:
        # 解析图像
        result = _parse_image_complete(image_path, analyze_content, extract_metadata)
        
        # 格式化结果
        formatted_result = _format_result(result)
        
        # 可选保存到文件
        if save_to_file:
            if not output_path:
                output_path = str(Path(image_path).with_suffix('.txt'))
            _save_result_to_file(result, output_path)
        
        # 构建摘要信息
        summary = f"""图像解析完成！

📊 统计信息:
  - 文件名: {result['file_name']}
  - 文件大小: {result['file_size']:,} 字节 ({result['file_size'] / 1024:.2f} KB)
  - 图像格式: {result['basic_info']['format']}
  - 图像尺寸: {result['basic_info']['width']} x {result['basic_info']['height']} 像素
  - 颜色模式: {result['basic_info']['mode']}
  - 元数据提取: {'已启用' if extract_metadata else '未启用'}
  - 内容分析: {'已启用' if analyze_content else '未启用'}

{'='*80}
完整内容:
{'='*80}

{formatted_result}
"""
        
        return summary
        
    except FileNotFoundError as e:
        return f"❌ 错误: {str(e)}"
    except Exception as e:
        return f"❌ 图像解析失败: {str(e)}"


# 导出工具列表
image_parser_tools = [
    parse_image_file
]
