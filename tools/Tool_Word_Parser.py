import os
import base64
from pathlib import Path
from openai import OpenAI
from typing import Dict, List
import io
import tempfile
from urllib.parse import urlparse
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# 安装依赖: pip install python-docx Pillow
try:
    from docx import Document
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import _Cell, Table
    from docx.text.paragraph import Paragraph
    from PIL import Image
except ImportError:
    print("请先安装依赖: pip install python-docx Pillow")


# 工具参数定义
class ParseWordParams(BaseModel):
    """解析Word文件的参数"""
    word_path: str = Field(description="Word文件的完整路径或上传文件的URL（如 http://localhost:5000/files/xxx.docx）")
    analyze_images: bool = Field(default=True, description="是否使用大模型分析图像内容，默认True")
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


def _analyze_image_with_llm(img_base64: str, context: str = "") -> str:
    """使用大模型分析图像内容"""
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    
    prompt = f"""请详细分析这张图像的内容。

{context}

请提取并描述：
1. 图像类型（图表、照片、截图、图形等）
2. 图像中的所有文字内容
3. 图像中的关键视觉元素和数据信息
4. 图像传达的主要信息

请用简洁清晰的语言描述，重点关注信息提取。"""

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


def _extract_images_from_paragraph(paragraph) -> List[bytes]:
    """从段落中提取所有图像"""
    images = []
    
    # 查找段落中的所有图像
    for run in paragraph.runs:
        # 获取run的XML元素
        for drawing in run._element.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing'):
            # 查找blip元素（包含图像引用）
            for blip in drawing.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}blip'):
                # 获取图像关系ID
                embed = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                if embed:
                    try:
                        # 获取图像数据
                        image_part = paragraph.part.related_parts[embed]
                        image_bytes = image_part.blob
                        images.append(image_bytes)
                    except Exception as e:
                        print(f"提取图像失败: {str(e)}")
    
    return images


def _extract_table_text(table: Table) -> str:
    """提取表格内容为文本"""
    table_text = "\n【表格】\n"
    for i, row in enumerate(table.rows):
        row_text = []
        for cell in row.cells:
            cell_text = cell.text.strip()
            row_text.append(cell_text)
        table_text += " | ".join(row_text) + "\n"
    return table_text


def _parse_word_complete(word_path: str, analyze_images: bool = True) -> Dict:
    """
    完整解析Word文件，提取文本和图像内容
    
    Args:
        word_path: Word文件路径或URL（如 http://localhost:5000/files/xxx.docx）
        analyze_images: 是否使用大模型分析图像，默认True
    
    Returns:
        包含完整Word内容的字典
    """
    # 处理 URL 格式的路径
    if word_path.startswith('http://') or word_path.startswith('https://'):
        # 从 URL 中提取文件名
        parsed_url = urlparse(word_path)
        filename = os.path.basename(parsed_url.path)
        # 构建临时文件夹的完整路径
        local_word_path = os.path.join(tempfile.gettempdir(), filename)
        print(f"检测到URL格式，转换为本地路径: {local_word_path}")
    else:
        local_word_path = word_path
    
    if not Path(local_word_path).exists():
        raise FileNotFoundError(f"Word文件不存在: {local_word_path}")
    
    print(f"开始解析Word文档: {local_word_path}")
    document = Document(local_word_path)
    
    result = {
        'total_paragraphs': 0,
        'total_tables': 0,
        'total_images': 0,
        'content_blocks': [],
        'full_content': ''
    }
    
    full_content_parts = []
    image_counter = 0
    paragraph_counter = 0
    table_counter = 0
    
    # 遍历文档的所有元素（段落和表格）
    for element in document.element.body:
        # 处理段落
        if isinstance(element, CT_P):
            paragraph = Paragraph(element, document)
            paragraph_counter += 1
            
            text = paragraph.text.strip()
            
            # 提取段落中的图像
            images = _extract_images_from_paragraph(paragraph)
            
            if text or images:
                block_content = ""
                
                # 添加文本内容
                if text:
                    # 判断是否为标题
                    if paragraph.style.name.startswith('Heading'):
                        level = paragraph.style.name.replace('Heading ', '')
                        block_content += f"\n{'#' * (int(level) if level.isdigit() else 1)} {text}\n"
                    else:
                        block_content += f"{text}\n"
                
                # 处理图像
                for img_bytes in images:
                    image_counter += 1
                    try:
                        img = Image.open(io.BytesIO(img_bytes))
                        img_size = (img.width, img.height)
                        print(f"  发现图像 {image_counter}: {img_size[0]}x{img_size[1]}")
                        
                        image_data = {
                            'type': 'image',
                            'image_index': image_counter,
                            'size': img_size,
                            'analysis': ''
                        }
                        
                        # 使用大模型分析图像
                        if analyze_images:
                            print(f"    正在分析图像 {image_counter}...")
                            img_base64 = _image_to_base64(img_bytes)
                            context = f"这是Word文档中的第{image_counter}张图像。"
                            if text:
                                context += f"\n\n图像所在段落的文本：\n{text}"
                            
                            analysis = _analyze_image_with_llm(img_base64, context)
                            image_data['analysis'] = analysis
                            
                            block_content += f"\n【图像 {image_counter}】({img_size[0]}x{img_size[1]})\n{analysis}\n"
                        else:
                            image_data['analysis'] = f"[图像 {image_counter}: {img_size[0]}x{img_size[1]}]"
                            block_content += f"\n【图像 {image_counter}】{img_size[0]}x{img_size[1]}\n"
                        
                        result['content_blocks'].append(image_data)
                        
                    except Exception as e:
                        print(f"    图像 {image_counter} 处理失败: {str(e)}")
                        block_content += f"\n【图像 {image_counter}】提取失败: {str(e)}\n"
                
                if block_content:
                    full_content_parts.append(block_content)
                    result['content_blocks'].append({
                        'type': 'paragraph',
                        'index': paragraph_counter,
                        'text': text
                    })
        
        # 处理表格
        elif isinstance(element, CT_Tbl):
            table = Table(element, document)
            table_counter += 1
            print(f"  发现表格 {table_counter}: {len(table.rows)}行 x {len(table.columns)}列")
            
            table_text = _extract_table_text(table)
            full_content_parts.append(table_text)
            
            result['content_blocks'].append({
                'type': 'table',
                'index': table_counter,
                'rows': len(table.rows),
                'columns': len(table.columns),
                'text': table_text
            })
    
    result['total_paragraphs'] = paragraph_counter
    result['total_tables'] = table_counter
    result['total_images'] = image_counter
    result['full_content'] = '\n'.join(full_content_parts)
    
    print(f"\n{'='*80}")
    print("Word文档解析完成！")
    print(f"总段落数: {paragraph_counter}")
    print(f"总表格数: {table_counter}")
    print(f"总图像数: {image_counter}")
    print(f"{'='*80}")
    
    return result


