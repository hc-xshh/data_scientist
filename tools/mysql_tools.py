from dotenv import load_dotenv
import os
from langchain.tools import tool
import pymysql
from pymysql.err import MySQLError

# 加载环境变量
load_dotenv()

db_config= {
            "host":os.environ.get("mysql_host","localhost"),
            "port":os.environ.get("mysql_port",3306),
            "user":os.environ.get("mysql_user","root"),
            "password":os.environ.get("mysql_pwd"),
            "database":os.environ.get("mysql_db","temp_base")
        }

# mysql_connection_url=(
#     f"mysql+pymysql://{db_config['user']}:{db_config['password']}@"
#     f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
# )

@tool(description="连接到 MySQL 数据库并执行建表 SQL 语句，一次只能执行一个SQL语句。query_sql必须传入,数据库连接信息可不提供，访问默认数据库")
def mysql_create_table(
    query_sql: str,
    host=db_config["host"],
    user=db_config["user"],
    password=db_config["password"],
    database=db_config["database"],
    port: int=db_config["port"]
):
    """
    连接到 MySQL 数据库并执行建表 SQL 语句。

    Args:
        query_sql (str): 用于创建表的 SQL 语句。
                         例如: "CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255));"
        host (str): MySQL 服务器地址。默认数据库的host，可不提供。
        user (str): 连接数据库的用户名。默认数据库的user，可不提供。
        password (str): 用户密码。默认数据库的password，可不提供。
        database (str): 要连接的数据库名。默认数据库的database，可不提供。
        port (int): MySQL 服务端口。默认为 3306。

    Returns:
        bool: 成功返回 True，失败返回 False。
    """
    connection = None
    try:
        # 建立数据库连接
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            charset='utf8mb4'  # 推荐使用 utf8mb4 支持完整的 UTF-8 字符
        )

        with connection.cursor() as cursor:
            # 执行 SQL 语句
            print(f"Executing SQL:\n{query_sql}")
            cursor.execute(query_sql)
        
        # 提交事务
        connection.commit()
        print("Table created successfully!")
        return True

    except MySQLError as e:
        # 捕获并打印 MySQL 相关错误
        print(f"A MySQL error occurred: {e}")
        return False
    except Exception as e:
        # 捕获其他可能的错误
        print(f"An unexpected error occurred: {e}")
        return False
    finally:
        # 确保连接被关闭
        if connection:
            connection.close()
            print("MySQL connection closed.")

