from state.state import AgentState
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_deepseek import ChatDeepSeek
from tools.Tool_Router import routing_tools  # 导入路由工具

def Orchestrator_node(state: AgentState) -> AgentState:
    """使用工具调用进行动态路由的Orchestrator"""
    
    messages = state.get("messages", [])
    
    # 1. 检查上一个Agent是否完成
    last_msg = messages[-1] if messages else None
    if last_msg and isinstance(last_msg, AIMessage):
        if hasattr(last_msg, "name") and last_msg.name in ["Agent_Data_Explorer", "Agent_Insighter_Reporter"]:
            # 检查是否还有待处理任务
            pending = state.get("pending_tasks", [])
            if not pending:
                # 所有任务完成，LLM会调用finish_task工具
                pass
    
    # 2. 构建系统提示词
    system_prompt = """
    你是一个智能任务协调器，负责分析用户需求并调用合适的工具来路由到专业Agent。
    
    你有以下路由工具可用：
    - route_to_data_explorer: 数据查询、分析、探索
    - route_to_reporter: 生成可视化、报告、大屏
    - finish_task: 所有任务完成，结束流程
    
    路由决策指南：
    1. 【只生成大屏】→ 直接调用 route_to_reporter
    2. 【根据数据生成大屏】→ 先调用 route_to_data_explorer（将"生成大屏"加入pending_tasks）
    3. 【只查看/分析数据】→ 调用 route_to_data_explorer
    
    注意事项：
    - 每次只调用一个路由工具
    - 如果需要多步骤，在reason中说明后续计划
    - 仔细阅读历史消息，避免重复调用
    - 检查pending_tasks中的待办事项
    """
    
    # 3. 准备消息
    messages_for_llm = [{"role": "system", "content": system_prompt}]
    
    for msg in messages:
        if isinstance(msg, HumanMessage):
            messages_for_llm.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            content = msg.content if msg.content else ""
            messages_for_llm.append({"role": "assistant", "content": content})
    
    # 添加当前状态上下文
    context = f"""
    当前状态：
    - 待处理任务: {state.get('pending_tasks', [])}
    - 当前任务: {state.get('current_task', 'None')}
    - 最近完成的Agent: {last_msg.name if last_msg and hasattr(last_msg, 'name') else 'None'}
    
    请根据用户问题和当前状态，调用合适的路由工具。
    """
    messages_for_llm.append({"role": "user", "content": context})
    
    # 4. 调用LLM with 工具
    model = ChatDeepSeek(model="deepseek-chat")
    model_with_tools = model.bind_tools(routing_tools)
    
    response = model_with_tools.invoke(messages_for_llm)
    
    # 5. 解析工具调用结果
    next_route = "FINISH"  # 默认结束
    routing_reason = ""
    new_pending_tasks = state.get("pending_tasks", []).copy()
    
    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_call = response.tool_calls[0]  # 取第一个工具调用
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        # 执行工具获取路由信息
        from langchain_core.tools import BaseTool
        tool_map = {t.name: t for t in routing_tools}
        
        if tool_name in tool_map:
            tool_result = tool_map[tool_name].invoke(tool_args)
            # 解析结果: "ROUTE:Agent_Data_Explorer|reason|output"
            parts = tool_result.split("|")
            if parts[0].startswith("ROUTE:"):
                next_route = parts[0].replace("ROUTE:", "")
                routing_reason = parts[1] if len(parts) > 1 else ""
                
                # 如果是数据探索且需要后续生成报告，添加到pending_tasks
                if next_route == "Agent_Data_Explorer" and "大屏" in str(messages):
                    if "生成报告" not in new_pending_tasks:
                        new_pending_tasks.append("生成可视化报告")
    
    # 6. 返回更新的状态
    # 将 LLM 响应添加到消息历史
    updated_messages = messages + [response]

    # 如果有工具调用，添加工具消息
    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_call = response.tool_calls[0]
        tool_name = tool_call["name"]

        # 添加 ToolMessage 记录路由决策
        tool_msg = ToolMessage(
            content=f"路由至：{next_route}，原因：{routing_reason}",
            tool_call_id = tool_call.get("id",""),
            name=tool_name
        )
        updated_messages.append(tool_msg)

    
    return {
        "next": next_route,
        "pending_tasks": new_pending_tasks,
        "current_task": routing_reason,
        "messages": updated_messages
    }