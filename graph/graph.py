from langgraph.graph import StateGraph, END, START
from state.state import AgentState
from graph.nodes import (
    Orchestrator_node, 
    Agent_Insighter_Reporter_node,
    Agent_Data_Explorer_node,
    Agent_File_Analysis_node
)

def route_orchestrator(state: AgentState) -> str:
    """Orchestrator路由逻辑"""
    # 直接从state中读取next字段
    next_node = state.get("next", "FINISH")
    
    # 添加有效节点验证
    valid_nodes = {"Agent_Data_Explorer", "Agent_Insighter_Reporter", "Agent_File_Analysis", "FINISH"}

    if not next_node or next_node not in valid_nodes:
        return "FINISH"
    
    return next_node

def create_workflow():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("Orchestrator", Orchestrator_node)
    workflow.add_node("Agent_Data_Explorer", Agent_Data_Explorer_node)
    workflow.add_node("Agent_Insighter_Reporter", Agent_Insighter_Reporter_node)
    workflow.add_node("Agent_File_Analysis", Agent_File_Analysis_node)
    workflow.add_edge(START, "Orchestrator")
    
    workflow.add_conditional_edges(
        "Orchestrator",
        route_orchestrator,
        {
            "Agent_Data_Explorer": "Agent_Data_Explorer",
            "Agent_Insighter_Reporter": "Agent_Insighter_Reporter",
            "Agent_File_Analysis": "Agent_File_Analysis",
            "FINISH": END
        }
    )
    
    workflow.add_edge("Agent_Data_Explorer", "Orchestrator")
    workflow.add_edge("Agent_Insighter_Reporter", "Orchestrator")
    workflow.add_edge("Agent_File_Analysis", "Orchestrator")

    app = workflow.compile()
    return app

app = create_workflow()