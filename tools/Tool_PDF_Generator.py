import os
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from langchain_core.tools import tool
import json
import tempfile

# PDF文档相关依赖
try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.units import inch, cm
    from reportlab.platypus.flowables import KeepTogether
    PDF_AVAILABLE = True
except ImportError:
    print("⚠️ reportlab 未安装，PDF功能不可用")
    PDF_AVAILABLE = False

FILE_FOLDER = tempfile.gettempdir()


def create_pdf_document_structure(content: Union[str, Dict, List], config: Dict) -> Dict:
    """
    创建PDF文档结构
    
    Args:
        content: 文档内容，可以是字符串、字典或列表
        config: 文档配置（标题、作者、样式等）
    
    Returns:
        结构化的文档数据字典
    """
    # 如果是字符串，转换为结构
    if isinstance(content, str):
        try:
            # 尝试解析为JSON
            content_data = json.loads(content)
        except:
            # 如果是纯文本，创建简单结构
            content_data = {
                "title": config.get('title', 'AI生成文档'),
                "paragraphs": content.split('\n')
            }
    elif isinstance(content, list):
        # 如果是列表，转换为段落列表
        content_data = {
            "title": config.get('title', 'AI生成文档'),
            "paragraphs": content
        }
    else:
        # 已经是字典结构
        content_data = content
    
    # 确保有标题
    if 'title' not in content_data:
        content_data['title'] = config.get('title', 'AI生成文档')
    
    # 添加元数据
    if 'metadata' not in content_data:
        content_data['metadata'] = {}
    
    content_data['metadata'].update({
        'author': config.get('author', 'AI Assistant'),
        'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': config.get('version', '1.0'),
        'generator': 'AI PDF Generator'
    })
    
    return content_data


def create_pdf_styles():
    """
    创建PDF样式
    
    Returns:
        样式字典
    """
    if not PDF_AVAILABLE:
        return {}
    
    styles = getSampleStyleSheet()
    
    # 注册中文字体（如果可用）
    try:
        # 尝试注册常见中文字体
        font_paths = [
            'C:/Windows/Fonts/simsun.ttc',  # Windows 宋体
            '/System/Library/Fonts/PingFang.ttc',  # macOS 苹方
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',  # Linux 文泉驿
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                    print(f"✅ 注册中文字体: {font_path}")
                    break
                except:
                    continue
    except:
        print("⚠️ 无法注册中文字体，使用默认字体")
    
    # 标题样式
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=30,
        alignment=1,  # 居中
        fontName='ChineseFont' if 'ChineseFont' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold'
    ))
    
    # 一级标题样式
    styles.add(ParagraphStyle(
        name='CustomHeading1',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#34495E'),
        spaceBefore=20,
        spaceAfter=12,
        fontName='ChineseFont' if 'ChineseFont' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold'
    ))
    
    # 二级标题样式
    styles.add(ParagraphStyle(
        name='CustomHeading2',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2C3E50'),
        spaceBefore=15,
        spaceAfter=10,
        fontName='ChineseFont' if 'ChineseFont' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold'
    ))
    
    # 正文样式
    styles.add(ParagraphStyle(
        name='CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=8,
        leading=15,
        firstLineIndent=20,  # 首行缩进
        fontName='ChineseFont' if 'ChineseFont' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
    ))
    
    # 代码样式
    styles.add(ParagraphStyle(
        name='CustomCode',
        fontName='Courier',
        fontSize=9,
        textColor=colors.HexColor('#27AE60'),
        backColor=colors.HexColor('#F8F9F9'),
        borderPadding=5,
        leftIndent=10,
        spaceBefore=5,
        spaceAfter=5
    ))
    
    # 列表样式
    styles.add(ParagraphStyle(
        name='CustomList',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#2C3E50'),
        leftIndent=20,
        spaceAfter=6,
        fontName='ChineseFont' if 'ChineseFont' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
    ))
    
    # 元数据样式
    styles.add(ParagraphStyle(
        name='CustomMeta',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#7F8C8D'),
        alignment=1,  # 居中
        spaceAfter=15
    ))
    
    return styles


