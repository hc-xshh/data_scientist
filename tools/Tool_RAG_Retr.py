import os
import json
import requests
from typing import Dict, List, Optional, Union, Any, Tuple
from langchain_core.tools import tool
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 全局配置
RAGFLOW_API_URL = os.getenv('RAGFLOW_API_URL', 'http://8.137.22.234:81')
RAGFLOW_API_KEY = os.getenv('RAGFLOW_API_KEY', 'ragflow-WAOfF27-0M1U5WsV19OVMdrc75jYvG2ugRWiA9RJXXo')
DEFAULT_CHAT_ID = "a4ca90adfa7911f09725269aa1038e6c"


def _get_headers() -> Dict:
    """获取API请求头"""
    headers = {
        'Content-Type': 'application/json',
    }
    
    if RAGFLOW_API_KEY:
        headers['Authorization'] = f'Bearer {RAGFLOW_API_KEY}'
    
    return headers


def _make_ragflow_request(
    query: str,
    chat_id: str = DEFAULT_CHAT_ID,
    stream: bool = False,
    reference: bool = True,
    metadata_conditions: List[Dict] = None,
    logic: str = "and",
    model: str = "model"
) -> Dict:
    """
    向RAGFlow API发送请求
    
    Args:
        query: 查询文本
        chat_id: 聊天ID
        stream: 是否流式传输
        reference: 是否包含引用
        metadata_conditions: 元数据过滤条件
        logic: 逻辑操作符 (and/or)
        model: 模型名称
        
    Returns:
        API响应
    """
    try:
        endpoint = f"{RAGFLOW_API_URL}/api/v1/chats_openai/{chat_id}/chat/completions"
        
        # 构建请求数据
        data = {
            "model": model,
            "messages": [{"role": "user", "content": query}],
            "stream": stream,
        }
        
        # 添加额外参数
        extra_body = {"reference": reference}
        
        if metadata_conditions:
            extra_body["metadata_condition"] = {
                "logic": logic,
                "conditions": metadata_conditions
            }
        
        data["extra_body"] = extra_body
        
        logger.info(f"发送请求到: {endpoint}")
        logger.info(f"查询: {query[:100]}...")
        
        # 发送请求
        response = requests.post(
            endpoint, 
            headers=_get_headers(), 
            json=data,
            timeout=60
        )
        
        response.raise_for_status()
        
        if stream:
            # 处理流式响应
            return _handle_stream_response(response)
        else:
            return response.json()
            
    except requests.exceptions.ConnectionError as e:
        logger.error(f"连接RAGFlow服务失败: {e}")
        raise Exception(f"无法连接到RAGFlow服务: {str(e)}")
    except requests.exceptions.Timeout as e:
        logger.error(f"请求超时: {e}")
        raise Exception("请求超时，请稍后重试")
    except requests.exceptions.RequestException as e:
        logger.error(f"API请求失败: {e}")
        if hasattr(e, 'response') and e.response:
            error_detail = f"状态码: {e.response.status_code}"
            try:
                error_json = e.response.json()
                if 'message' in error_json:
                    error_detail += f", 错误信息: {error_json['message']}"
            except:
                error_detail += f", 响应: {e.response.text[:200]}"
        else:
            error_detail = str(e)
        raise Exception(f"请求失败: {error_detail}")
    except Exception as e:
        logger.error(f"未知错误: {e}")
        raise Exception(f"处理请求时出错: {str(e)}")


def _handle_stream_response(response) -> Dict:
    """
    处理流式响应
    
    Args:
        response: 响应对象
        
    Returns:
        合并后的响应数据
    """
    try:
        full_content = ""
        chunks = []
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    if data_str == '[DONE]':
                        break
                    
                    try:
                        chunk_data = json.loads(data_str)
                        chunks.append(chunk_data)
                        
                        if 'choices' in chunk_data and len(chunk_data['choices']) > 0:
                            choice = chunk_data['choices'][0]
                            if 'delta' in choice and 'content' in choice['delta']:
                                content = choice['delta']['content']
                                if content:
                                    full_content += content
                    except json.JSONDecodeError:
                        continue
        
        # 构建非流式格式的响应
        return {
            "choices": [{
                "message": {
                    "content": full_content,
                    "role": "assistant"
                },
                "finish_reason": "stop",
                "index": 0
            }],
            "stream_chunks": chunks,
            "full_content": full_content
        }
        
    except Exception as e:
        logger.error(f"处理流式响应失败: {e}")
        raise Exception(f"处理流式响应时出错: {str(e)}")


