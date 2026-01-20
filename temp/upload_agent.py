import os
from typing import TypedDict, Annotated, Sequence, Dict, Any, List, Optional, Literal
from pathlib import Path
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredFileLoader,
    CSVLoader,
    UnstructuredExcelLoader,
    UnstructuredMarkdownLoader,
)
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field
import json

# --- 环境配置 ---
# 确保设置以下环境变量:
# OPENAI_API_KEY 或 DEEPSEEK_API_KEY - 你的API密钥
# LANGCHAIN_API_KEY - 你的LangSmith API密钥（可选）
# LANGCHAIN_TRACING_V2=true - 启用LangSmith追踪（可选）
# LANGCHAIN_PROJECT="File Analysis Agent" - 项目名称（可选）

# 如果环境中没有设置，可以在这里设置
if os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "File Analysis Agent"

# --- 状态定义 ---
class AgentState(TypedDict):
    """智能体的状态模式"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    file_path: Optional[str]
    file_content: Optional[str]
    file_metadata: Optional[Dict[str, Any]]
    analysis_result: Optional[str]
    error: Optional[str]
    current_step: Optional[str]  # 用于追踪当前步骤

# --- 支持的文件类型 ---
SUPPORTED_EXTENSIONS = {
    ".txt": TextLoader,
    ".pdf": PyPDFLoader,
    ".doc": Docx2txtLoader,
    ".docx": Docx2txtLoader,
    ".csv": CSVLoader,
    ".xlsx": UnstructuredExcelLoader,
    ".xls": UnstructuredExcelLoader,
    ".md": UnstructuredMarkdownLoader,
}

# --- 工具定义 ---
@tool
def validate_file(file_path: str) -> Dict[str, Any]:
    """验证文件是否存在且可读"""
    try:
        path = Path(file_path)
        
        if not path.exists():
            return {
                "valid": False,
                "error": f"文件不存在: {file_path}"
            }
        
        if not path.is_file():
            return {
                "valid": False,
                "error": f"路径不是一个文件: {file_path}"
            }
        
        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return {
                "valid": False,
                "error": f"不支持的文件类型: {ext}。支持的类型: {', '.join(SUPPORTED_EXTENSIONS.keys())}"
            }
        
        # 获取文件元数据
        stat = path.stat()
        return {
            "valid": True,
            "file_name": path.name,
            "file_type": ext,
            "file_size": stat.st_size,
            "file_size_mb": round(stat.st_size / (1024 * 1024), 2)
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"验证文件时出错: {str(e)}"
        }

@tool
def load_file(file_path: str) -> Dict[str, Any]:
    """加载并读取文件内容"""
    try:
        path = Path(file_path)
        ext = path.suffix.lower()
        
        # 选择合适的加载器
        if ext in SUPPORTED_EXTENSIONS:
            loader_class = SUPPORTED_EXTENSIONS[ext]
            loader = loader_class(file_path)
        else:
            # 尝试使用通用加载器
            loader = UnstructuredFileLoader(file_path)
        
        documents = loader.load()
        content = "\n\n".join([doc.page_content for doc in documents])
        
        # 为了避免token过多，限制内容长度
        max_chars = 10000
        truncated = len(content) > max_chars
        if truncated:
            content_preview = content[:max_chars] + "\n\n... [内容已截断，仅显示前10000字符]"
        else:
            content_preview = content
        
        return {
            "success": True,
            "content": content_preview,
            "full_content": content,
            "truncated": truncated,
            "char_count": len(content),
            "page_count": len(documents)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# --- 节点函数定义 ---
def validate_input(state: AgentState, config: RunnableConfig) -> AgentState:
    """验证用户输入和文件"""
    print("🔍 正在验证文件...")
    
    if not state.get("file_path"):
        return {
            **state,
            "error": "没有提供文件路径，请指定要分析的文件",
            "current_step": "validation_failed"
        }
    
    # 验证文件
    validation_result = validate_file.invoke({"file_path": state["file_path"]})
    
    if not validation_result.get("valid"):
        return {
            **state,
            "error": validation_result.get("error"),
            "current_step": "validation_failed"
        }
    
    print(f"✅ 文件验证成功: {validation_result['file_name']} ({validation_result['file_size_mb']}MB)")
    
    return {
        **state,
        "file_metadata": validation_result,
        "current_step": "validated",
        "error": None
    }

def process_file(state: AgentState, config: RunnableConfig) -> AgentState:
    """处理上传的文件"""
    print("🔄 正在加载文件内容...")
    
    try:
        # 使用工具加载文件
        file_result = load_file.invoke({"file_path": state["file_path"]})
        
        if not file_result.get("success"):
            return {
                **state,
                "error": f"文件加载失败: {file_result.get('error', '未知错误')}",
                "current_step": "load_failed"
            }
        
        print(f"✅ 文件加载成功 - 字符数: {file_result.get('char_count')}, 页数: {file_result.get('page_count')}")
        if file_result.get("truncated"):
            print("⚠️ 内容过长，已截断用于分析")
        
        return {
            **state,
            "file_content": file_result["content"],
            "current_step": "loaded",
            "error": None
        }
    except Exception as e:
        return {
            **state,
            "error": f"处理文件时出错: {str(e)}",
            "current_step": "load_failed"
        }

def analyze_content(state: AgentState, config: RunnableConfig) -> AgentState:
    """使用LLM分析文件内容"""
    print("🧠 正在使用AI分析内容...")
    
    if not state.get("file_content"):
        return {
            **state,
            "error": "没有文件内容可供分析",
            "current_step": "analysis_failed"
        }
    
    try:
        # 初始化LLM - 优先使用DeepSeek（成本更低），如果没有配置则使用OpenAI
        if os.getenv("DEEPSEEK_API_KEY"):
            llm = ChatDeepSeek(model="deepseek-chat", temperature=0)
            print("📡 使用DeepSeek模型...")
        elif os.getenv("OPENAI_API_KEY"):
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            print("📡 使用OpenAI模型...")
        else:
            return {
                **state,
                "error": "未配置LLM API密钥，请设置DEEPSEEK_API_KEY或OPENAI_API_KEY环境变量",
                "current_step": "analysis_failed"
            }
        
        # 获取文件元数据
        file_name = state.get("file_metadata", {}).get("file_name", "未知文件")
        file_type = state.get("file_metadata", {}).get("file_type", "未知类型")
        
        # 创建系统提示
        system_prompt = """你是一个专业的文件分析助手。你的任务是分析用户上传的文件内容，并提供全面、结构化的分析报告。

