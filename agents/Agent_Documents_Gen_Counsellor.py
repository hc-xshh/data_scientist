# AI文档生成 Agent
# 根据输入内容生成《调研提纲》、《诊断访谈纪要》、《诊断调研报告》、《蓝图规划》、《项目实施进度》
# 《课程纲要》、《课件》、《实践案例》、《产品概念文档》、《宣讲文档》、《会议纪要》、《产品价格手册》、《售前方案》、《实施版解决方案》

from langchain.agents import create_agent
from config import settings
from models.Deepseek_Models import call_deepseek_chat
from prompts import DocumentsGenCounsellorPrompt

agent = create_agent(
    model=call_deepseek_chat(),
    system_prompt=DocumentsGenCounsellorPrompt
)

