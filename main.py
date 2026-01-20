from langchain_deepseek import ChatDeepSeek
from tools.python_REPL import repl_tool
from langchain.agents import create_agent

model = ChatDeepSeek(model="deepseek-chat")

tools = [repl_tool]

prompts = """你是一个python编程专家,擅长使用Python解决各种问题,包括数据分析、可视化、自动化等。你可以调用内置的Python REPL工具来执行Python代码,并返回结果。"""

agent = create_agent(
    model,
    tools,
    system_prompt=prompts,
)

