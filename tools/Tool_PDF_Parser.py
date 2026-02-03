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

# 安装依赖: pip install PyMuPDF Pillow
try:
    import fitz  # PyMuPDF
    from PIL import Image
except ImportError:
    print("请先安装依赖: pip install PyMuPDF Pillow")


# 工具参数定义
class ParsePDFParams(BaseModel):
    """解析PDF文件的参数"""
    pdf_path: str = Field(description="PDF文件的完整路径或上传文件的URL（如 http://localhost:5000/files/xxx.pdf）")
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


def _parse_pdf_complete(pdf_path: str, analyze_images: bool = True) -> Dict:
    """
    完整解析PDF文件，提取文本和图像内容
    
    Args:
        pdf_path: PDF文件路径或URL（如 http://localhost:5000/files/xxx.pdf）
        analyze_images: 是否使用大模型分析图像，默认True
    
    Returns:
        包含完整PDF内容的字典
    """
    # 处理 URL 格式的路径
    if pdf_path.startswith('http://') or pdf_path.startswith('https://'):
        # 从 URL 中提取文件名
        parsed_url = urlparse(pdf_path)
        filename = os.path.basename(parsed_url.path)
        # 构建临时文件夹的完整路径
        local_pdf_path = os.path.join(tempfile.gettempdir(), filename)
        print(f"检测到URL格式，转换为本地路径: {local_pdf_path}")
    else:
        local_pdf_path = pdf_path
    
    if not Path(local_pdf_path).exists():
        raise FileNotFoundError(f"PDF文件不存在: {local_pdf_path}")
    
    print(f"开始解析PDF: {local_pdf_path}")
    pdf_document = fitz.open(local_pdf_path)
    total_pages = len(pdf_document)
    print(f"总页数: {total_pages}")
    
    result = {
        'total_pages': total_pages,
        'pages': [],
        'full_content': ''
    }
    
    full_content_parts = []
    
    for page_num in range(total_pages):
        print(f"\n处理第 {page_num + 1}/{total_pages} 页...")
        page = pdf_document[page_num]
        
        # 提取文本内容
        text = page.get_text()
        print(f"  提取文本: {len(text)} 字符")
        
        # 提取图像
        image_list = page.get_images(full=True)
        print(f"  发现图像: {len(image_list)} 个")
        
        page_data = {
            'page_num': page_num + 1,
            'text': text,
            'images': []
        }
        
        # 处理页面文本
        page_content = f"\n{'='*80}\n第 {page_num + 1} 页\n{'='*80}\n"
        
        if text.strip():
            page_content += f"\n【文本内容】\n{text}\n"
        
        # 处理图像
        for img_index, img_info in enumerate(image_list):
            xref = img_info[0]
            try:
                # 提取图像数据
                base_image = pdf_document.extract_image(xref)
                image_bytes = base_image["image"]
                
                # 获取图像尺寸
                img = Image.open(io.BytesIO(image_bytes))
                img_size = (img.width, img.height)
                print(f"    图像 {img_index + 1}: {img_size[0]}x{img_size[1]}")
                
                image_data = {
                    'image_index': img_index + 1,
                    'size': img_size,
                    'analysis': ''
                }
                
                # 使用大模型分析图像
                if analyze_images:
                    print(f"    正在分析图像 {img_index + 1}...")
                    img_base64 = _image_to_base64(image_bytes)
                    context = f"这是PDF第{page_num + 1}页中的第{img_index + 1}张图像。"
                    if text.strip():
                        context += f"\n\n页面文本上下文：\n{text[:500]}..."
                    
                    analysis = _analyze_image_with_llm(img_base64, context)
                    image_data['analysis'] = analysis
                    
                    page_content += f"\n【图像 {img_index + 1}】({img_size[0]}x{img_size[1]})\n{analysis}\n"
                else:
                    image_data['analysis'] = f"[图像 {img_index + 1}: {img_size[0]}x{img_size[1]}]"
                    page_content += f"\n【图像 {img_index + 1}】{img_size[0]}x{img_size[1]}\n"
                
                page_data['images'].append(image_data)
                
            except Exception as e:
                print(f"    图像 {img_index + 1} 处理失败: {str(e)}")
                page_data['images'].append({
                    'image_index': img_index + 1,
                    'size': (0, 0),
                    'analysis': f"[图像提取失败: {str(e)}]"
                })
        
        result['pages'].append(page_data)
        full_content_parts.append(page_content)
    
    pdf_document.close()
    
    # 整合完整内容
    result['full_content'] = '\n'.join(full_content_parts)
    
    print(f"\n{'='*80}")
    print("PDF解析完成！")
    print(f"{'='*80}")
    
    return result


def _save_result_to_file(result: Dict, output_path: str):
    """将解析结果保存到文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result['full_content'])
    print(f"\n结果已保存到: {output_path}")


# 定义langchain工具

@tool(args_schema=ParsePDFParams)
def parse_pdf_document(
    pdf_path: str,
    analyze_images: bool = True,
    save_to_file: bool = False,
    output_path: str = ""
) -> str:
    """
    完整解析PDF文档，提取文本和图像内容，可选使用视觉大模型分析图像。
    
    适用场景:
    - 提取PDF文档的所有文本内容
    - 识别和分析PDF中的图表、图片
    - 使用视觉大模型理解图像内容
    - 将PDF转换为结构化文本
    - 分析学术论文、报告、合同等文档
    - 提取PDF中的表格和数据
    
    功能特点:
    - 逐页提取文本内容
    - 识别并提取所有图像
    - 可选使用qwen-vl-max模型分析图像内容
    - 自动优化图像大小和质量
    - 输出结构化的完整内容
    - 可选保存结果到文件
    - 支持本地路径和上传文件URL（自动从临时文件夹获取）
    
    参数说明:
    - pdf_path: PDF文件的完整路径或上传文件的URL（如 http://localhost:5000/files/xxx.pdf）
    - analyze_images: 是否使用大模型分析图像（需要DASHSCOPE_API_KEY环境变量）
    - save_to_file: 是否将结果保存到文件
    - output_path: 输出文件路径（当save_to_file为True时必填）
    
    返回:
    - 包含PDF完整内容的文本，包括所有页面的文本和图像分析结果
    """
    try:
        # 解析PDF
        result = _parse_pdf_complete(pdf_path, analyze_images)
        
        # 可选保存到文件
        if save_to_file:
            if not output_path:
                output_path = pdf_path.replace('.pdf', '_parsed.txt')
            _save_result_to_file(result, output_path)
        
        # 构建摘要信息
        summary = f"""PDF解析完成！

📄 文件: {pdf_path}
📊 统计信息:
  - 总页数: {result['total_pages']}
  - 总文本长度: {sum(len(p['text']) for p in result['pages'])} 字符
  - 总图像数: {sum(len(p['images']) for p in result['pages'])} 个
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
        return f"❌ PDF解析失败: {str(e)}"


# 导出工具列表
pdf_parser_tools = [
    parse_pdf_document
]
