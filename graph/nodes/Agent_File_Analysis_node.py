from state.state import AgentState
from langchain_core.messages import HumanMessage, AIMessage
from agents import Agent_File_Analysis

def Agent_File_Analysis_node(state: AgentState) -> AgentState:
    # File Analysis Agent logic

    agent = Agent_File_Analysis

    messages = state["messages"]

    context_parts = []
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) and hasattr(msg, "name"):
            if msg.name == "Orchestrator":
                context_parts.append(f"Orchestrator said: {msg.content}")
    
    if context_parts:
        context_msg = HumanMessage(
            content=f"""
            你是一个文件分析专家，擅长解析和分析各种数据文件(PDF、Word、CSV、Excel、JSON等)。
            
            用户的问题：
            {chr(10).join(reversed(context_parts))}
            
            请使用 analyze_file 工具来读取文件内容（工具支持HTTP/HTTPS URL）。
            工具会自动识别文件类型并提取完整内容，返回Markdown格式的分析结果。
            
            基于提取的内容，给出：
            1. 文件基本信息
            2. 数据质量分析（如适用）
            3. 关键发现和洞察
            """
        )
        messages = list(messages) + [context_msg]

    result = agent.invoke({"messages": messages})

    if isinstance(result, dict) and "messages" in result:
        messages = result["messages"]
        if messages and isinstance(messages[-1], AIMessage):
            messages[-1].name = "Agent_File_Analysis"
        return {"messages": messages}
    else:
        msg = AIMessage(content=str(result), name="Agent_File_Analysis")
        return {"messages": [msg]}