from typing import TypedDict, Annotated, Sequence, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from typing import Literal

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next: str   # Next agent
    task_completed: bool      # Flag indicating if the current task is completed
    pending_tasks: List[str]    # List of pending tasks for the agent
    current_task: str         # Current task being processed

class RouteResponse(BaseModel):
    next: Literal["Agent_Insighter_Reporter", "FINISH"]
    reasoning: str
    pending_tasks: List[str] = []