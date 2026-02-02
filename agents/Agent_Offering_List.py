# 报价表生成 Agent
# 销售将需求给到AI后，AI根据模板自动输出《报价表》PDF版

from langchain.agents import create_agent
from config import settings
from models.Deepseek_Models import call_deepseek_chat
from prompts import OfferingPrompt

agent = create_agent(
    model=call_deepseek_chat(),
    system_prompt=OfferingPrompt
)

