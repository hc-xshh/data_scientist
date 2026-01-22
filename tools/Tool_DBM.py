import os
from config import settings
from pydantic import BaseModel, Field
from langchain_core.tools import tool


class DB_Schema(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str

@tool(args_schema=DB_Schema)
def get_tables_from_db(host: str, port: int, user: str, password: str, database: str) -> str:
    """
    获取指定数据库中的所有表名。
    """
    from sqlalchemy import create_engine, inspect
    try:
        db_uri = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        engine = create_engine(db_uri, echo=False)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if tables:
            return f"数据库中包含以下表: {', '.join(tables)}"
        else:
            return "数据库中没有找到任何表。"
    except Exception as e:
        return f"查询失败！无法连接数据库或发生错误: {str(e)}"
    


class DB_Schema_Table_Query(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str
    table_name: str

@tool(args_schema=DB_Schema_Table_Query)
def get_table_schema(host: str, port: int, user: str, password: str, database: str, table_name: str) -> str:
    """
    获取指定数据库表的结构信息。
    """
    from sqlalchemy import create_engine, inspect
    try:
        db_uri = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        engine = create_engine(db_uri, echo=False)
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        if columns:
            schema_info = f"表 '{table_name}' 的结构信息:\n"
            for col in columns:
                schema_info += f"- 列名: {col['name']}, 类型: {col['type']}, 可否为空: {col['nullable']}, 默认值: {col['default']}\n"
            return schema_info
        else:
            return f"表 '{table_name}' 不存在或没有找到任何列。"
    except Exception as e:
        return f"查询失败！无法连接数据库或发生错误: {str(e)}"
    

DB_Data_Query_description = """
当用户需要进行数据库查询工作时，请调用该函数。
该函数用于在指定MySQL服务器上运行一段SQL代码，完成数据查询相关工作，
并且当前函数是使用pymsql连接MySQL数据库。
本函数只负责运行SQL代码并进行数据查询，若要进行数据提取，则使用另一个extract_data函数。
"""

class DB_Data_Query(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str
    query: str = Field(description=DB_Data_Query_description)

@tool(args_schema=DB_Data_Query)
def run_db_query(host: str, port: int, user: str, password: str, database: str, query: str) -> str:
    """
    在指定的MySQL数据库上运行一段SQL查询代码，并返回查询结果。
    """
    import pymysql
    try:
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchall()
                if result:
                    return f"查询结果: {result}"
                else:
                    return "查询成功，但没有返回任何结果。"
    except Exception as e:
        return f"查询失败！无法连接数据库或发生错误: {str(e)}"
    