def _extract_content(response: Dict) -> str:
    """
    从响应中提取内容
    
    Args:
        response: API响应
        
    Returns:
        提取的内容
    """
    try:
        if "choices" in response and len(response["choices"]) > 0:
            if "message" in response["choices"][0]:
                return response["choices"][0]["message"]["content"]
            elif "delta" in response["choices"][0] and "content" in response["choices"][0]["delta"]:
                return response["choices"][0]["delta"]["content"]
        
        # 如果是自定义格式
        if "full_content" in response:
            return response["full_content"]
        
        return str(response)
        
    except Exception as e:
        logger.warning(f"提取内容失败: {e}")
        return "无法解析响应内容"


def _create_metadata_condition(
    name: str,
    comparison_operator: str,
    value: Any,
    field_type: str = "string"
) -> Dict:
    """
    创建元数据条件
    
    Args:
        name: 字段名
        comparison_operator: 比较操作符
        value: 值
        field_type: 字段类型
        
    Returns:
        元数据条件字典
    """
    valid_operators = ["is", "is_not", "contains", "not_contains", 
                      "starts_with", "ends_with", "greater_than", 
                      "less_than", "greater_equal", "less_equal", "in", "not_in"]
    
    if comparison_operator not in valid_operators:
        logger.warning(f"无效的操作符: {comparison_operator}, 使用默认值 'is'")
        comparison_operator = "is"
    
    return {
        "name": name,
        "comparison_operator": comparison_operator,
        "value": value,
        "field_type": field_type
    }


@tool
def retrieve_from_ragflow(
    query: str,
    chat_id: str = DEFAULT_CHAT_ID,
    include_reference: bool = True,
    stream: bool = False
) -> str:
    """
    从RAGFlow知识库检索内容
    
    参数:
        query: 查询文本
        chat_id: 聊天会话ID（默认使用配置的ID）
        include_reference: 是否在响应中包含引用信息
        stream: 是否使用流式传输（流式传输可能包含更多细节）
    
    返回:
        从知识库检索到的相关内容
    
    示例:
        retrieve_from_ragflow("哈哈的电话号码是多少？")
        
        retrieve_from_ragflow(
            query="项目进度报告",
            chat_id="custom_chat_id",
            include_reference=True
        )
    """
    try:
        logger.info(f"检索内容: {query}")
        
        response = _make_ragflow_request(
            query=query,
            chat_id=chat_id,
            stream=stream,
            reference=include_reference
        )
        
        content = _extract_content(response)
        
        logger.info(f"检索完成，内容长度: {len(content)}")
        return content
        
    except Exception as e:
        error_msg = f"❌ 检索失败: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
def retrieve_with_metadata_filter(
    query: str,
    metadata_conditions: List[Dict],
    logic: str = "and",
    chat_id: str = DEFAULT_CHAT_ID,
    include_reference: bool = True
) -> str:
    """
    使用元数据过滤从知识库检索内容
    
    参数:
        query: 查询文本
        metadata_conditions: 元数据过滤条件列表
        logic: 逻辑操作符 (and/or)
        chat_id: 聊天会话ID
        include_reference: 是否包含引用
    
    返回:
        过滤后的检索结果
    
    示例:
        retrieve_with_metadata_filter(
            query="技术文档",
            metadata_conditions=[
                {"name": "author", "comparison_operator": "is", "value": "张三"},
                {"name": "department", "comparison_operator": "contains", "value": "技术部"}
            ],
            logic="and"
        )
    """
    try:
        logger.info(f"使用元数据过滤检索: {query}")
        logger.info(f"过滤条件: {metadata_conditions}")
        
        response = _make_ragflow_request(
            query=query,
            chat_id=chat_id,
            stream=False,
            reference=include_reference,
            metadata_conditions=metadata_conditions,
            logic=logic
        )
        
        content = _extract_content(response)
        
        # 添加元数据过滤信息
        if include_reference:
            condition_info = " | ".join([
                f"{cond.get('name')} {cond.get('comparison_operator')} {cond.get('value')}"
                for cond in metadata_conditions
            ])
            content = f"📋 **元数据过滤**: {condition_info}\n\n{content}"
        
        logger.info(f"元数据过滤检索完成")
        return content
        
    except Exception as e:
        error_msg = f"❌ 元数据过滤检索失败: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
