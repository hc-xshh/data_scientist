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
pdf_path = r"D:\HAHA\项目\A公司\code\trae+skill\市场监测系统项目实施方案附件1_可视化设计方案.pdf"

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
        model="qwen-vl-max",
        messages=[{"role": "user", "content": content}],
        stream=False,
    )
    
    print(completion.choices[0].message.content)
    print()

print(f"\n{'='*60}")
print("所有页面分析完成！")
print(f"{'='*60}")