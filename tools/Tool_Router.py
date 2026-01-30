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
    file_type: str = Field(description="文件类型:CSV/Excel/JSON/TXT等")
    analysis_goal: str = Field(description="分析目标")

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
    当用户需要分析文件内容、读取文件数据时调用此工具。
    
    适用场景:
    - 读取和解析CSV、Excel文件
    - 分析JSON、XML数据文件
    - 处理文本文件
    - 提取文件中的数据特征
    - 文件格式转换
    - 批量文件处理
    
    注意:此工具专门处理文件,如果是数据库操作请使用route_to_data_explorer。
    """
    return f"ROUTE:Agent_File_Analysis|{reason}|{file_type}|{analysis_goal}"

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
    finish_task
]