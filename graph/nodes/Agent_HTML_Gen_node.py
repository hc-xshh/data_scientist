from state.state import AgentState
from langchain_core.messages import HumanMessage, AIMessage
from agents import Agent_HTML_Gen

def Agent_HTML_Gen_node(state: AgentState) -> AgentState:
    # HTML生成Agent逻辑
    agent = Agent_HTML_Gen
    messages = state["messages"]

    context_parts = []
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) and hasattr(msg, "name"):
            if msg.name == "Orchestrator":
                context_parts.append(f"Orchestrator said: {msg.content}")
    
    if context_parts:
        context_msg = HumanMessage(
            content=f"""
            你是一个数据可视化和前端开发专家，擅长根据分析结果生成高质量的HTML页面和可视化大屏。
            请根据以下分析/设计需求：
            {chr(10).join(reversed(context_parts))}
            生成专业、美观、易用的HTML代码，并给出可视化建议。
            """
        )
        messages = list(messages) + [context_msg]

    result = agent.invoke({"messages": messages})

    if isinstance(result, dict) and "messages" in result:
        messages = result["messages"]
        if messages and isinstance(messages[-1], AIMessage):
            messages[-1].name = "Agent_HTML_Gen"
        return {"messages": messages}
    else:
        msg = AIMessage(content=str(result), name="Agent_HTML_Gen")
        return {"messages": [msg]}
