from state.state import AgentState
from langchain_core.messages import HumanMessage, AIMessage
from agents import Agent_Data_Explorer

def Agent_Data_Explorer_node(state: AgentState) -> AgentState:
    # Data Explorer Agent logic

    agent = Agent_Data_Explorer

    messages = state["messages"]

    context_parts = []
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) and hasattr(msg, "name"):
            if msg.name == "Orchestrator":
                context_parts.append(f"Orchestrator said: {msg.content}")
    
    if context_parts:
        context_msg = HumanMessage(
            content=f"""
            你是一个数据分析专家，擅长使用Python进行数据探索性分析。
            你可以使用提供的工具来查询数据库中的表结构和数据。
            请根据用户的问题
             {chr(10).join(reversed(context_parts))}
             ，选择合适的工具进行查询，
            并给出详细的分析结果和可视化建议。
            """
        )
        messages = list(messages) + [context_msg]

    result = agent.invoke({"messages": messages})

    if isinstance(result, dict) and "messages" in result:
        messages = result["messages"]
        if messages and isinstance(messages[-1], AIMessage):
            messages[-1].name = "Agent_Data_Explorer"
        return {"messages": messages}
    else:
        msg = AIMessage(content=str(result), name="Agent_Data_Explorer")
        return {"messages": [msg]}