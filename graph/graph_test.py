from state.state import AgentState
def route_orchestrator(state: AgentState) -> str:
    """
    解析Orchestrator通过工具调用决定的路由
    这个函数非常简单，只需要读取state["next"]即可
    """
    next_agent = state.get("next", "FINISH")
    
    # 可以添加日志
    print(f"🔀 路由到: {next_agent}")
    print(f"📋 待处理任务: {state.get('pending_tasks', [])}")
    
    return next_agent


def create_workflow():
    from langgraph.graph import StateGraph, END, START
    from state.state import AgentState
    from graph.nodes import (
        Orchestrator_node,
        Agent_Data_Explorer_node,
        Agent_Insighter_Reporter_node
    )
    
    workflow = StateGraph(AgentState)
    
    # 添加所有节点
    workflow.add_node("Orchestrator", Orchestrator_node)
    workflow.add_node("Agent_Data_Explorer", Agent_Data_Explorer_node)
    workflow.add_node("Agent_Insighter_Reporter", Agent_Insighter_Reporter_node)
    # 未来添加: workflow.add_node("QA_Agent", QA_Agent_node)
    
    # 起始边
    workflow.add_edge(START, "Orchestrator")
    
    # 条件路由 - 所有分支都由LLM的工具调用决定
    workflow.add_conditional_edges(
        "Orchestrator",
        route_orchestrator,
        {
            "Agent_Data_Explorer": "Agent_Data_Explorer",
            "Agent_Insighter_Reporter": "Agent_Insighter_Reporter",
            # "QA_Agent": "QA_Agent",  # 未来启用
            "FINISH": END
        }
    )
    
    # 所有Agent完成后返回Orchestrator重新评估
    workflow.add_edge("Agent_Data_Explorer", "Orchestrator")
    workflow.add_edge("Agent_Insighter_Reporter", "Orchestrator")
    
    return workflow.compile()

app = create_workflow()