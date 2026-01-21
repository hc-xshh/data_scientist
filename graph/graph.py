from langgraph.graph import StateGraph, END, START
from langchain_core.messages import HumanMessage, AIMessage
from langchain_deepseek import ChatDeepSeek
from agents import Agent_Insighter_Reporter
from state.state import AgentState, RouteResponse
def Orchestrator_node(state: AgentState) -> AgentState:
    # Orchestrator logic to manage workflow
    messages = state.get("messages", [])
    pending_tasks = state.get("pending_tasks", [])

    if pending_tasks:
        next_task = pending_tasks[0]
        remaining_tasks = pending_tasks[1:]
        return {
            "next": next_task,
            "pending_tasks": remaining_tasks,
            "current_task": next_task
        }
    
    last_msg = messages[-1] if messages else None

    if last_msg and isinstance(last_msg, AIMessage) and hasattr(last_msg, "name"):
        if last_msg.name in ["Agent_Insighter_Reporter"]:
            content = str(last_msg.content)
            has_no_tool_calls = not getattr(last_msg, "tool_calls", None)

            if has_no_tool_calls and len(content) > 50 and not pending_tasks:
                return {
                    "next": "FINISH",
                    "task_completed": True
                }
    
    prompt = """
    You are an orchestrator agent that manages the workflow and delegates tasks to specialized agents.
    """
    model = ChatDeepSeek(model="deepseek-chat")
    structured_llm =  model.with_structured_output(RouteResponse)

    messages_for_llm = [{"role": "system", "content": prompt}]

    for msg in messages:
        if isinstance(msg, HumanMessage):
            messages_for_llm.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            messages_for_llm.append({"role": "assistant", "content": msg.content})

    response = structured_llm.invoke(messages_for_llm)

    return {
        "next": response.next,
        "pending_tasks": response.pending_tasks,
        "current_task": response.next,
        "messages": [AIMessage(content=f"[调度决策] {response.reasoning}")]
    }


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
    
    workflow.add_edge(START, "Orchestrator")
    workflow.add_edge("Orchestrator", "Agent_Insighter_Reporter")
    workflow.add_edge("Agent_Insighter_Reporter", END)

    app = workflow.compile()

    return app

app = create_workflow()