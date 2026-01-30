# 文件内容解析 Agent
# 解析和理解各种文件内容

from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek
from prompts import FileAnalysisPrompt
from tools.Tool_File_Read import analyze_file

tools = [analyze_file]

model = ChatDeepSeek(model="deepseek-chat")

agent = create_agent(model=model, tools=tools, system_prompt=FileAnalysisPrompt)