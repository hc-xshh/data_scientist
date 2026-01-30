import base64  # 新增：导入 base64 模块用于编码
import requests
from langchain.tools import tool


def local_image_to_base64(image_path: str) -> str:
    """
    将本地图片文件转换为 Base64 编码字符串（可直接用于图片 URL 拼接）
    
    Args:
        image_path: 本地图片的绝对路径或相对路径
    
    Returns:
        str: 图片的 Base64 编码字符串（不含前缀，纯编码内容）
    
    Raises:
        FileNotFoundError: 图片文件不存在时抛出
        RuntimeError: 读取文件或编码失败时抛出
    """
    try:
        # 1. 读取本地图片为原始字节流
        with open(image_path, "rb") as img_file:
            image_bytes = img_file.read()
        
        # 2. 将字节流编码为 Base64 字符串（解码为 utf-8 避免字节类型返回）
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        
        return image_base64
    except FileNotFoundError:
                raise FileNotFoundError(f"本地文件不存在：{image_path}")
    except PermissionError:
        raise PermissionError(f"没有权限访问本地文件：{image_path}")
    except Exception as e:
        raise Exception(f"处理本地文件 {image_path} 时发生未知错误：{str(e)}")


def web_image_to_base64(image_url: str, timeout: int = 15) -> str:
    """
    从网络 URL 下载图片并转换为 Base64 编码字符串
    
    Args:
        image_url: 图片的完整网络链接
        timeout: 超时时间（秒），默认 15 秒
    
    Returns:
        str: 图片的 Base64 编码字符串（不含前缀，纯编码内容）
    
    Raises:
        RuntimeError: 下载图片或编码失败时抛出
    """
    try:
        # 1. 下载网络图片为原始字节流
        response = requests.get(image_url, timeout=timeout, stream=True)
        response.raise_for_status()  # 检查 HTTP 请求是否成功
        image_bytes = response.content
        
        # 2. 将字节流编码为 Base64 字符串
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        
        return image_base64
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"下载网络图片失败：{str(e)}")
    except Exception as e:
        raise RuntimeError(f"网络图片转换 Base64 失败：{str(e)}")