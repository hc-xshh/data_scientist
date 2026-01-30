from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek
from tools import generate_dashboard_html, generate_simple_chart_html
from prompts import HTMLGenPrompt

tools = [
    generate_dashboard_html,
    generate_simple_chart_html
]

model = ChatDeepSeek(model="deepseek-chat")

agent = create_agent(model=model, tools=tools, system_prompt=HTMLGenPrompt)