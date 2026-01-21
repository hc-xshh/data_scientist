from sqlalchemy import create_engine, inspect
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, List

# 1. 定义输入模型
class QueryDBTablesInput(BaseModel):
    db_uri: str = Field(
        ..., 
        description="数据库连接字符串 (例如: mysql+pymysql://user:password@localhost:3306/mydb)"
    )

# 2. 定义工具类
class QueryDBTablesTool(BaseTool):
    name: str = "query_database_tables"
    description: str = "用于查询数据库中存在哪些数据表。输入数据库连接信息，返回表名列表。"
    args_schema: Type[BaseModel] = QueryDBTablesInput

    def _run(self, db_uri: str) -> str:
        try:
            # --- 步骤 1: 创建引擎 ---
            engine = create_engine(db_uri, echo=False)
            
            # --- 步骤 2: 使用 Inspector 获取表名 ---
            # Inspector 是 SQLAlchemy 提供的用于查询数据库元数据的工具
            inspector = inspect(engine)
            
            # 获取所有表名
            tables: List[str] = inspector.get_table_names()
            
            if tables:
                table_list_str = ", ".join(tables)
                return f"数据库中包含以下表: [{table_list_str}]"
            else:
                return "数据库中没有找到任何表。"
                
        except Exception as e:
            return f"查询失败！无法连接数据库或发生错误: {str(e)}"

    async def _arun(self, db_uri: str) -> str:
        raise NotImplementedError("异步模式未实现。")

# --- 3. 使用示例 ---

if __name__ == "__main__":
    tool = QueryDBTablesTool()
    
    result = tool._run(
        db_uri="mysql+pymysql://root:123456@8.137.22.234:3306/lc_db"
    )
    
    print(result)