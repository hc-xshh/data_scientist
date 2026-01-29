# 报告生成与可视化 Agent
# 生成数据分析报告与可视化图表
# 关键工具（示例）：matplotlib, seaborn, plotly, reportlab

from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek
from prompts import HTMLGenPrompt

model = ChatDeepSeek(model="deepseek-chat")

agent = create_agent(model=model, system_prompt=HTMLGenPrompt)


