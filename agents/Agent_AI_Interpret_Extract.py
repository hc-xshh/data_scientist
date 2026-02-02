# 定位：AI 辅助解读与要点提取模块
# 功能：解析咨询思路文档、整合业务需求输出解决方案、细化生成项目实施计划表。

from langchain.agents import create_agent
from config import settings
from models.Deepseek_Models import call_deepseek_chat
from prompts import AIInterpretExtractPrompt

agent = create_agent(
    model=call_deepseek_chat(),
    system_prompt=AIInterpretExtractPrompt
)

