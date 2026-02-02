# PDF可视化分析技能

## 技能描述
该技能用于分析PDF文档中的可视化内容，通过将PDF页面转换为图像，使用多模态AI模型（Qwen-VL）对图表、架构图、流程图、界面设计等视觉内容进行深度分析。

## 核心功能
1. **PDF图像转换**：将PDF页面转换为高质量的图像格式
2. **智能压缩**：自动优化图像大小，平衡清晰度与性能
3. **多模态分析**：使用视觉语言模型深度解析可视化内容
4. **结构化提取**：识别并提取图表类型、数据、设计要点等信息

## 适用场景
- 分析商业报告中的图表和数据可视化
- 解读技术文档中的架构图和流程图
- 提取设计文稿中的界面原型和设计规范
- 分析可视化设计方案和仪表盘
- 理解包含大量图表的学术论文

## 技术特点
- 🎯 **智能分页**：支持指定分析页数，避免资源浪费
- 🖼️ **自适应缩放**：自动调整图像分辨率，防止内存溢出
- 💾 **高效压缩**：使用JPEG优化压缩，减小传输大小
- 🔍 **逐页分析**：独立分析每一页，提供详细反馈
- 📊 **多维解读**：从类型、描述、数据、设计多个维度分析

## 使用方法

### 基础调用
```python
from skills.pdf_analysis.pdf_analysis import analyze_pdf_visualizations

# 分析PDF文件
results = analyze_pdf_visualizations(
    pdf_path="path/to/your/document.pdf",
    max_pages=5  # 分析前5页
)

# 查看结果
for page_num, analysis in results.items():
    print(f"第{page_num}页分析：")
    print(analysis)
```

### 高级配置
```python
results = analyze_pdf_visualizations(
    pdf_path="path/to/your/document.pdf",
    max_pages=10,
    max_image_size=1920,  # 最大图像尺寸
    jpeg_quality=85,       # JPEG压缩质量
    dpi_scale=1.5         # PDF渲染DPI缩放
)
```

## 输入参数
- `pdf_path` (str): PDF文件的完整路径
- `max_pages` (int, 默认=5): 最多分析的页数
- `max_image_size` (int, 默认=1920): 图像最大宽度或高度（像素）
- `jpeg_quality` (int, 默认=85): JPEG压缩质量 (1-100)
- `dpi_scale` (float, 默认=1.5): PDF渲染分辨率倍数

## 输出格式
返回字典，键为页码，值为分析结果文本：
```python
{
    1: "图像类型分析...",
    2: "详细内容描述...",
    ...
}
```

每页分析包含：
1. **图像类型**：可视化类型识别（图表、架构图、流程图等）
2. **图像描述**：详细的视觉元素描述（标题、文字、图表、颜色、布局）
3. **数据信息**：提取的数值、指标、趋势和关键发现
4. **设计要点**：设计特点和亮点分析

## 依赖要求
```bash
pip install PyMuPDF Pillow openai
```

环境变量：
```bash
export DASHSCOPE_API_KEY="your_api_key"
```

## 注意事项
1. 确保PDF文件路径正确且文件可访问
2. 需要配置有效的 DASHSCOPE_API_KEY
3. 大型PDF建议限制 max_pages 避免长时间等待
4. 图像分辨率和压缩质量需根据实际需求平衡
5. API调用可能产生费用，请注意用量控制

## 性能优化建议
- 默认参数已针对大多数场景优化
- 如PDF图表较小，可适当提高 dpi_scale (如 2.0)
- 如需要更快处理，可降低 max_image_size (如 1280)
- 纯文字页面建议使用文本提取而非此技能

## 版本信息
- 版本：1.0.0
- 使用模型：qwen-vl-max
- 最后更新：2026-02-02
