"""
状态管理模块

本模块定义了LangGraph工作流中的核心状态类和路由响应类，用于管理Agent之间的通信、任务调度和工作流控制。
"""

# 导入类型提示相关的模块
from typing import TypedDict, Annotated, Sequence, List
# 导入LangChain核心消息类，用于表示对话消息
from langchain_core.messages import BaseMessage
# 导入LangGraph的消息处理函数，用于自动合并和管理消息序列
from langgraph.graph.message import add_messages
# 导入Pydantic基础模型类，用于数据验证
from pydantic import BaseModel
# 导入字面量类型，用于限定字符串值的范围
from typing import Literal


class AgentState(TypedDict):
    """
    Agent状态类
    
    定义了整个多Agent系统中共享的状态结构。这个状态会在不同的Agent节点之间传递，
    记录对话历史、任务进度和控制流信息。
    
    属性说明：
        messages: 消息序列，存储整个对话历史
            - 使用Annotated标注，配合add_messages函数实现消息自动追加
            - add_messages是一个reducer函数，每次状态更新时会自动将新消息追加到序列末尾
            - 这样可以保持完整的对话上下文，供各个Agent使用
        
        next: 下一个要执行的Agent节点名称
            - 用于控制工作流的路由方向
            - 由当前Agent决定下一步应该由哪个Agent处理
            - 例如: "Agent_Data_Explorer", "Agent_Model_Builder" 等
        
        task_completed: 当前任务完成标志
            - 布尔值，指示当前处理的任务是否已经完成
            - True表示任务完成，可以继续下一个任务
            - False表示任务仍在进行中
        
        pending_tasks: 待处理任务列表
            - 存储所有尚未处理的任务描述
            - 每个元素是一个字符串，描述一个具体的任务
            - Orchestrator会根据这个列表动态分配任务给合适的Agent
        
        current_task: 当前正在处理的任务
            - 字符串类型，描述当前Agent正在执行的具体任务
            - 帮助各个Agent明确自己当前的工作目标
            - 便于调试和日志记录
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next: str   # 下一个Agent节点的名称
    task_completed: bool      # 当前任务是否已完成的标志
    pending_tasks: List[str]    # 待处理任务的列表
    current_task: str         # 当前正在处理的任务描述

