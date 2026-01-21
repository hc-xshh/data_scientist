from state.state import AgentState
from langchain_core.messages import HumanMessage, AIMessage
from agents import Agent_Insighter_Reporter

def Agent_Insighter_Reporter_node(state: AgentState) -> AgentState:
    # Insighter Reporter Agent logic

    agent = Agent_Insighter_Reporter

    messages = state["messages"]

    context_parts = []
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) and hasattr(msg, "name"):
            if msg.name == "Orchestrator":
                context_parts.append(f"Orchestrator said: {msg.content}")
    
    if context_parts:
        context_msg = HumanMessage(
            content=f"请基于以下分析结果生成可视化大屏草图:\n\n{chr(10).join(reversed(context_parts))}\n\n生成一个专业、美观的数据大屏设计。"
        )
        messages = list(messages) + [context_msg]

    result = agent.invoke({"messages": messages})

    if isinstance(result, dict) and "messages" in result:
        messages = result["messages"]
        if messages and isinstance(messages[-1], AIMessage):
            messages[-1].name = "Agent_Insighter_Reporter"
        return {"messages": messages}
    else:
        msg = AIMessage(content=str(result), name="Agent_Insighter_Reporter")
        return {"messages": [msg]}