def create_pdf_document(content_data: Dict, config: Dict, output_path: str):
    """
    创建PDF文档并保存
    
    Args:
        content_data: 结构化文档数据
        config: 文档配置
        output_path: 输出文件路径
    """
    if not PDF_AVAILABLE:
        raise ImportError("reportlab未安装")
    
    # 创建文档模板
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # 获取样式
    styles = create_pdf_styles()
    
    # 构建文档内容
    story = []
    
    # 添加标题
    title = content_data.get('title', 'AI生成文档')
    story.append(Paragraph(title, styles['CustomTitle']))
    
    # 添加元数据
    if 'metadata' in content_data:
        metadata = content_data['metadata']
        meta_parts = []
        
        if 'author' in metadata:
            meta_parts.append(f"作者: {metadata['author']}")
        if 'generated_date' in metadata:
            meta_parts.append(f"生成时间: {metadata['generated_date']}")
        if 'version' in metadata:
            meta_parts.append(f"版本: {metadata['version']}")
        
        if meta_parts:
            story.append(Paragraph(" | ".join(meta_parts), styles['CustomMeta']))
    
    story.append(Spacer(1, 20))
    
    # 添加文档内容
    if 'sections' in content_data:
        for section_idx, section in enumerate(content_data['sections']):
            # 添加章节标题
            if 'title' in section:
                story.append(Paragraph(section['title'], styles['CustomHeading1']))
            
            # 添加章节内容
            if 'content' in section:
                content = section['content']
                _add_pdf_content(story, content, styles)
            
            # 如果不是最后一个章节，添加间距
            if section_idx < len(content_data['sections']) - 1:
                story.append(Spacer(1, 15))
    
    elif 'paragraphs' in content_data:
        # 添加段落
        for para_text in content_data['paragraphs']:
            if para_text.strip():
                story.append(Paragraph(para_text.strip(), styles['CustomBody']))
                story.append(Spacer(1, 5))
    
    elif 'content' in content_data:
        # 直接内容
        content = content_data['content']
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    _add_pdf_content(story, [item], styles)
                else:
                    story.append(Paragraph(str(item), styles['CustomBody']))
                    story.append(Spacer(1, 5))
        else:
            paragraphs = str(content).split('\n')
            for para_text in paragraphs:
                if para_text.strip():
                    story.append(Paragraph(para_text.strip(), styles['CustomBody']))
                    story.append(Spacer(1, 5))
    
    # 生成PDF文档
    doc.build(story)


def _add_pdf_content(story, content, styles):
    """
    添加PDF内容
    
    Args:
        story: 文档流列表
        content: 内容
        styles: 样式字典
    """
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                item_type = item.get('type', 'text')
                
                if item_type == 'text':
                    text = item.get('text', '')
                    if text:
                        story.append(Paragraph(text, styles['CustomBody']))
                        story.append(Spacer(1, 5))
                
                elif item_type == 'code':
                    code = item.get('code', '')
                    if code:
                        story.append(Paragraph(code, styles['CustomCode']))
                        story.append(Spacer(1, 5))
                
                elif item_type == 'list':
                    items = item.get('items', [])
                    ordered = item.get('ordered', False)
                    
                    for i, list_item in enumerate(items):
                        prefix = f"{i+1}. " if ordered else "• "
                        story.append(Paragraph(prefix + str(list_item), styles['CustomList']))
                        story.append(Spacer(1, 3))
                    
                    story.append(Spacer(1, 5))
                
                elif item_type == 'table':
                    data = item.get('data', [])
                    if data:
                        table = Table(data)
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 10),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9F9')),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
                        ]))
                        story.append(table)
                        story.append(Spacer(1, 10))
            else:
                story.append(Paragraph(str(item), styles['CustomBody']))
                story.append(Spacer(1, 5))
    else:
        story.append(Paragraph(str(content), styles['CustomBody']))
        story.append(Spacer(1, 5))


