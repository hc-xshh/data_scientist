# 定位：AI审核合同
# 功能：面向企业合同场景的 AI 智能辅助工具，核心作用是基于输入的业务信息生成合同初稿，并对合同内容进行合规性、风险点审核，提升合同起草与审核的效率与准确性。

from langchain.agents import create_agent
from config import settings
from models.Deepseek_Models import call_deepseek_chat
from prompts import AIAssistedPrompt

agent = create_agent(
    model=call_deepseek_chat(),
    system_prompt=AIAssistedPrompt
)

