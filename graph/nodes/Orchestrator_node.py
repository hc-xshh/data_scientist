"""
协调器节点模块

本模块实现了多Agent系统的核心协调器，负责：
1. 分析用户请求和当前状态
2. 通过工具调用决定路由到哪个专业Agent
3. 管理任务队列和工作流状态
4. 处理包含文件/图片的多模态消息
"""

from state.state import AgentState
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from models.Deepseek_Models import call_deepseek_chat
from tools.Tool_Router import routing_tools
from prompts.Prompt_Orchestrator import Prompt as OrchestratorPrompt
from utils import logger
from typing import List


def message_process(messages: List) -> List:
    """
    处理消息列表，将多模态内容转换为LLM可处理的纯文本格式
    
    功能：
    - 将文件信息转换为文本描述（文件名、类型、大小、URL）
    - 将图片信息转换为文本描述（URL标识）
    - 保留其他类型的消息内容不变
    
    Args:
        messages: 原始消息列表，可能包含多模态内容
        
    Returns:
        处理后的消息列表，所有多模态内容已转为文本描述
    """
    internal_messages = []
    
    for msg in messages:
        if hasattr(msg, 'content') and isinstance(msg.content, list):
            text_parts = []
            
            for item in msg.content:
                if isinstance(item, dict):
                    if item.get("type") == "file":
                        # 提取文件元数据
                        filename = item.get("metadata", {}).get("filename", "unknown")
                        size = item.get("metadata", {}).get("size", "unknown")
                        mime_type = item.get("mime_type", "unknown")
                        url = item.get("url", "")
                        
                        # 构造文本描述
                        file_description = (
                            f"[文件: {filename}, 类型: {mime_type}, "
                            f"大小: {size} bytes, URL: {url}]"
                        )
                        text_parts.append({"type": "text", "text": file_description})
                        
                    elif item.get("type") == "image":
                        # 构造图片文本描述
                        url = item.get("url", "")
                        image_description = f"[图片: 已上传图片, URL: {url}]"
                        text_parts.append({"type": "text", "text": image_description})
                        
                    else:
                        # 保留其他类型内容
                        text_parts.append(item)
                else:
                    text_parts.append(item)
            
            # 创建处理后的消息对象
            internal_msg = HumanMessage(
                content=text_parts,
                additional_kwargs=getattr(msg, 'additional_kwargs', {}),
                response_metadata=getattr(msg, 'response_metadata', {}),
                id=getattr(msg, 'id', None)
            )
            internal_messages.append(internal_msg)
        else:
            # 非列表内容直接保留
            internal_messages.append(msg)
    
    return internal_messages


def build_context_message(state: AgentState) -> str:
    """
    构建当前状态的上下文信息
    
    Args:
        state: 当前的Agent状态
        
    Returns:
        格式化的上下文字符串
    """
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else None
    last_agent = "None"
    
    if last_msg and isinstance(last_msg, AIMessage) and hasattr(last_msg, "name"):
        last_agent = last_msg.name
    
    context = f"""
【当前工作流状态】
- 待处理任务: {state.get('pending_tasks', [])}
- 当前任务: {state.get('current_task', 'None')}
- 最近完成的Agent: {last_agent}

【协调指令】
请根据用户需求和当前状态，调用合适的路由工具：
1. 如果需要查询/分析数据 → 调用 route_to_data_explorer
2. 如果需要分析文件 → 调用 route_to_file_analyzer
3. 如果需要生成报告/大屏/可视化 → 调用 route_to_reporter
4. 如果需要生成HTML页面/前端代码 → 调用 route_to_html_gen
5. 如果所有任务已完成 → 调用 finish_task

注意：
- 仔细分析用户意图，避免误判路由
- 如果需要先查数据再生成报告，先路由到数据探索，在reason中说明后续需要生成报告
- 检查pending_tasks，优先处理待办任务
"""
    return context


def prepare_messages_for_llm(messages: List, system_prompt: str, context: str) -> List[dict]:
    """
    将消息列表转换为LLM API需要的格式
    
    Args:
        messages: 已处理的消息列表
        system_prompt: 系统提示词
        context: 当前状态上下文
        
    Returns:
        符合LLM API格式的消息字典列表
    """
    messages_for_llm = [{"role": "system", "content": system_prompt}]
    
    for msg in messages:
        if isinstance(msg, HumanMessage):
            messages_for_llm.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            content = msg.content if msg.content else ""
            messages_for_llm.append({"role": "assistant", "content": content})
        elif isinstance(msg, ToolMessage):
            # 工具消息跳过（deepseek-chat不直接支持tool role）
            continue
    
    # 添加状态上下文
    messages_for_llm.append({"role": "user", "content": context})
    
    return messages_for_llm