请按照以下结构进行分析：

1. **文件概览**
   - 文件类型和格式
   - 整体结构和组织方式

2. **内容摘要**（150-200字）
   - 用简洁的语言总结文件的主要内容

3. **关键主题和要点**
   - 列出3-5个最重要的主题或要点
   - 每个要点用简短的段落说明

4. **深入分析**
   - 内容质量评估
   - 语言风格和语调
   - 目标受众识别
   - 任何特殊的格式或结构

5. **关键发现**
   - 重要数据、事实或论点
   - 值得注意的见解或观点

6. **建议和后续行动**（如适用）
   - 对内容的改进建议
   - 可能的应用场景

请用清晰、专业的中文撰写分析报告，使用Markdown格式使报告易于阅读。"""

        # 创建用户提示
        user_prompt = f"""请分析以下文件：

**文件名:** {file_name}
**文件类型:** {file_type}

**文件内容:**
```
{state["file_content"]}
```

请提供详细的分析报告。"""
        
        # 调用LLM进行分析
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        print("💭 正在生成分析报告...")
        response = llm.invoke(messages, config=config)
        
        print("✅ 内容分析成功")
        return {
            **state,
            "analysis_result": response.content,
            "current_step": "analyzed",
            "error": None
        }
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"❌ 分析出错: {str(e)}")
        return {
            **state,
            "error": f"分析内容时出错: {str(e)}",
            "current_step": "analysis_failed"
        }

def format_response(state: AgentState, config: RunnableConfig) -> AgentState:
    """格式化最终响应给用户"""
    print("📝 正在格式化最终响应...")
    
    if state.get("error"):
        response_content = f"""❌ **处理过程中出现错误**

**错误信息:** {state['error']}

**建议:**
- 请检查文件路径是否正确
- 确认文件格式是否支持（支持: {', '.join(SUPPORTED_EXTENSIONS.keys())}）
- 验证文件是否可以正常访问
"""
    elif state.get("analysis_result"):
        file_info = state.get("file_metadata", {})
        file_name = file_info.get("file_name", "未知")
        file_size = file_info.get("file_size_mb", "未知")
        
        response_content = f"""✅ **文件分析完成**

---

**文件信息:**
- 文件名: `{file_name}`
- 文件大小: {file_size}MB

---

{state['analysis_result']}

---

