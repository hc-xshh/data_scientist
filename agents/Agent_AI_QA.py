# 定位：AI问答
# 功能：面向企业内部员工的 AI 知识查询工具，核心作用是通过自然语言交互，快速响应员工对业务知识、制度流程、常见问题等内容的查询，提升内部信息获取效率

from langchain.agents import create_agent
from config import settings
from models.Deepseek_Models import call_deepseek_chat
from prompts import AIQAPrompt

agent = create_agent(
    model=call_deepseek_chat(),
    system_prompt=AIQAPrompt
)

