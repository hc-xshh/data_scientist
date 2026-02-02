# 定位：AI生成(商务中心)
# 功能：面向企业招投标与培训场景的文档自动化生成工具，核心作用是基于预设模板和输入信息，快速生成各类标准化商业文档与培训材料，提升内容产出效率与规范性。

from langchain.agents import create_agent
from config import settings
from models.Deepseek_Models import call_deepseek_chat
from prompts import AIDocGenBusinessPrompt

agent = create_agent(
    model=call_deepseek_chat(),
    system_prompt=AIDocGenBusinessPrompt
)