def parse_routing_decision(response: AIMessage, state: AgentState) -> tuple:
    """
    解析LLM的路由决策
    
    Args:
        response: LLM的响应消息
        state: 当前状态
        
    Returns:
        (next_route, routing_reason, new_pending_tasks) 元组
    """
    next_route = "FINISH"
    routing_reason = ""
    new_pending_tasks = state.get("pending_tasks", []).copy()
    
    if not hasattr(response, "tool_calls") or not response.tool_calls:
        logger.warning("LLM未返回工具调用，默认结束流程")
        return next_route, "未检测到有效的路由决策", new_pending_tasks
    
    tool_call = response.tool_calls[0]
    tool_name = tool_call["name"]
    tool_args = tool_call.get("args", {})
    
    # 构建工具映射
    tool_map = {t.name: t for t in routing_tools}
    
    if tool_name not in tool_map:
        logger.error(f"未知的工具名称: {tool_name}")
        return next_route, f"调用了未知工具: {tool_name}", new_pending_tasks
    
    # 执行工具获取路由结果
    tool_result = tool_map[tool_name].invoke(tool_args)
    logger.info(f"工具 {tool_name} 执行结果: {tool_result}")
    
    # 解析结果格式: "ROUTE:Agent_Name|reason|..."
    parts = tool_result.split("|")
    if parts[0].startswith("ROUTE:"):
        next_route = parts[0].replace("ROUTE:", "")
        routing_reason = parts[1] if len(parts) > 1 else ""
        
        # 获取用户查询用于智能规划
        messages = state.get("messages", [])
        user_query = str([m.content for m in messages if isinstance(m, HumanMessage)])
        
        # 智能任务规划：如果是数据探索且用户提到生成报告/大屏
        if next_route == "Agent_Data_Explorer":
            if any(keyword in user_query for keyword in ["大屏", "报告", "可视化", "dashboard"]):
                if "生成可视化报告" not in new_pending_tasks:
                    new_pending_tasks.append("生成可视化报告")
                    logger.info("检测到需要后续生成报告，已添加到pending_tasks")
        
        # 智能任务规划：如果用户提到生成HTML页面
        if any(keyword in user_query for keyword in ["HTML", "页面", "前端", "web", "dashboard"]):
            if "生成HTML页面" not in new_pending_tasks:
                new_pending_tasks.append("生成HTML页面")
                logger.info("检测到需要后续生成HTML，已添加到pending_tasks")
    
    return next_route, routing_reason, new_pending_tasks


def Orchestrator_node(state: AgentState) -> AgentState:
    """
    协调器节点主函数
    
    工作流程：
    1. 预处理消息（多模态转文本）
    2. 构建上下文和系统提示
    3. 调用LLM进行路由决策
    4. 解析工具调用结果
    5. 更新状态并返回
    
    Args:
        state: 当前的Agent状态
        
    Returns:
        更新后的Agent状态，包含路由决策和新的消息
    """
    logger.info("=" * 50)
    logger.info("进入 Orchestrator 节点")
    
    # 步骤1: 预处理消息
    messages = state.get("messages", [])
    messages = message_process(messages)
    print("接收到的消息:", messages)
    # 步骤2: 构建系统提示和上下文
    system_prompt = OrchestratorPrompt
    context = build_context_message(state)
    
    # 步骤3: 准备LLM消息
    messages_for_llm = prepare_messages_for_llm(messages, system_prompt, context)
    
    # 步骤4: 调用LLM进行路由决策
    model = call_deepseek_chat(temperature=0.3)  # 降低温度以获得更稳定的路由决策
    model_with_tools = model.bind_tools(routing_tools)
    
    logger.info("调用LLM进行路由决策...")
    response = model_with_tools.invoke(messages_for_llm)
    
    # 步骤5: 解析路由决策
    next_route, routing_reason, new_pending_tasks = parse_routing_decision(response, state)
    
    logger.info(f"路由决策: {next_route}")
    logger.info(f"路由原因: {routing_reason}")
    logger.info(f"待处理任务: {new_pending_tasks}")
    
    # 步骤6: 更新消息历史
    updated_messages = messages + [response]
    
    # 添加工具消息到历史记录
    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_call = response.tool_calls[0]
        tool_msg = ToolMessage(
            content=f"路由至: {next_route}\n原因: {routing_reason}",
            tool_call_id=tool_call.get("id", ""),
            name=tool_call.get("name", "routing_tool")
        )
        updated_messages.append(tool_msg)
    
    logger.info("=" * 50)
    
    # 步骤7: 返回更新后的状态
    return {
        "next": next_route,
        "pending_tasks": new_pending_tasks,
        "current_task": routing_reason,
        "messages": updated_messages
    }