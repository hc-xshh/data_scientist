from state.state import AgentState
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_deepseek import ChatDeepSeek
from tools.Tool_Router import routing_tools  # 导入路由工具
from prompts import OrchestratorPrompt

def message_process(messages :list):
    # 创建一个内部使用的消息副本，不影响前端显示
    internal_messages = []
    for msg in messages:
        if hasattr(msg, 'content') and isinstance(msg.content, list):
            # 重构内容，将文件和图片转换为文本描述
            text_parts = []
            for item in msg.content:
                if isinstance(item, dict):
                    if item.get("type") == "file":
                        # 将文件信息转换为文本描述
                        filename = item.get("metadata", {}).get("filename", "unknown")
                        size = item.get("metadata", {}).get("size", "unknown")
                        mime_type = item.get("mime_type", "unknown")
                        url = item.get("url", "")
                        
                        file_description = f"[文件: {filename}, 类型: {mime_type}, 大小: {size} bytes, URL: {url}]"
                        text_parts.append({"type": "text", "text": file_description})
                        
                    elif item.get("type") == "image":
                        # 将图片信息转换为文本描述
                        url = item.get("url", "")
                        image_description = f"[图片: 已上传图片, URL: {url}]"
                        text_parts.append({"type": "text", "text": image_description})
                    else:
                        # 保持其他类型的内容不变
                        text_parts.append(item)
                else:
                    # 如果不是字典，保持原样
                    text_parts.append(item)
            
            # 创建内部消息用于LLM处理
            internal_msg = HumanMessage(
                content=text_parts,
                additional_kwargs=getattr(msg, 'additional_kwargs', {}),
                response_metadata=getattr(msg, 'response_metadata', {}),
                id=getattr(msg, 'id', None)
            )
            internal_messages.append(internal_msg)
        else:
            # 如果消息内容不是列表，直接添加
            internal_messages.append(msg)

    return internal_messages
    

def Orchestrator_node(state: AgentState) -> AgentState:
    """使用工具调用进行动态路由的Orchestrator"""
    
    messages = state.get("messages", [])

    messages = message_process(messages)
    
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
    system_prompt = OrchestratorPrompt
    
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