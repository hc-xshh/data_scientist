"""
全局配置管理模块（Pydantic v2 风格）
使用 pydantic-settings 从环境变量加载配置
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    """应用配置类"""

    # DeepSeek API 配置
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    # 模型参数
    deepseek_model_name: str = "deepseek-chat"
    deepseek_model_temperature: float = 0.7
    deepseek_model_max_tokens: int = 4096

    # 智谱 API 配置
    zhipuai_api_key: str
    zhipuai_base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    zhipuai_model: str = "glm-4.5v"

    # 模型参数
    zhipuai_model_temperature: float = 0.7
    zhipuai_model_max_tokens: int = 4096


    # 数据库配置
    db_host: str
    db_user: str
    db_password: str
    db_name: str
    db_port: int = 3306

    # LangSmith 配置（可选）
    langchain_tracing_v2: bool = False
    langchain_api_key: Optional[str] = None
    langchain_project: str = "data-analysis-agent"
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # 搜索工具 API Keys（可选）
    tavily_api_key: Optional[str] = None
    serpapi_api_key: Optional[str] = None

    # 应用配置
    max_iterations: int = 10
    debug: bool = False

    # === 新增：v2 风格配置 ===
    model_config = SettingsConfigDict(
        env_file=".env",           # 读取 .env 文件
        case_sensitive=False,      # 环境变量不区分大小写
        extra="ignore",            # 忽略额外字段
        validate_default=True,     # 验证默认值是否合法（可选增强安全性）
    )


# 全局配置实例
settings = Settings()


# 设置环境变量（用于 LangSmith 追踪）
if settings.langchain_tracing_v2 and settings.langchain_api_key:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint