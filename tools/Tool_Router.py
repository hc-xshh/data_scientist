from langchain_core.tools import tool
from pydantic import BaseModel, Field


# 工具参数定义
class RouteToDataExplorer(BaseModel):
    """路由到数据探索Agent的参数"""
    reason: str = Field(description="为什么需要数据探索")
    expected_output: str = Field(description="期望的输出结果")

class RouteToReporter(BaseModel):
    """路由到报告生成Agent的参数"""
    reason: str = Field(description="为什么需要生成报告")
    visualization_type: str = Field(description="可视化类型:大屏/图表/报告等")

class RouteToFileAnalyzer(BaseModel):
    """路由到文件分析Agent的参数"""
    reason: str = Field(description="为什么需要分析文件")
    file_type: str = Field(description="文件类型:PDF/Word/图像等")
    analysis_goal: str = Field(description="分析目标:内容提取/图表识别/文档理解等")

class RouteToHTMLGen(BaseModel):
    """路由到HTML生成Agent的参数"""
    reason: str = Field(description="为什么需要生成HTML页面")
    html_goal: str = Field(description="HTML页面的设计目标或内容要求")

class FinishTask(BaseModel):
    """结束任务的参数"""
    reason: str = Field(description="为什么结束任务")
    summary: str = Field(description="任务总结")


# 定义路由工具

@tool(args_schema=RouteToDataExplorer)
def route_to_data_explorer(reason: str, expected_output: str) -> str:
    """
    当用户需要查看、分析、统计、探索数据库数据时调用此工具。
    
    适用场景:
    - 查看数据库中的表和字段
    - 分析数据的统计特征
    - 探索数据分布和相关性
    - 数据清洗和预处理
    - 执行SQL查询
    """
    return f"ROUTE:Agent_Data_Explorer|{reason}|{expected_output}"

@tool(args_schema=RouteToReporter)
def route_to_reporter(reason: str, visualization_type: str) -> str:
    """
    当用户需要生成可视化大屏、图表、报告时调用此工具。
    
    适用场景:
    - 生成数据可视化大屏
    - 制作数据分析报告
    - 创建数据图表
    - 可视化展示分析结果
    
    注意:如果需要基于数据库数据生成报告,应该先调用route_to_data_explorer获取数据。
    """
    return f"ROUTE:Agent_Insighter_Reporter|{reason}|{visualization_type}"

@tool(args_schema=RouteToFileAnalyzer)
def route_to_file_analyzer(reason: str, file_type: str, analysis_goal: str) -> str:
    """
    当用户需要解析和分析PDF文档、Word文档、图像文件或数据文件时调用此工具。
    
    适用场景:
    - 解析PDF文档，提取文本、图像和表格内容，支持学术论文、商业报告等
    - 解析Word文档(.docx)，提取文本、图像和表格，保留文档层次结构
    - 分析图像文件，识别图表、截图、照片中的内容，使用视觉模型理解图像
    - 解析Excel、CSV等数据文件，提取数据内容和统计信息
    - 使用视觉大模型深度理解文档中的图像、图表和复杂布局
    - 提取学术论文、合同、技术文档的完整内容和结构信息
    - 识别图像中的文字(OCR)、物体、场景、图表元素
    - 分析数据可视化图表、截图、设计稿
    - 提取Excel表格的数据概览、统计信息、多工作表内容
    
    支持格式:
    - PDF文档 (.pdf)
    - Word文档 (.docx)
    - 图像文件 (JPG、PNG、BMP、GIF、WEBP等)
    - 数据文件 (Excel .xlsx/.xls, CSV .csv等)
    
    重要特性:
    - 所有工具都支持本地文件路径和HTTP/HTTPS URL
    - 上传文件URL格式: http://localhost:5000/files/文件名
    - 自动启用视觉模型分析图像，获得更深入的内容理解
    - Excel文件支持多工作表解析和数据统计
    
    注意:此工具专门处理文档、图像和数据文件的内容解析与分析。
    如果需要对数据库进行SQL查询或数据探索，请使用route_to_data_explorer。
    """
    return f"ROUTE:Agent_File_Analysis|{reason}|{file_type}|{analysis_goal}"

@tool(args_schema=RouteToHTMLGen)
def route_to_html_gen(reason: str, html_goal: str) -> str:
    """
    当用户需要生成HTML页面或数据可视化前端代码时调用此工具。
    
    适用场景:
    - 生成数据可视化大屏的HTML代码
    - 根据分析结果生成前端页面
    - 制作交互式可视化组件
    - 输出美观、专业的HTML结构
    """
    return f"ROUTE:Agent_HTML_Gen|{reason}|{html_goal}"

@tool(args_schema=FinishTask)
def finish_task(reason: str, summary: str) -> str:
    """
    当所有任务已完成,可以结束流程时调用此工具。
    
    适用场景:
    - 用户的问题已经完全回答
    - 所有分析和可视化都已完成
    - 没有其他待处理的任务
    """
    return f"ROUTE:FINISH|{reason}|{summary}"

# 导出所有路由工具
routing_tools = [
    route_to_data_explorer,
    route_to_reporter,
    route_to_file_analyzer,
    route_to_html_gen,
    finish_task
]