def retrieve_by_author(
    query: str,
    author_name: str,
    chat_id: str = DEFAULT_CHAT_ID,
    include_reference: bool = True
) -> str:
    """
    按作者从知识库检索内容
    
    参数:
        query: 查询文本
        author_name: 作者姓名
        chat_id: 聊天会话ID
        include_reference: 是否包含引用
    
    返回:
        指定作者的相关内容
    
    示例:
        retrieve_by_author("项目文档", "张三")
        
        retrieve_by_author("技术方案", "李四", include_reference=False)
    """
    try:
        metadata_conditions = [
            _create_metadata_condition("author", "is", author_name)
        ]
        
        return retrieve_with_metadata_filter.invoke({
            "query": query,
            "metadata_conditions": metadata_conditions,
            "logic": "and",
            "chat_id": chat_id,
            "include_reference": include_reference
        })
        
    except Exception as e:
        error_msg = f"❌ 按作者检索失败: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
def retrieve_by_department(
    query: str,
    department: str,
    chat_id: str = DEFAULT_CHAT_ID,
    include_reference: bool = True
) -> str:
    """
    按部门从知识库检索内容
    
    参数:
        query: 查询文本
        department: 部门名称
        chat_id: 聊天会话ID
        include_reference: 是否包含引用
    
    返回:
        指定部门的相关内容
    
    示例:
        retrieve_by_department("年度报告", "技术部")
        
        retrieve_by_department("市场分析", "市场部", include_reference=True)
    """
    try:
        metadata_conditions = [
            _create_metadata_condition("department", "contains", department)
        ]
        
        return retrieve_with_metadata_filter.invoke({
            "query": query,
            "metadata_conditions": metadata_conditions,
            "logic": "and",
            "chat_id": chat_id,
            "include_reference": include_reference
        })
        
    except Exception as e:
        error_msg = f"❌ 按部门检索失败: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
def retrieve_by_date_range(
    query: str,
    start_date: str = None,
    end_date: str = None,
    chat_id: str = DEFAULT_CHAT_ID,
    include_reference: bool = True
) -> str:
    """
    按日期范围从知识库检索内容
    
    参数:
        query: 查询文本
        start_date: 开始日期 (YYYY-MM-DD格式)
        end_date: 结束日期 (YYYY-MM-DD格式)
        chat_id: 聊天会话ID
        include_reference: 是否包含引用
    
    返回:
        指定日期范围内的相关内容
    
    示例:
        retrieve_by_date_range("会议纪要", "2024-01-01", "2024-12-31")
        
        retrieve_by_date_range("项目进展", start_date="2024-06-01")
    """
    try:
        metadata_conditions = []
        
        if start_date:
            metadata_conditions.append(
                _create_metadata_condition("date", "greater_equal", start_date, "date")
            )
        
        if end_date:
            metadata_conditions.append(
                _create_metadata_condition("date", "less_equal", end_date, "date")
            )
        
        if not metadata_conditions:
            # 如果没有日期条件，使用普通检索
            return retrieve_from_ragflow.invoke({
                "query": query,
                "chat_id": chat_id,
                "include_reference": include_reference
            })
        
        return retrieve_with_metadata_filter.invoke({
            "query": query,
            "metadata_conditions": metadata_conditions,
            "logic": "and",
            "chat_id": chat_id,
            "include_reference": include_reference
        })
        
    except Exception as e:
        error_msg = f"❌ 按日期范围检索失败: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
def retrieve_with_multiple_conditions(
    query: str,
    conditions: List[Dict],
    chat_id: str = DEFAULT_CHAT_ID,
    include_reference: bool = True
) -> str:
    """
    使用多个条件从知识库检索内容
    
    参数:
        query: 查询文本
        conditions: 条件列表，每个条件包含字段名、操作符和值
        chat_id: 聊天会话ID
        include_reference: 是否包含引用
    
    返回:
        符合多个条件的相关内容
    
    示例:
        retrieve_with_multiple_conditions(
            query="技术文档",
            conditions=[
                {"field": "type", "operator": "is", "value": "技术文档"},
                {"field": "status", "operator": "is", "value": "已发布"}
            ]
        )
    """
    try:
        metadata_conditions = []
        
        for condition in conditions:
            field = condition.get("field", "")
            operator = condition.get("operator", "is")
            value = condition.get("value", "")
            field_type = condition.get("field_type", "string")
            
            if field and value:
                metadata_conditions.append(
                    _create_metadata_condition(field, operator, value, field_type)
                )
        
        if not metadata_conditions:
            return "❌ 未提供有效的过滤条件"
        
        return retrieve_with_metadata_filter.invoke({
            "query": query,
            "metadata_conditions": metadata_conditions,
            "logic": "and",
            "chat_id": chat_id,
            "include_reference": include_reference
        })
        
    except Exception as e:
        error_msg = f"❌ 多条件检索失败: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