@tool
def generate_pdf_document(
    content: Union[str, Dict, List],
    title: str = "AI生成文档",
    author: str = "AI Assistant",
    template_type: str = "professional",
    output_filename: Optional[str] = None,
    save_dir: Optional[str] = None
) -> str:
    """
    生成PDF格式的文档
    
    参数:
        content: 文档内容，可以是：
            - 文本字符串
            - JSON字符串
            - 字典结构
            - 列表
            
            字典结构示例:
            {
                "title": "文档标题",
                "metadata": {
                    "author": "作者",
                    "version": "1.0"
                },
                "sections": [
                    {
                        "title": "章节1",
                        "content": [
                            {"type": "text", "text": "段落内容"},
                            {"type": "list", "items": ["项1", "项2"]},
                            {"type": "code", "code": "print('Hello')"},
                            {"type": "table", "data": [["标题1", "标题2"], ["数据1", "数据2"]]}
                        ]
                    }
                ]
            }
        
        title: 文档标题
        author: 作者
        template_type: 模板类型 (professional/modern/simple)
        output_filename: 输出文件名（不指定则自动生成）
        save_dir: 保存目录（不指定则使用默认temp目录）
    
    返回:
        生成的PDF文档文件路径和下载URL
    
    示例:
        generate_pdf_document(
            content="这是一个测试文档内容",
            title="测试文档",
            author="张三"
        )
    """
    try:
        if not PDF_AVAILABLE:
            return "❌ 错误: reportlab库未安装，无法生成PDF文档。请安装: pip install reportlab"
        
        # 准备保存目录
        if save_dir is None:
            save_dir = FILE_FOLDER
        
        os.makedirs(save_dir, exist_ok=True)
        
        # 生成文件名
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title[:50]  # 限制长度
            output_filename = f"{safe_title}_{timestamp}.pdf"
        
        if not output_filename.endswith('.pdf'):
            output_filename += '.pdf'
        
        output_path = os.path.join(save_dir, output_filename)
        
        # 创建文档配置
        config = {
            'title': title,
            'author': author,
            'template_type': template_type
        }
        
        # 创建文档结构
        content_data = create_pdf_document_structure(content, config)
        
        # 生成PDF文档
        create_pdf_document(content_data, config, output_path)
        
        print(f"✅ PDF文档已生成: {output_path}")
        print(f"📄 文件大小: {os.path.getsize(output_path):,} 字节")
        print(f"📝 文档标题: {title}")
        print(f"👤 作者: {author}")
        
        # 生成下载URL
        file_url = f"http://localhost:5000/download/{os.path.basename(output_path)}"
        preview_url = f"http://localhost:5000/preview/{os.path.basename(output_path)}"
        
        return f"""
🎉 PDF文档生成成功！

📋 文档信息：
• 文档标题：{title}
• 作    者：{author}
• 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• 文件格式：PDF (便携式文档格式)
• 文件大小：{os.path.getsize(output_path):,} 字节

📎 文件访问：
• 📍 本地路径：{output_path}
• ⬇️  下载链接：{file_url}
• 👁️  在线预览：{preview_url}

💡 使用说明：
1. 点击下载链接可以直接保存文档
2. 使用预览链接可以在浏览器中查看
3. PDF文档适合打印和正式场合使用
4. 支持Adobe Reader、Chrome、Edge等打开

🔄 如需重新生成或转换为其他格式，请告诉我！
"""
    
    except Exception as e:
        error_msg = f"❌ 生成PDF文档失败: {str(e)}"
        print(error_msg)
        return error_msg


