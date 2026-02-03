import os
import base64
from pathlib import Path
from openai import OpenAI
from typing import List, Dict
import io

# 安装依赖: pip install PyMuPDF Pillow
try:
    import fitz  # PyMuPDF
    from PIL import Image
except ImportError:
    print("请先安装依赖: pip install PyMuPDF Pillow")
    exit(1)

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


def image_to_base64(image_bytes: bytes, max_size: int = 1920, quality: int = 85) -> str:
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


def analyze_image_with_llm(img_base64: str, context: str = "") -> str:
    """使用大模型分析图像内容"""
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


def parse_pdf_complete(pdf_path: str, analyze_images: bool = True) -> Dict:
    """
    完整解析PDF文件，提取文本和图像内容
    
    Args:
        pdf_path: PDF文件路径
        analyze_images: 是否使用大模型分析图像，默认True
    
    Returns:
        包含完整PDF内容的字典：
        {
            'total_pages': int,
            'pages': [
                {
                    'page_num': int,
                    'text': str,
                    'images': [
                        {
                            'image_index': int,
                            'size': (width, height),
                            'analysis': str  # 大模型分析结果
                        }
                    ]
                }
            ],
            'full_content': str  # 整合后的完整文本内容
        }
    """
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
    
    print(f"开始解析PDF: {pdf_path}")
    pdf_document = fitz.open(pdf_path)
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
                    img_base64 = image_to_base64(image_bytes)
                    context = f"这是PDF第{page_num + 1}页中的第{img_index + 1}张图像。"
                    if text.strip():
                        context += f"\n\n页面文本上下文：\n{text[:500]}..."
                    
                    analysis = analyze_image_with_llm(img_base64, context)
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


def save_result_to_file(result: Dict, output_path: str):
    """将解析结果保存到文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result['full_content'])
    print(f"\n结果已保存到: {output_path}")


# 主程序
if __name__ == "__main__":
    # PDF文件路径
    pdf_path = r"D:\HAHA\Study\学习资料\知识星球\具身智能综述 网络空间与现实世界相融合.pdf"
    
    # 解析PDF
    result = parse_pdf_complete(pdf_path, analyze_images=True)
    
    # 打印摘要信息
    print(f"\n解析摘要：")
    print(f"- 总页数: {result['total_pages']}")
    print(f"- 总文本长度: {sum(len(p['text']) for p in result['pages'])} 字符")
    print(f"- 总图像数: {sum(len(p['images']) for p in result['pages'])} 个")
    
    # 保存完整内容到文件
    output_file = "pdf_complete_content.txt"
    save_result_to_file(result, output_file)
    
    # 也可以打印完整内容
    print("\n" + "="*80)
    print("完整PDF内容：")
    print("="*80)
    print(result['full_content'])
