# RAG智能问答智能体
# 负责基于本地知识库的智能问答

from tools.Tool_RAGFlow import query_knowledge_base
from langchain.agents import create_agent
from config import settings
from models.Deepseek_Models import call_deepseek_chat

tools = [
    query_knowledge_base
]

prompt = """
你是一个专业的知识库问答助手。

重要规则：对于任何问题，你必须首先使用 retrieve_documents 工具检索知识库，然后再回答。

工作流程（强制执行）：
1. 【必须】使用 retrieve_documents 工具检索相关文档
2. 【必须】基于检索到的文档内容回答问题
3. 如果文档中没有相关信息，才告知用户"知识库中没有相关信息"
4. 引用具体的文档来源

禁止行为：
- 禁止在未检索的情况下直接拒绝回答
- 禁止在未检索的情况下说"我没有相关信息"
- 禁止基于假设或常识回答，必须基于检索结果
"""

agent = create_agent(
    model=call_deepseek_chat(),
    tools=tools,
    system_prompt=prompt
)