def compare_multiple_retrievals(
    queries: List[str],
    chat_id: str = DEFAULT_CHAT_ID,
    include_reference: bool = False
) -> str:
    """
    比较多个查询的检索结果
    
    参数:
        queries: 查询文本列表
        chat_id: 聊天会话ID
        include_reference: 是否包含引用
    
    返回:
        多个查询结果的比较分析
    
    示例:
        compare_multiple_retrievals(
            queries=["哈哈的电话", "哈哈的邮箱", "哈哈的职位"],
            include_reference=False
        )
    """
    try:
        if not queries or len(queries) < 2:
            return "❌ 请提供至少两个查询进行比较"
        
        results = []
        formatted = f"🔍 **多个查询结果比较**\n\n"
        formatted += f"**比较时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for i, query in enumerate(queries, 1):
            logger.info(f"执行查询 {i}/{len(queries)}: {query}")
            
            try:
                response = _make_ragflow_request(
                    query=query,
                    chat_id=chat_id,
                    stream=False,
                    reference=include_reference
                )
                
                content = _extract_content(response)
                results.append({
                    "query": query,
                    "content": content,
                    "length": len(content)
                })
                
                logger.info(f"查询 {i} 完成，内容长度: {len(content)}")
                
            except Exception as e:
                results.append({
                    "query": query,
                    "content": f"❌ 检索失败: {str(e)}",
                    "length": 0,
                    "error": str(e)
                })
                logger.error(f"查询 {i} 失败: {e}")
        
        # 生成比较报告
        formatted += "📊 **查询结果统计**\n\n"
        
        for i, result in enumerate(results, 1):
            formatted += f"**{i}. {result['query']}**\n"
            formatted += f"   • 内容长度: {result['length']} 字符\n"
            
            if 'error' in result:
                formatted += f"   • 状态: ❌ 失败 - {result['error'][:100]}...\n"
            else:
                formatted += f"   • 状态: ✅ 成功\n"
            
            # 显示内容摘要
            content_preview = result['content'][:150].replace('\n', ' ')
            if len(result['content']) > 150:
                content_preview += "..."
            
            formatted += f"   • 内容摘要: {content_preview}\n\n"
        
        # 添加分析
        formatted += "📈 **分析结果**\n\n"
        
        successful_results = [r for r in results if 'error' not in r]
        if successful_results:
            avg_length = sum(r['length'] for r in successful_results) / len(successful_results)
            max_result = max(successful_results, key=lambda x: x['length'])
            min_result = min(successful_results, key=lambda x: x['length'])
            
            formatted += f"• 成功检索: {len(successful_results)}/{len(queries)} 个查询\n"
            formatted += f"• 平均内容长度: {avg_length:.0f} 字符\n"
            formatted += f"• 最详细结果: {max_result['query']} ({max_result['length']} 字符)\n"
            formatted += f"• 最简洁结果: {min_result['query']} ({min_result['length']} 字符)\n\n"
        
        formatted += "💡 **建议**:\n"
        formatted += "• 内容长度较长的查询可能得到了更详细的回答\n"
        formatted += "• 可以调整查询方式以获得更精确的结果\n"
        
        return formatted
        
    except Exception as e:
        error_msg = f"❌ 比较检索结果失败: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
def check_ragflow_status() -> str:
    """
    检查RAGFlow服务状态
    
    返回:
        服务状态信息
    
    示例:
        check_ragflow_status()
    """
    try:
        test_query = "测试连接"
        
        start_time = time.time()
        response = _make_ragflow_request(
            query=test_query,
            stream=False,
            reference=False
        )
        response_time = time.time() - start_time
        
        content = _extract_content(response)
        
        status_info = f"✅ **RAGFlow服务状态正常**\n\n"
        status_info += f"**基本信息**:\n"
        status_info += f"• API地址: {RAGFLOW_API_URL}\n"
        status_info += f"• 聊天ID: {DEFAULT_CHAT_ID}\n"
        status_info += f"• 响应时间: {response_time:.2f}秒\n"
        status_info += f"• 测试查询: '{test_query}'\n\n"
        
        status_info += f"**测试响应**:\n"
        if len(content) > 200:
            status_info += f"{content[:200]}...\n"
        else:
            status_info += f"{content}\n"
        
        return status_info
        
    except Exception as e:
        return f"❌ **RAGFlow服务异常**\n\n错误信息: {str(e)}\n\n请检查:\n1. 服务是否启动\n2. API地址是否正确\n3. API密钥是否有效"