def _save_result_to_file(result: Dict, output_path: str):
    """将解析结果保存到文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result['full_content'])
    print(f"\n结果已保存到: {output_path}")


# 定义langchain工具

@tool(args_schema=ParseWordParams)
def parse_word_document(
    word_path: str,
    analyze_images: bool = True,
    save_to_file: bool = False,
    output_path: str = ""
) -> str:
    """
    完整解析Word文档（.docx格式），提取文本、表格和图像内容，可选使用视觉大模型分析图像。
    
    适用场景:
    - 提取Word文档的所有文本内容
    - 识别和分析Word中的图表、图片
    - 提取Word文档中的表格数据
    - 使用视觉大模型理解图像内容
    - 将Word转换为结构化文本
    - 分析报告、合同、方案等文档
    - 保留文档的层次结构（标题、段落、表格）
    
    功能特点:
    - 逐段落提取文本内容
    - 识别并提取所有图像
    - 提取表格数据并格式化
    - 识别标题层级结构
    - 可选使用qwen-vl-max模型分析图像内容
    - 自动优化图像大小和质量
    - 输出结构化的完整内容
    - 可选保存结果到文件
    - 支持本地路径和上传文件URL（自动从临时文件夹获取）
    
    参数说明:
    - word_path: Word文件的完整路径或上传文件的URL（如 http://localhost:5000/files/xxx.docx）
    - analyze_images: 是否使用大模型分析图像（需要DASHSCOPE_API_KEY环境变量）
    - save_to_file: 是否将结果保存到文件
    - output_path: 输出文件路径（当save_to_file为True时必填）
    
    注意事项:
    - 仅支持.docx格式（不支持旧版.doc格式）
    - 需要安装python-docx库
    - 图像分析需要配置DASHSCOPE_API_KEY环境变量
    
    返回:
    - 包含Word文档完整内容的文本，包括所有段落、表格和图像分析结果
    """
    try:
        # 解析Word
        result = _parse_word_complete(word_path, analyze_images)
        
        # 可选保存到文件
        if save_to_file:
            if not output_path:
                output_path = word_path.replace('.docx', '_parsed.txt')
            _save_result_to_file(result, output_path)
        
        # 构建摘要信息
        summary = f"""Word文档解析完成！

📄 文件: {word_path}
📊 统计信息:
  - 总段落数: {result['total_paragraphs']}
  - 总表格数: {result['total_tables']}
  - 总图像数: {result['total_images']}
  - 总文本长度: {len(result['full_content'])} 字符
  - 图像分析: {'已启用' if analyze_images else '未启用'}

{'='*80}
完整内容:
{'='*80}

{result['full_content']}
"""
        
        return summary
        
    except FileNotFoundError as e:
        return f"❌ 错误: {str(e)}"
    except Exception as e:
        return f"❌ Word文档解析失败: {str(e)}\n请确保文件是.docx格式（不支持旧版.doc格式）"


# 导出工具列表
word_parser_tools = [
    parse_word_document
]
