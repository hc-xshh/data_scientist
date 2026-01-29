# 报告生成与可视化 Agent
# 生成数据分析报告与可视化图表
# 关键工具（示例）：matplotlib, seaborn, plotly, reportlab

from tools import image_gen_tool
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek
from agents.Agent_HTML_Gen import agent as html_gen_agent
from prompts import InsighterReporterPrompt

@tool
def html_gen(request: str) -> str:
    """使用自然语言生成HTML页面。

    当用户想要创建或修改网页时使用此功能。处理HTML、CSS和JavaScript的生成。

    输入：用于HTML页面创建或修改的自然语言请求（
    例如，“为一家叫翻转的 AI 初创公司制作一个惊艳的、生产级的落地页面。风格要求：暗黑模式、发光渐变、毛玻璃特效。”）
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

agent = create_agent(model=model, tools=tools, system_prompt=InsighterReporterPrompt)