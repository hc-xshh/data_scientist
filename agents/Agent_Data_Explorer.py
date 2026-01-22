# 探索性分析 Agent
# 描述统计、分布分析、相关性分析
# 关键工具（示例）：seaborn, matplotlib, statsmodels

from tools import get_table_schema, get_tables_from_db, run_db_query
from langchain.agents import create_agent
from config import settings
from models.Deepseek_Models import call_deepseek_chat

tools = [
    get_tables_from_db,
    get_table_schema,
    run_db_query
]

prompt = """
你是一个数据分析专家，擅长使用Python进行数据探索性分析。
你可以使用提供的工具来查询数据库中的表结构和数据。
请根据用户的问题，选择合适的工具进行查询，并给出详细的分析结果和可视化建议。
"""

agent = create_agent(
    model=call_deepseek_chat(),
    tools=tools,
    system_prompt=prompt
)

