# 数据文件解析 Agent
# 解析和理解各种数据文件内容（Excel/CSV/JSON）

from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek
from prompts import DataParserPrompt
from tools import parse_data_file

tools = [
    parse_data_file,
]

model = ChatDeepSeek(model="deepseek-chat")

agent = create_agent(model=model, tools=tools, system_prompt=DataParserPrompt)