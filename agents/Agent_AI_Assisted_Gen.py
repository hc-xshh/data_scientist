# 定位：AI 辅助生成模块
# 功能：基于项目场景的输入信息和标准化模板，自动产出各类项目相关文档与成果，以提升项目管理和交付的效率与规范性。

from langchain.agents import create_agent
from config import settings
from models.Deepseek_Models import call_deepseek_chat
from tools import generate_word_document, generate_pdf_document, generate_dashboard_html, quick_pdf_generate, generate_document, quick_word_generate
from prompts import AIAssistedPrompt


tools = [
    generate_word_document, generate_pdf_document, generate_dashboard_html, quick_pdf_generate, generate_document, quick_word_generate
]

agent = create_agent(
    model=call_deepseek_chat(),
    tools=tools,
    system_prompt=AIAssistedPrompt
)

