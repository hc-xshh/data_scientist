# 问答 Agent
# 智能问答

from langchain.agents import create_agent
from config import settings
from models.Deepseek_Models import call_deepseek_chat
from prompts import AIQWGrowthPrompt

agent = create_agent(
    model=call_deepseek_chat(),
    system_prompt=AIQWGrowthPrompt
)

