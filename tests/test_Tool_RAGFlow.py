# tests/test_Tool_RAGFlow.py
from tools.Tool_RAGFlow import query_knowledge_base_tool, query_ragflow_raw


def test_query_knowledge_base_returns_answer():
    """测试调用 RAGFlow 能返回有效答案"""
    answer = query_ragflow_raw("什么是RAG？")

    assert isinstance(answer, str)
    assert len(answer.strip()) > 0, "回答不应为空"
    assert "[HTTP 4" not in answer, "疑似请求失败"
    assert "[HTTP 5" not in answer, "服务器内部错误"
    assert "【异常】" not in answer, "代码抛出异常"
    assert "未找到相关答案" not in answer.lower(), "虽然无异常但无结果"


def test_query_with_empty_question():
    """测试空问题是否处理得当"""
    answer = query_ragflow_raw("")
    assert isinstance(answer, str)
    # 应该返回错误提示而不是崩溃
    assert "不能为空" in answer or "长度" in answer or "无效" in answer


def test_tool_invoke_structure():
    """测试 Tool 是否正确封装"""
    result = query_knowledge_base_tool.invoke({"question": "测试问题"})
    assert isinstance(result, str)