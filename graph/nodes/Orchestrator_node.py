from state.state import AgentState, RouteResponse
from langchain_core.messages import HumanMessage, AIMessage
from langchain_deepseek import ChatDeepSeek
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