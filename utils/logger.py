"""
日志配置模块

提供统一的日志记录功能，支持：
- 控制台输出（带颜色）
- 文件输出（带日志轮转）
- 不同级别的日志记录
- 自定义日志格式
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime


# 定义日志颜色（ANSI颜色代码）
class LogColors:
    """终端日志颜色配置"""
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器（仅在控制台使用）"""
    
    # 不同日志级别对应的颜色
    COLORS = {
        'DEBUG': LogColors.CYAN,
        'INFO': LogColors.GREEN,
        'WARNING': LogColors.YELLOW,
        'ERROR': LogColors.RED,
        'CRITICAL': LogColors.RED + LogColors.BOLD
    }
    
    def format(self, record):
        """格式化日志记录，添加颜色"""
        # 获取对应级别的颜色
        color = self.COLORS.get(record.levelname, LogColors.WHITE)
        
        # 为日志级别添加颜色
        record.levelname = f"{color}{record.levelname}{LogColors.RESET}"
        
        # 为模块名添加颜色
        record.name = f"{LogColors.MAGENTA}{record.name}{LogColors.RESET}"
        
        return super().format(record)


def setup_logger(
    name: str = "data_scientist",
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_dir: str = "logs"
) -> logging.Logger:
    """
    配置并返回一个logger实例
    
    Args:
        name: logger名称
        level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_to_file: 是否输出到文件
        log_dir: 日志文件目录
        
    Returns:
        配置好的logger实例
    """
    # 创建logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 日志格式
    detailed_format = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "%(filename)s:%(lineno)d - %(funcName)s() - %(message)s"
    )
    simple_format = "%(asctime)s - %(levelname)s - %(message)s"
    
    # 时间格式
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 1. 控制台处理器（带颜色）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = ColoredFormatter(simple_format, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 2. 文件处理器（带日志轮转）
    if log_to_file:
        # 创建日志目录
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # 日志文件路径（按日期命名）
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = log_path / f"{name}_{today}.log"
        
        # 创建文件处理器（最大10MB，保留5个备份文件）
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(detailed_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # 阻止日志传播到root logger
    logger.propagate = False
    
    return logger


# 创建全局默认logger实例
logger = setup_logger(
    name="data_scientist",
    level=logging.INFO,
    log_to_file=True,
    log_dir="logs"
)


# 便捷函数
def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    获取指定名称的logger
    
    Args:
        name: logger名称
        level: 日志级别
        
    Returns:
        logger实例
    """
    return setup_logger(name=name, level=level)


def set_log_level(level: int):
    """
    设置全局日志级别
    
    Args:
        level: 日志级别（logging.DEBUG, logging.INFO等）
    """
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


# 示例用法（可以删除或注释掉）
if __name__ == "__main__":
    # 测试不同级别的日志
    logger.debug("这是一条调试信息")
    logger.info("这是一条普通信息")
    logger.warning("这是一条警告信息")
    logger.error("这是一条错误信息")
    logger.critical("这是一条严重错误信息")
    
    # 测试自定义logger
    custom_logger = get_logger("custom_module", level=logging.DEBUG)
    custom_logger.debug("自定义模块的调试信息")