@tool
def quick_rag_search(
    query: str,
    chat_id: str = DEFAULT_CHAT_ID
) -> str:
    """
    快速从RAG知识库检索（简化版本）
    
    参数:
        query: 查询文本
        chat_id: 聊天会话ID
    
    返回:
        简洁的检索结果
    
    示例:
        quick_rag_search("哈哈的电话号码")
        
        quick_rag_search("公司地址", chat_id="another_chat_id")
    """
    try:
        logger.info(f"快速检索: {query}")
        
        response = _make_ragflow_request(
            query=query,
            chat_id=chat_id,
            stream=False,
            reference=True
        )
        
        content = _extract_content(response)
        
        # 简化输出
        if len(content) > 500:
            content = content[:500] + "...\n\n💡 提示：结果已被截断，如需完整信息请使用其他检索工具。"
        
        return content
        
    except Exception as e:
        return f"❌ 快速检索失败: {str(e)}"


# 工具列表
RAGFLOW_TOOLS = [
    retrieve_from_ragflow,
    retrieve_with_metadata_filter,
    retrieve_by_author,
    retrieve_by_department,
    retrieve_by_date_range,
    retrieve_with_multiple_conditions,
    compare_multiple_retrievals,
    check_ragflow_status,
    quick_rag_search
]


def test_all_tools():
    """测试所有工具"""
    print("🧪 测试RAGFlow工具集...")
    print("=" * 60)
    
    # 显示配置
    print(f"📋 当前配置:")
    print(f"  • API地址: {RAGFLOW_API_URL}")
    print(f"  • 聊天ID: {DEFAULT_CHAT_ID}")
    print(f"  • API密钥: {'已设置' if RAGFLOW_API_KEY else '未设置'}")
    
    # 测试状态检查
    print("\n1️⃣ 测试服务状态检查...")
    try:
        status = check_ragflow_status.invoke({})
        print(f"状态: {status[:200]}..." if len(status) > 200 else f"状态: {status}")
    except Exception as e:
        print(f"❌ 状态检查失败: {e}")
    
    # 测试基础检索
    print("\n2️⃣ 测试基础检索...")
    try:
        result = retrieve_from_ragflow.invoke({
            "query": "哈哈的电话号码是多少？",
            "include_reference": True
        })
        print(f"结果长度: {len(result)} 字符")
        if len(result) > 150:
            print(f"结果预览: {result[:150]}...")
    except Exception as e:
        print(f"❌ 基础检索失败: {e}")
    
    # 测试快速检索
    print("\n3️⃣ 测试快速检索...")
    try:
        result = quick_rag_search.invoke({
            "query": "哈哈的邮箱"
        })
        print(f"结果: {result[:200]}..." if len(result) > 200 else f"结果: {result}")
    except Exception as e:
        print(f"❌ 快速检索失败: {e}")
    
    # 测试按作者检索
    print("\n4️⃣ 测试按作者检索...")
    try:
        result = retrieve_by_author.invoke({
            "query": "文档",
            "author_name": "bob"
        })
        print(f"按作者检索结果长度: {len(result)} 字符")
    except Exception as e:
        print(f"❌ 按作者检索失败: {e}")
    
    # 测试多查询比较
    print("\n5️⃣ 测试多查询比较...")
    try:
        result = compare_multiple_retrievals.invoke({
            "queries": ["哈哈", "电话", "邮箱"],
            "include_reference": False
        })
        print(f"比较结果长度: {len(result)} 字符")
        if len(result) > 200:
            print(f"结果预览:\n{result[:200]}...")
    except Exception as e:
        print(f"❌ 多查询比较失败: {e}")
    
    print("\n✅ 测试完成")