@tool
def quick_pdf_generate(
    text: str,
    title: str = "快速生成文档",
    author: str = "AI Assistant"
) -> str:
    """
    快速生成PDF文档（简化接口）
    
    参数:
        text: 文档内容文本
        title: 文档标题
        author: 作者信息
    
    返回:
        PDF文档下载链接
    
    示例:
        quick_pdf_generate(
            text="这是一个快速生成的测试文档...",
            title="测试报告",
            author="李四"
        )
    """
    return generate_pdf_document.invoke({
        "content": text,
        "title": title,
        "author": author,
        "template_type": "simple"
    })


@tool
def generate_document(
    content: Union[str, Dict, List],
    title: str = "AI生成文档",
    author: str = "AI Assistant",
    format: str = "pdf",
    output_filename: Optional[str] = None,
    save_dir: Optional[str] = None
) -> str:
    """
    智能生成文档（支持PDF和Word格式）
    
    参数:
        content: 文档内容
        title: 文档标题
        author: 作者信息
        format: 文档格式，支持 'pdf' 或 'docx'
        output_filename: 输出文件名
        save_dir: 保存目录
    
    返回:
        生成的文档文件路径和下载URL
    """
    format_lower = format.lower()
    
    if format_lower == 'pdf':
        return generate_pdf_document.invoke({
            "content": content,
            "title": title,
            "author": author,
            "output_filename": output_filename,
            "save_dir": save_dir
        })
    elif format_lower in ['docx', 'word']:
        # 需要导入Word生成工具
        try:
            from Tool_Word_Generator import generate_word_document
            return generate_word_document.invoke({
                "content": content,
                "title": title,
                "author": author,
                "output_filename": output_filename,
                "save_dir": save_dir
            })
        except ImportError:
            return "❌ 错误: Word文档生成工具不可用"
    else:
        return f"❌ 错误: 不支持的格式 '{format}'，请使用 'pdf' 或 'docx'"


# 测试函数
def test_pdf_generation():
    """测试PDF文档生成"""
    print("🧪 测试PDF文档生成工具...")
    
    # 测试1：简单文本
    print("\n📝 测试1：简单文本生成")
    result = generate_pdf_document.invoke({
        "content": "这是一个简单的测试PDF文档。\n包含多行内容。\n第一行。\n第二行。\n第三行内容稍长一些。",
        "title": "测试PDF文档",
        "author": "测试用户"
    })
    print(f"结果: {result}")
    
    # 测试2：结构化内容
    print("\n📊 测试2：结构化内容生成")
    structured_content = {
        "title": "项目技术方案",
        "metadata": {
            "author": "技术团队",
            "department": "研发部",
            "version": "2.0",
            "confidential": "内部使用"
        },
        "sections": [
            {
                "title": "项目概述",
                "content": [
                    {"type": "text", "text": "本项目旨在开发一个智能文档生成系统。"},
                    {"type": "list", "items": [
                        "支持多种文档格式生成",
                        "提供丰富的模板库",
                        "支持自定义样式",
                        "易于集成到现有系统"
                    ]},
                    {"type": "text", "text": "系统将大大提高文档编写效率。"}
                ]
            },
            {
                "title": "技术架构",
                "content": [
                    {"type": "text", "text": "采用微服务架构设计："},
                    {"type": "table", "data": [
                        ["组件", "技术栈", "描述"],
                        ["前端", "Vue.js + ElementUI", "用户界面"],
                        ["后端", "Python + FastAPI", "业务逻辑"],
                        ["文档生成", "python-docx + reportlab", "文档处理"],
                        ["数据库", "PostgreSQL", "数据存储"],
                        ["缓存", "Redis", "性能优化"]
                    ]},
                    {"type": "code", "code": "# 示例代码\ndef generate_document(content, format='pdf'):\n    if format == 'pdf':\n        return generate_pdf(content)\n    else:\n        return generate_word(content)"}
                ]
            }
        ]
    }
    
    result = generate_pdf_document.invoke({
        "content": json.dumps(structured_content, ensure_ascii=False),
        "title": "技术方案文档",
        "author": "架构师团队",
        "template_type": "professional"
    })
    print(f"结果: {result}")


if __name__ == "__main__":
    test_pdf_generation()