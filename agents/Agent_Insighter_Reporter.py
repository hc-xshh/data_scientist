# 报告生成与可视化 Agent
# 生成数据分析报告与可视化图表
# 关键工具（示例）：matplotlib, seaborn, plotly, reportlab

from tools import image_gen_tool
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek
from agents.Agent_HTML_Gen import agent as html_gen_agent

@tool
def html_gen(request: str) -> str:
    """Generate HTML pages using natural language.

    Use this when the user wants to create or modify web pages. Handles HTML, CSS, and JavaScript generation.

    Input: Natural language request for HTML page creation or modification (e.g., 'create a landing page with a hero section')
    """
    result = html_gen_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].text

tools = [
    image_gen_tool,
    html_gen
]

model = ChatDeepSeek(model="deepseek-chat")

prompt = """
You are an insightful reporter agent that generates data analysis reports and visualizations 
using tools like matplotlib, seaborn, plotly, and reportlab.
"""

agent = create_agent(model=model, tools=tools, system_prompt=prompt)