# 报告生成与可视化 Agent
# 生成数据分析报告与可视化图表
# 关键工具（示例）：matplotlib, seaborn, plotly, reportlab

from tools import image_gen_tool
from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek

tools = [
    image_gen_tool
]

model = ChatDeepSeek(model="deepseek-chat")

prompt = """
You are an insightful reporter agent that generates data analysis reports and visualizations 
using tools like matplotlib, seaborn, plotly, and reportlab.
"""

agent = create_agent(model=model, tools=tools, system_prompt=prompt)