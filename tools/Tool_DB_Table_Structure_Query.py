from sqlalchemy import create_engine, inspect
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, List
from config import settings

# 1. 定义输入模型
class QueryDBSchemaInput(BaseModel):
    db_uri: str = Field(
        ..., 
        description="数据库连接字符串"
    )
    table_names: List[str] = Field(
        ..., 
        description="要查询结构的表名列表，例如 ['users', 'orders']"
    )

# 2. 定义工具类
class QueryDBSchemaTool(BaseTool):
    name: str = "query_table_schema"
    description: str = ("根据提供的表名列表，查询并返回这些数据库表的详细结构（字段名、数据类型等）。\n"
                       "输入必须包含数据库链接和一个表名数组。")
    args_schema: Type[BaseModel] = QueryDBSchemaInput

    def _run(self, db_uri: str, table_names: List[str]) -> str:
        try:
            # --- 步骤 1: 创建引擎和检查器 ---
            engine = create_engine(db_uri, echo=False)
            inspector = inspect(engine)
            
            all_tables_info = ""
            
            # --- 步骤 2: 遍历表名列表 ---
            for table_name in table_names:
                # 获取该表的列信息
                columns = inspector.get_columns(table_name)
                
                # 拼接表结构信息
                column_details = []
                for col in columns:
                    # 提取常用信息：字段名、类型、是否主键
                    col_info = f"  - {col['name']} ({col['type']}{' [PK]' if col.get('primary_key') else ''})"
                    column_details.append(col_info)
                
                all_tables_info += f"表名: {table_name}\n字段详情:\n" + "\n".join(column_details) + "\n\n"
            
            return all_tables_info
            
        except Exception as e:
            return f"查询表结构失败: {str(e)}"

    # async def _arun(self, db_uri: str, table_names: List[str]) -> str:
    #     raise NotImplementedError("异步模式未实现。")

# --- 3. 使用示例 ---
if __name__ == "__main__":
    tool = QueryDBSchemaTool()
    
    # 模拟查询 'users' 和 'orders' 这两张表的结构
    result = tool._run(
        db_uri=f"mysql+pymysql://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}",
        table_names=["全国黑名单列表", "案件查询列表", "零售户信息查询"] # 这里是你关心的表
    )
    
    print(result)