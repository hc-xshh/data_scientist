# 探索性分析 Agent
# 描述统计、分布分析、相关性分析
# 关键工具（示例）：seaborn, matplotlib, statsmodels

from tools import get_table_schema, get_tables_from_db, run_db_query
from langchain.agents import create_agent
from config import settings
from models.Deepseek_Models import call_deepseek_chat
from prompts import DataExplorerPrompts

tools = [
    get_tables_from_db,
    get_table_schema,
    run_db_query
]

agent = create_agent(
    model=call_deepseek_chat(),
    tools=tools,
    system_prompt=DataExplorerPrompts
)

