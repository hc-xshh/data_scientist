from state.state import AgentState
from langchain_core.messages import HumanMessage, AIMessage
from agents import Agent_File_Analysis

def Agent_File_Analysis_node(state: AgentState) -> AgentState:
    # File Analysis Agent logic

    agent = Agent_File_Analysis

    messages = state["messages"]

    context_parts = []
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) and hasattr(msg, "name"):
            if msg.name == "Orchestrator":
                context_parts.append(f"Orchestrator said: {msg.content}")
    
    if context_parts:
        context_msg = HumanMessage(
            content=f"""
            你是一个文件内容解析与分析专家，擅长深度提取和理解PDF文档、Word文档和图像文件。
            
            用户的问题：
            {chr(10).join(reversed(context_parts))}
            
            你可以使用以下工具：
            - parse_pdf_document: 解析PDF文档，提取文本、图像和表格内容
            - parse_word_document: 解析Word文档，提取文本、图像和表格，保留结构层次
            - parse_image_file: 解析图像文件，使用视觉模型分析内容并提取元数据
            
            所有工具都支持本地路径和HTTP/HTTPS URL。
            根据文件类型选择合适的工具，启用视觉模型分析以获得更深入的理解。
            
            基于提取的内容，提供：
            1. 文件内容的完整提取和结构化呈现
            2. 关键信息的识别和总结
            3. 针对用户问题的专业分析和洞察
            """
        )
        messages = list(messages) + [context_msg]

    result = agent.invoke({"messages": messages})

    if isinstance(result, dict) and "messages" in result:
        messages = result["messages"]
        if messages and isinstance(messages[-1], AIMessage):
            messages[-1].name = "Agent_File_Analysis"
        return {"messages": messages}
    else:
        msg = AIMessage(content=str(result), name="Agent_File_Analysis")
        return {"messages": [msg]}