import os
import getpass
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.chat_models.tongyi import ChatTongyi

load_dotenv()

# 从环境变量中获取 DeepSeek API Key（如果未找到则抛出异常）
QWQ_API_KEY = os.getenv("QWEN_API_KEY")
if not QWQ_API_KEY:
    raise EnvironmentError("未在 .env 文件中找到 QWQ_API_KEY 配置，请检查 .env 文件是否存在且配置正确")

def call_qwq3_vl_plus(temperature: float = 0.7,
    max_tokens: int = 9000):
    """
    qwq3_vl_plus模型的快捷调用方法，可配置temperature和max_tokens参数
    
    Args:
        temperature:温度，默认值0.7
        max_tokens:最大token数量，默认值9000
    """
    vllm = ChatOpenAI(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen3-vl-plus",  # 此处以qwen-plus为例，您可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        # other params...
        max_completion_tokens=max_tokens,
        api_key=QWQ_API_KEY
    )
    
    return vllm


def call_qwq3_vl_flash(temperature: float = 0.7,
    max_tokens: int = 9000):
    """
    qwq3_vl_flash模型的快捷调用方法，可配置temperature和max_tokens参数
    
    Args:
        temperature:温度，默认值0.7
        max_tokens:最大token数量，默认值9000
    """
    
    vllm = ChatOpenAI(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen3-vl-flash",  # 此处以qwen-plus为例，您可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        # other params...
        max_completion_tokens=max_tokens,
        api_key=QWQ_API_KEY
    )
    return vllm
