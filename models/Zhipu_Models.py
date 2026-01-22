import os
from dotenv import load_dotenv
from config import settings
def call_zhipu_chat(temperature: float = 0.7):
    """
    zhipu-chat模型的快捷调用方法，可配置temperature参数
    
    Args:
        temperature:温度，默认值0.7
    """
    from langchain_community.chat_models import ChatZhipuAI

    model = ChatZhipuAI(
        model=settings.zhipuai_model,  # 或 "glm-4"
        api_key=settings.zhipuai_api_key,
        temperature=settings.zhipuai_model_temperature,
        streaming=False
    )

    return model