def interactive_mode():
    """交互式模式"""
    print("\n🔄 交互式检索模式")
    print("=" * 40)
    print("可用命令:")
    print("  • ask <问题> - 提问")
    print("  • quick <问题> - 快速提问")
    print("  • author <问题> <作者名> - 按作者检索")
    print("  • dept <问题> <部门名> - 按部门检索")
    print("  • compare <问题1,问题2,...> - 比较多个查询")
    print("  • status - 检查服务状态")
    print("  • help - 显示帮助")
    print("  • quit - 退出")
    
    while True:
        try:
            user_input = input("\n> ").strip()
            
            if user_input.lower() in ['quit', 'exit', '退出']:
                print("再见！")
                break
                
            elif user_input.lower() == 'status':
                result = check_ragflow_status.invoke({})
                print(f"\n{result}")
                
            elif user_input.lower() == 'help':
                print("\n帮助:")
                print("  1. 直接提问: 'ask 哈哈的电话号码是多少？'")
                print("  2. 快速提问: 'quick 公司地址'")
                print("  3. 按作者检索: 'author 文档 张三'")
                print("  4. 按部门检索: 'dept 报告 技术部'")
                print("  5. 比较查询: 'compare 哈哈的电话,哈哈的邮箱,哈哈的职位'")
                print("  6. 检查状态: 'status'")
                print("  7. 退出: 'quit'")
                
            elif user_input.lower().startswith('ask '):
                question = user_input[4:].strip()
                if question:
                    print(f"\n提问: {question}")
                    result = retrieve_from_ragflow.invoke({
                        "query": question,
                        "include_reference": True
                    })
                    print(f"回答:\n{result}")
                else:
                    print("❌ 问题不能为空")
                    
            elif user_input.lower().startswith('quick '):
                question = user_input[6:].strip()
                if question:
                    print(f"\n快速提问: {question}")
                    result = quick_rag_search.invoke({"query": question})
                    print(f"回答:\n{result}")
                else:
                    print("❌ 问题不能为空")
                    
            elif user_input.lower().startswith('author '):
                parts = user_input[7:].strip().split(' ', 1)
                if len(parts) == 2:
                    question, author = parts
                    print(f"\n按作者检索: {question} (作者: {author})")
                    result = retrieve_by_author.invoke({
                        "query": question,
                        "author_name": author
                    })
                    print(f"回答:\n{result}")
                else:
                    print("❌ 格式错误，正确格式: author <问题> <作者名>")
                    
            elif user_input.lower().startswith('dept '):
                parts = user_input[5:].strip().split(' ', 1)
                if len(parts) == 2:
                    question, dept = parts
                    print(f"\n按部门检索: {question} (部门: {dept})")
                    result = retrieve_by_department.invoke({
                        "query": question,
                        "department": dept
                    })
                    print(f"回答:\n{result}")
                else:
                    print("❌ 格式错误，正确格式: dept <问题> <部门名>")
                    
            elif user_input.lower().startswith('compare '):
                queries_str = user_input[8:].strip()
                if queries_str:
                    queries = [q.strip() for q in queries_str.split(',') if q.strip()]
                    if len(queries) >= 2:
                        print(f"\n比较查询: {', '.join(queries)}")
                        result = compare_multiple_retrievals.invoke({
                            "queries": queries,
                            "include_reference": False
                        })
                        print(f"比较结果:\n{result}")
                    else:
                        print("❌ 至少需要两个查询进行比较")
                else:
                    print("❌ 请提供要比较的查询，用逗号分隔")
                    
            elif user_input:
                # 默认作为问题处理
                print(f"\n提问: {user_input}")
                result = quick_rag_search.invoke({"query": user_input})
                print(f"回答:\n{result}")
                
        except KeyboardInterrupt:
            print("\n\n程序被中断")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("🔍 RAGFlow知识库检索工具集")
    print("=" * 60)
    
    print("\n📚 可用工具:")
    for i, tool_func in enumerate(RAGFLOW_TOOLS, 1):
        print(f"{i}. {tool_func.name} - {tool_func.description.split('.')[0]}")
    
    print("\n💡 快速开始:")
    print("  1. 运行测试: python script.py test")
    print("  2. 交互模式: python script.py interactive")
    print("  3. 直接使用: python script.py")
    
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            test_all_tools()
        elif sys.argv[1] == 'interactive':
            interactive_mode()
        else:
            print(f"未知参数: {sys.argv[1]}")
    else:
        # 运行测试然后进入交互模式
        test_all_tools()
        interactive_mode()


if __name__ == "__main__":
    main()