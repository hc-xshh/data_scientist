import os
from dotenv import load_dotenv
import pymysql
from sqlalchemy import create_engine
from langchain_deepseek.chat_models import ChatDeepSeek
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

load_dotenv(override=True)

host = os.getenv('DB_HOST')
user = os.getenv('DB_USER')
mysql_pw = os.getenv('DB_PASSWORD')
db = os.getenv('DB_NAME')
port = os.getenv('DB_PORT')

# 创建 SQLAlchemy 引擎
engine = create_engine(
    f'mysql+pymysql://{user}:{mysql_pw}@{host}:{port}/{db}?charset=utf8'
)

sql_database = SQLDatabase(engine)

model = ChatDeepSeek(model="deepseek-chat")

toolkit = SQLDatabaseToolkit(db=sql_database, llm=model)
tools = toolkit.get_tools()

for tool in tools:
    print(f"{tool.name}: {tool.description}")

system_prompt = """
You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run,
then look at the results of the query and return the answer. Unless the user
specifies a specific number of examples they wish to obtain, always limit your
query to at most {top_k} results.

You can order the results by a relevant column to return the most interesting
examples in the database. Never query for all the columns from a specific table,
only ask for the relevant columns given the question.

You MUST double check your query before executing it. If you get an error while
executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
database.

To start you should ALWAYS look at the tables in the database to see what you
can query. Do NOT skip this step.

Then you should query the schema of the most relevant tables.
""".format(
    dialect=sql_database.dialect,
    top_k=5,
)

agent = create_agent(
    model,
    tools,
    system_prompt=system_prompt,
)


# question = "黑名单中姓刘的有几个？"

# for step in agent.stream(
#     {"messages": [{"role": "user", "content": question}]},
#     stream_mode="values",
# ):
#     step["messages"][-1].pretty_print()
    




