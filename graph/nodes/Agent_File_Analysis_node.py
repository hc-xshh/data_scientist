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
            你是专业的文件内容解析与分析专家，擅长深度提取和理解各种类型文件的内容，包括文档、图像和数据文件。
            
            用户的问题：
            {chr(10).join(reversed(context_parts))}
            
            你可以使用以下工具：
            - parse_pdf_document: 解析PDF文档，提取文本、图像和表格内容，支持学术论文、商业报告等
            - parse_word_document: 解析Word文档(.docx)，提取文本、图像和表格，保留文档层次结构
            - parse_image_file: 解析图像文件，使用视觉模型分析内容、识别文字、理解图表，并提取EXIF元数据
            - parse_data_file: 解析结构化数据文件(Excel、CSV等)，提取数据内容和统计信息
            
            重要提示：
            - 所有工具都支持本地文件路径和HTTP/HTTPS URL
            - 对于PDF和Word，优先启用视觉模型分析图像(analyze_images=True)以获得更深入理解
            - 对于Excel文件，可通过sheet_name指定工作表，通过preview_rows控制预览行数
            - 上传文件URL格式: http://localhost:5000/files/文件名
            
            请根据文件类型选择合适的工具，完整提取内容后，提供：
            1. 文件内容的完整提取和结构化呈现
            2. 关键信息的识别、总结和分析
            3. 针对用户问题的专业洞察和建议
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