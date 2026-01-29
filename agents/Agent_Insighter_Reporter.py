# 报告生成与可视化 Agent
# 生成数据分析报告与可视化图表
# 关键工具（示例）：图像生成

from tools import image_gen_tool
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek
from prompts import InsighterReporterPrompt

tools = [
    image_gen_tool
]

model = ChatDeepSeek(model="deepseek-chat")

agent = create_agent(model=model, tools=tools, system_prompt=InsighterReporterPrompt)