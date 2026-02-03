# 文件内容解析 Agent
# 解析和理解各种文件内容

from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek
from prompts import FileAnalysisPrompt
from tools import parse_pdf_document, parse_word_document, parse_image_file

tools = [
    parse_pdf_document,
    parse_word_document,
    parse_image_file,
]

model = ChatDeepSeek(model="deepseek-chat")

agent = create_agent(model=model, tools=tools, system_prompt=FileAnalysisPrompt)