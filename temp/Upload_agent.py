import os
from dotenv import load_dotenv
from langchain_tavily import TavilySearch
# from langchain_deepseek import ChatDeepSeek
from langchain.agents import create_agent

# 加载环境变量
load_dotenv(override=True)

search_tool = TavilySearch(max_results=5, topic="general")

tools = [search_tool]

# 创建模型
# model = ChatDeepSeek(model="deepseek-chat")

from langchain_community.chat_models import ChatZhipuAI

model = ChatZhipuAI(
    model="glm-4.5v",  # 或 "glm-4"
    api_key="e0b34dda8da544a49baf7b42deaad63c.MHSryou4GDu0cxnC",
    temperature=0.6,
    streaming=False
)

prompt = "You are a helpful assistant that uses Tavily Search to answer user queries."
# 创建Agent
agent = create_agent(model=model, tools=tools, system_prompt=prompt)