*分析由AI生成，仅供参考*
"""
    else:
        response_content = "⚠️ 未能生成分析结果，请重试"
    
    return {
        **state,
        "messages": [*state["messages"], AIMessage(content=response_content)]
    }

# --- 条件路由函数 ---
def should_continue(state: AgentState) -> Literal["process_file", "handle_error"]:
    """决定验证后的下一步"""
    if state.get("current_step") == "validation_failed":
        return "handle_error"
    return "process_file"

def after_load(state: AgentState) -> Literal["analyze_content", "handle_error"]:
    """决定加载后的下一步"""
    if state.get("current_step") == "load_failed":
        return "handle_error"
    return "analyze_content"

def after_analysis(state: AgentState) -> Literal["format_response", "handle_error"]:
    """决定分析后的下一步"""
    if state.get("current_step") == "analysis_failed":
        return "handle_error"
    return "format_response"

def handle_error(state: AgentState, config: RunnableConfig) -> AgentState:
    """处理错误情况"""
    print(f"⚠️ 错误处理节点: {state.get('error')}")
    # 错误已经在state中，直接返回
    return state

# --- 构建图 ---
def create_file_analysis_graph():
    """创建文件分析状态图"""
    print("🏗️ 构建文件分析工作流图...")
    
    workflow = StateGraph(AgentState)
    
    # 添加所有节点
    workflow.add_node("validate_input", validate_input)
    workflow.add_node("process_file", process_file)
    workflow.add_node("analyze_content", analyze_content)
    workflow.add_node("handle_error", handle_error)
    workflow.add_node("format_response", format_response)
    
    # 设置入口点
    workflow.add_edge(START, "validate_input")
    
    # 添加条件边
    workflow.add_conditional_edges(
        "validate_input",
        should_continue,
        {
            "process_file": "process_file",
            "handle_error": "handle_error"
        }
    )
    
    workflow.add_conditional_edges(
        "process_file",
        after_load,
        {
            "analyze_content": "analyze_content",
            "handle_error": "handle_error"
        }
    )
    
    workflow.add_conditional_edges(
        "analyze_content",
        after_analysis,
        {
            "format_response": "format_response",
            "handle_error": "handle_error"
        }
    )
    
    # 错误处理后也格式化响应
    workflow.add_edge("handle_error", "format_response")
    
    # 最终节点
    workflow.add_edge("format_response", END)
    
    # 编译图（添加内存以支持多轮对话）
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    print("✅ 工作流图构建完成")
    return app

# --- 主应用 ---
def main():
    """主函数 - 用于本地测试"""
    print("🚀 初始化文件分析智能体...")
    print("="*60)
    
    # 创建智能体
    app = create_file_analysis_graph()
    
    # 示例文件路径 - 请替换为实际文件路径
    # 你可以修改这里来测试不同的文件
    import sys
    
    if len(sys.argv) > 1:
        # 从命令行参数获取文件路径
        sample_file_path = sys.argv[1]
    else:
        # 默认示例路径 - 请修改为你的测试文件
        sample_file_path = r"D:\HAHA\项目\A公司\code\data_scientist\README.md"
    
    print(f"📄 准备分析文件: {sample_file_path}")
    print("="*60)
    
    # 初始状态
    initial_state = {
        "messages": [HumanMessage(content=f"请帮我分析这个文件: {sample_file_path}")],
        "file_path": sample_file_path,
        "file_content": None,
        "file_metadata": None,
        "analysis_result": None,
        "error": None,
        "current_step": "initial"
    }
    
    # 配置（用于LangSmith追踪和会话管理）
    config = {
        "configurable": {
            "thread_id": f"file-analysis-{hash(sample_file_path) % 10000}",
        },
        "metadata": {
            "user": "test-user",
            "file_path": sample_file_path,
            "timestamp": str(Path(sample_file_path).stat().st_mtime) if Path(sample_file_path).exists() else "unknown"
        }
    }
    
    # 执行图
    try:
        print("\n开始执行分析流程...\n")
        final_state = app.invoke(initial_state, config=config)
        
        # 打印最终结果
        print("\n" + "="*60)
        print("📊 分析结果:")
        print("="*60)
        
        # 获取最后一条AI消息
        for msg in reversed(final_state["messages"]):
            if isinstance(msg, AIMessage):
                print(msg.content)
                break
        
        print("\n" + "="*60)
        print("✅ 分析完成！")
        
        if os.getenv("LANGCHAIN_API_KEY"):
            print("🔍 你可以在 LangSmith (https://smith.langchain.com/) 中查看详细的执行追踪")
        else:
            print("💡 提示: 设置 LANGCHAIN_API_KEY 环境变量以启用 LangSmith 追踪")
        
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 执行过程中出错: {str(e)}")
        import traceback
        print("\n详细错误信息:")
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()

# --- 用于LangGraph Dev服务器 ---
def get_app():
    """
    返回应用实例，用于langgraph dev服务器
    
    使用方法:
    1. 在终端运行: langgraph dev
    2. 打开浏览器访问: http://localhost:8123
    3. 在LangGraph Studio中测试智能体
    """
    return create_file_analysis_graph()

# 导出图定义（可选，用于可视化）
graph = get_app()