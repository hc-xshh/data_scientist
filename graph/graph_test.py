from langgraph.graph import StateGraph, END, START
from state.state import AgentState
from graph.nodes import Orchestrator_node, Agent_Insighter_Reporter_node, Agent_Data_Explorer_node


def create_workflow():
    workflow = StateGraph(AgentState)
    
    workflow.add_node(
        "Orchestrator",
        Orchestrator_node,
        description="Manages the overall workflow and delegates tasks to specialized agents.")
    workflow.add_node(
        "Agent_Insighter_Reporter",
        Agent_Insighter_Reporter_node,
        description="Generates data analysis reports and visualizations.")
    workflow.add_node(
        "Agent_Data_Explorer",
        Agent_Data_Explorer_node,
        description="Performs exploratory data analysis using provided tools.")
    
    workflow.add_edge(START, "Orchestrator")
    workflow.add_edge("Orchestrator", "Agent_Data_Explorer")
    workflow.add_edge("Agent_Data_Explorer", "Agent_Insighter_Reporter")
    workflow.add_edge("Agent_Insighter_Reporter", END)

    app = workflow.compile()

    return app

app = create_workflow()