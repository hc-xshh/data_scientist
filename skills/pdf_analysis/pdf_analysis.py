"""
PDF可视化分析技能

使用多模态AI模型分析PDF文档中的可视化内容，包括图表、架构图、流程图等。
将PDF页面转换为图像后，利用Qwen-VL模型进行深度视觉分析。
"""

import os
import base64
from pathlib import Path
from typing import List, Dict, Optional
from openai import OpenAI

try:
    import fitz  # PyMuPDF
    from PIL import Image
    import io
except ImportError:
    raise ImportError("请先安装依赖: pip install PyMuPDF Pillow")


def pdf_to_base64_images(
    pdf_path: str,
    max_pages: int = 5,
    max_size: int = 1920,
    jpeg_quality: int = 85,
    dpi_scale: float = 1.5
) -> List[str]:
    """
    将PDF的前几页转换为base64编码的图像
    
    Args:
        pdf_path: PDF文件路径
        max_pages: 最多转换的页数
        max_size: 图像最大宽度或高度（像素）
        jpeg_quality: JPEG压缩质量 (1-100)
        dpi_scale: PDF渲染分辨率倍数
        
    Returns:
        base64编码的图像列表
    """
    images = []
    pdf_document = fitz.open(pdf_path)
    
    for page_num in range(min(max_pages, len(pdf_document))):
        page = pdf_document[page_num]
        # 使用指定的分辨率渲染PDF页面
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi_scale, dpi_scale))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # 压缩图像到指定尺寸
        if img.width > max_size or img.height > max_size:
            ratio = min(max_size / img.width, max_size / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # 转换为base64，使用JPEG格式并设置质量
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=jpeg_quality, optimize=True)
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        images.append(img_base64)
        
        print(f"  第{page_num + 1}页: {img.width}x{img.height}, {len(img_base64)/1024:.1f}KB")
    
    pdf_document.close()
    return images


def analyze_single_page(
    client: OpenAI,
    img_base64: str,
    page_num: int,
    model: str = "qwen-vl-max"
) -> str:
    """
    分析单个PDF页面的图像内容
    
    Args:
        client: OpenAI客户端实例
        img_base64: base64编码的图像
        page_num: 页码
        model: 使用的模型名称
        
    Returns:
        分析结果文本
    """
    content = [
        {
            "type": "text",
            "text": """请详细分析这张图像中的内容，包括：

1. **图像类型**：识别这是什么类型的可视化（图表、架构图、流程图、界面设计等）

2. **图像描述**：详细描述图像中的所有可视化元素：
   - 标题和主要文字内容
   - 图表类型（柱状图、折线图、饼图、仪表盘等）
   - 颜色方案和设计风格
   - 布局结构

3. **数据信息**：如果包含数据，请提取：
   - 具体的数值和指标
   - 数据的含义和趋势
   - 关键发现

4. **设计要点**：分析设计特点和亮点

请尽可能详细和准确地描述图像内容。"""
        },
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{img_base64}"
            }
        }
    ]
    
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": content}],
        stream=False,
    )
    
    return completion.choices[0].message.content


def analyze_pdf_visualizations(
    pdf_path: str,
    max_pages: int = 5,
    max_image_size: int = 1920,
    jpeg_quality: int = 85,
    dpi_scale: float = 1.5,
    api_key: Optional[str] = None,
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
    model: str = "qwen-vl-max",
    verbose: bool = True
) -> Dict[int, str]:
    """
    分析PDF文件中的可视化内容
    
    Args:
        pdf_path: PDF文件路径
        max_pages: 最多分析的页数
        max_image_size: 图像最大尺寸
        jpeg_quality: JPEG压缩质量
        dpi_scale: PDF渲染DPI倍数
        api_key: API密钥（如不提供则从环境变量读取）
        base_url: API基础URL
        model: 使用的模型名称
        verbose: 是否打印详细信息
        
    Returns:
        字典，键为页码，值为分析结果
        
    Raises:
        FileNotFoundError: PDF文件不存在
        ValueError: API密钥未配置
    """
    # 验证文件存在
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
    
    # 获取API密钥
    if api_key is None:
        api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("未配置DASHSCOPE_API_KEY环境变量或未提供api_key参数")
    
    # 初始化客户端
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    if verbose:
        print(f"正在分析PDF文件: {pdf_path}")
        print("正在转换PDF为图像...")
    
    # 将PDF转换为图像
    images = pdf_to_base64_images(
        pdf_path=pdf_path,
        max_pages=max_pages,
        max_size=max_image_size,
        jpeg_quality=jpeg_quality,
        dpi_scale=dpi_scale
    )
    
    if verbose:
        print(f"已转换 {len(images)} 页")
        print("\n开始分析每一页的图像...")
    
    # 逐页分析
    results = {}
    for idx, img_base64 in enumerate(images):
        page_num = idx + 1
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"第 {page_num} 页分析")
            print(f"{'='*60}")
        
        analysis = analyze_single_page(
            client=client,
            img_base64=img_base64,
            page_num=page_num,
            model=model
        )
        
        results[page_num] = analysis
        
        if verbose:
            print(analysis)
            print()
    
    if verbose:
        print(f"\n{'='*60}")
        print("所有页面分析完成！")
        print(f"{'='*60}")
    
    return results


def main():
    """
    命令行测试入口
    """
    # 示例用法
    pdf_path = r"D:\HAHA\项目\A公司\code\trae+skill\市场监测系统项目实施方案附件1_可视化设计方案.pdf"
    
    try:
        results = analyze_pdf_visualizations(
            pdf_path=pdf_path,
            max_pages=3,
            verbose=True
        )
        
        # 可以进一步处理结果
        print("\n分析结果汇总：")
        for page_num, analysis in results.items():
            print(f"\n第{page_num}页关键信息：")
            print(analysis[:200] + "..." if len(analysis) > 200 else analysis)
            
    except Exception as e:
        print(f"分析失败: {e}")
        raise


if __name__ == "__main__":
    main()
