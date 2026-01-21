import pandas as pd
from sqlalchemy import create_engine, text
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

# 1. 定义工具的输入参数模型
class ExcelToDBInput(BaseModel):
    file_path: str = Field(..., description="Excel 文件的本地路径或网络路径 (例如: ./data.xlsx)")
    table_name: str = Field(..., description="目标数据库表的名称")
    db_uri: str = Field(..., description="数据库连接字符串 (例如: mysql+pymysql://user:password@localhost:3306/mydb)")

# 2. 定义核心工具类
class ExcelToDBTool(BaseTool):
    name: str = "excel_to_database"
    description: str = "将 Excel 文件中的数据读取并存储到指定的 SQL 数据库中。"
    args_schema: Type[BaseModel] = ExcelToDBInput

    def _run(self, file_path: str, table_name: str, db_uri: str) -> str:
        try:
            # --- 步骤 1: 读取 Excel ---
            # header=0 表示将第一行作为列名
            df = pd.read_excel(file_path, header=0) 
            
            # --- 步骤 2: 连接数据库 ---
            # echo=True 会在控制台打印 SQL 语句，调试时很有用，上线时可设为 False
            engine = create_engine(db_uri, echo=False) 
            
            # --- 步骤 3: 写入数据库 ---
            # if_exists='append' 表示如果表存在，则追加数据
            # if_exists='replace' 表示如果表存在，则删除旧表并创建新表
            # index=False 表示不写入 pandas 的索引列
            df.to_sql(name=table_name, con=engine, if_exists='append', index=False)
            
            # --- 步骤 4: 验证写入 ---
            with engine.connect() as conn:
                # 使用 text() 包装原生 SQL
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = result.scalar()
            
            return f"成功！Excel 数据已成功导入到表 '{table_name}' 中。共导入 {row_count} 行数据。"
        
        except Exception as e:
            return f"失败！导入过程中发生错误: {str(e)}"

    async def _arun(self, file_path: str, table_name: str, db_uri: str) -> str:
        # 如果需要异步支持，可以在这里实现，或者直接抛出异常
        raise NotImplementedError("异步模式未实现。")

# --- 3. 使用示例 (模拟 Agent 调用) ---

if __name__ == "__main__":
    # 实例化工具
    excel_tool = ExcelToDBTool()
    
    # 模拟 Agent 调用该工具
    # 注意：实际 Agent 会自动解析参数，这里手动传参演示
    result = excel_tool._run(
        file_path="../input/temp.xlsx", # 替换为你的文件路径
        table_name="temp",   # 替换为你的表名
        db_uri="mysql+pymysql://root:123456@8.137.22.234:3306/lc_db" # 替换为你的数据库连接
    )
    
    print(result)