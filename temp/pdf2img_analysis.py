import os
import base64
from pathlib import Path
from openai import OpenAI

# 安装依赖: pip install PyMuPDF Pillow
try:
    import fitz  # PyMuPDF
    from PIL import Image
    import io
except ImportError:
    print("请先安装依赖: pip install PyMuPDF Pillow")
    exit(1)

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

def pdf_to_base64_images(pdf_path, max_pages=5):
    """将PDF的前几页转换为base64编码的图像"""
    images = []
    pdf_document = fitz.open(pdf_path)
    
    for page_num in range(min(max_pages, len(pdf_document))):
        page = pdf_document[page_num]
        # 使用较低的分辨率以避免buffer overflow (从2降到1.5)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # 压缩图像到更小的尺寸
        max_size = 1920  # 最大宽度或高度
        if img.width > max_size or img.height > max_size:
            ratio = min(max_size / img.width, max_size / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # 转换为base64，使用JPEG格式并设置质量以减小文件大小
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85, optimize=True)
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        images.append(img_base64)
        
        print(f"  第{page_num + 1}页: {img.width}x{img.height}, {len(img_base64)/1024:.1f}KB")
    
    pdf_document.close()
    return images

# PDF文件路径
# pdf_path = r"D:\HAHA\项目\A公司\code\trae+skill\市场监测系统项目实施方案附件1_可视化设计方案.pdf"
pdf_path = r"D:\HAHA\Study\学习资料\知识星球\具身智能综述 网络空间与现实世界相融合.pdf"

if not Path(pdf_path).exists():
    print(f"文件不存在: {pdf_path}")
    exit(1)

print(f"正在分析PDF文件: {pdf_path}")
print("正在转换PDF为图像...")

# 将PDF转换为图像
images = pdf_to_base64_images(pdf_path, max_pages=3)  # 只分析前3页
print(f"已转换 {len(images)} 页")

# 逐页分析图像
print("\n开始分析每一页的图像...")

for idx, img_base64 in enumerate(images):
    page_num = idx + 1
    print(f"\n{'='*60}")
    print(f"第 {page_num} 页分析")
    print(f"{'='*60}")
    
    content = [
        {
            "type": "text",
            "text": """请全面分析这张图像的内容，包括：

1. **内容类型识别**：
   - 判断图像的主要类型（如：数据图表、文档页面、照片、截图、设计稿、架构图、流程图、思维导图、UI界面、广告海报、自然场景等）
   - 说明图像的用途或应用场景

2. **视觉元素描述**：
   - 文字内容：提取所有可见的标题、正文、标签、注释等文本信息
   - 图形元素：描述图表、图标、形状、线条、箭头等视觉组件
   - 图像内容：如包含照片或插图，描述其中的对象、人物、场景等
   - 颜色与风格：分析配色方案、设计风格、视觉层次

3. **结构与布局**：
   - 整体布局方式（单栏、多栏、分区等）
   - 内容组织逻辑和层级关系
   - 关键区域的位置和功能

4. **信息提取**：
   - 数据信息：如有数值、统计数据、指标等，请详细提取
   - 核心观点：总结图像传达的主要信息或结论
   - 重要细节：标注值得注意的特殊信息

5. **综合评价**（可选）：
   - 设计特点或技术亮点
   - 信息传达的有效性
   - 可能的改进建议

请根据图像的实际内容，灵活调整分析重点，尽可能详细和准确地描述。"""
        },
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{img_base64}"
            }
        }
    ]
    
    completion = client.chat.completions.create(
        model="qwen-vl-max",
        messages=[{"role": "user", "content": content}],
        stream=False,
    )
    
    print(completion.choices[0].message.content)
    print()

print(f"\n{'='*60}")
print("所有页面分析完成！")
print(f"{'='*60}")