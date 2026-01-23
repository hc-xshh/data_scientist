from langgraph.graph import StateGraph, END, START
from state.state import AgentState
from graph.nodes import (
    Orchestrator_node, 
    Agent_Insighter_Reporter_node,
    Agent_Data_Explorer_node,
    Agent_RAG_node
)

def route_orchestrator(state: AgentState) -> str:
    """Orchestrator路由逻辑"""
    # 直接从state中读取next字段
    next_node = state.get("next", "FINISH")
    
    # 如果next_node为空或者是"FINISH"，则结束
    if not next_node or next_node == "FINISH":
        return "FINISH"
    
    return next_node

def create_workflow():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("Orchestrator", Orchestrator_node)
    workflow.add_node("Agent_Data_Explorer", Agent_Data_Explorer_node)
    workflow.add_node("Agent_Insighter_Reporter", Agent_Insighter_Reporter_node)
    workflow.add_node("Agent_RAG", Agent_RAG_node) 
    workflow.add_edge(START, "Orchestrator")
    
    workflow.add_conditional_edges(
        "Orchestrator",
        route_orchestrator,
        {
            "Agent_Data_Explorer": "Agent_Data_Explorer",
            "Agent_Insighter_Reporter": "Agent_Insighter_Reporter",
            "Agent_RAG": "Agent_RAG", 
            "FINISH": END
        }
    )
    
    workflow.add_edge("Agent_Data_Explorer", "Orchestrator")
    workflow.add_edge("Agent_Insighter_Reporter", "Orchestrator")
    workflow.add_edge("Agent_RAG", "Orchestrator") 

    app = workflow.compile()
    return app

app = create_workflow()