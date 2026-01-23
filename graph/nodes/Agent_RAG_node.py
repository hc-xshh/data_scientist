from state.state import AgentState
from langchain_core.messages import HumanMessage, AIMessage
from agents import Agent_RAG

def Agent_RAG_node(state: AgentState) -> AgentState:
    """RAG智能问答节点"""
    
    agent = Agent_RAG
    messages = state["messages"]
    
    # 提取Orchestrator的上下文
    context_parts = []
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) and hasattr(msg, "name"):
            if msg.name == "Orchestrator":
                context_parts.append(f"Orchestrator said: {msg.content}")
    
    if context_parts:
        context_msg = HumanMessage(
            content=f"""
            接收到Orchestrator的任务：
            {chr(10).join(reversed(context_parts))}
            
            【强制要求】请立即使用 retrieve_documents 工具检索知识库，然后基于检索结果回答。
            不要直接回答，不要拒绝，先检索！
            """
        )
        messages = list(messages) + [context_msg]
    
    result = agent.invoke({"messages": messages})
    
    if isinstance(result, dict) and "messages" in result:
        messages = result["messages"]
        if messages and isinstance(messages[-1], AIMessage):
            messages[-1].name = "Agent_RAG"
        return {"messages": messages}
    else:
        msg = AIMessage(content=str(result), name="Agent_RAG")
        return {"messages": [msg]}