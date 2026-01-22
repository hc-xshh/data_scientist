import os
import getpass
from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek

load_dotenv()

# 从环境变量中获取 DeepSeek API Key（如果未找到则抛出异常）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise EnvironmentError("未在 .env 文件中找到 DEEPSEEK_API_KEY 配置，请检查 .env 文件是否存在且配置正确")

def call_deepseek_chat(temperature: float = 0.7):
    """
    deepseek-chat模型的快捷调用方法，可配置temperature和max_tokens参数
    
    Args:
        temperature:温度，默认值0.7
        max_tokens:最大token数量，默认值2048
    """
    llm = ChatDeepSeek(
        model="deepseek-chat",
        temperature=temperature,
        api_key=DEEPSEEK_API_KEY
        )
    return llm


def call_deepseek_reasoner(temperature: float = 0.7):
    """
    deepseek-reasoner模型的快捷调用方法，可配置temperature和max_tokens参数
    
    Args:
        temperature:温度，默认值0.7
    """
    llm = ChatDeepSeek(
        model="deepseek-reasoner",
        temperature=temperature,
        api_key=DEEPSEEK_API_KEY
        )
    return llm