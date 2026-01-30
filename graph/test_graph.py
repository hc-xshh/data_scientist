from langgraph.graph import MessagesState,StateGraph,START,END
from src.custom_tools.format_table_head import format_table_head
from src.models.deepseek_models import call_deepseek_chat
from langchain.agents import create_agent
from langchain.messages import HumanMessage,AIMessage,ToolMessage
from src.custom_tools.mysql_tools import mysql_create_table

class ExtendedMessagesState(MessagesState):
    images: list[dict]
    files: list[dict]

def write_file(state:ExtendedMessagesState):
    # print("上传的图片：",state["images"]),
    # print("上传的文件：",state["files"])
    with open("messages.txt","w",encoding="utf-8") as file:
        file.write(str(state))



def agent_call(state: ExtendedMessagesState):
    llm = call_deepseek_chat()
    agent = create_agent(
        model=llm,
        tools=[format_table_head,mysql_create_table],
        system_prompt="你是一个帮助用户解析图片和文件的助手，你可以调用工具来处理表格文件。用户可能会上传文件，你需要根据文件信息决定是否调用工具进行处理。" \
        "如果用户提供了图片并希望你从图片里解析表结构，你可以先调用format_table_head工具解析，不要直接让用户补充信息、这是一个极其错误的行为，如果无法解析出来表结构再让用户提供表信息" \
        "format_table_head：只需要提供图片的链接，和少量的信息就可以开始解析表结构信息" \
        "mysql_create_table：是一个操作MySQL数据库创建表的工具，需要提供建表语句(建表语句应当与解析出来的表结构完全一致，不能擅自添加或减少字段，用户特别强调除外)。数据库连接信息可不提供，使用系统默认的数据库"
    )
    print("初始消息：",state["messages"])
    # 创建一个内部使用的消息副本，不影响前端显示
    internal_messages = []
    for msg in state["messages"]:
        if hasattr(msg, 'content') and isinstance(msg.content, list):
            # 重构内容，将文件和图片转换为文本描述
            text_parts = []
            for item in msg.content:
                if isinstance(item, dict):
                    if item.get("type") == "file":
                        # 将文件信息转换为文本描述
                        filename = item.get("metadata", {}).get("filename", "unknown")
                        size = item.get("metadata", {}).get("size", "unknown")
                        mime_type = item.get("mime_type", "unknown")
                        url = item.get("url", "")
                        
                        file_description = f"[文件: {filename}, 类型: {mime_type}, 大小: {size} bytes, URL: {url}]"
                        text_parts.append({"type": "text", "text": file_description})
                        
                    elif item.get("type") == "image":
                        # 将图片信息转换为文本描述
                        url = item.get("url", "")
                        image_description = f"[图片: 已上传图片, URL: {url}]"
                        text_parts.append({"type": "text", "text": image_description})
                    else:
                        # 保持其他类型的内容不变
                        text_parts.append(item)
                else:
                    # 如果不是字典，保持原样
                    text_parts.append(item)
            
            # 创建内部消息用于LLM处理
            internal_msg = HumanMessage(
                content=text_parts,
                additional_kwargs=getattr(msg, 'additional_kwargs', {}),
                response_metadata=getattr(msg, 'response_metadata', {}),
                id=getattr(msg, 'id', None)
            )
            internal_messages.append(internal_msg)
        else:
            # 如果消息内容不是列表，直接添加
            internal_messages.append(msg)
    
    # 使用重构后的内部消息调用代理
    result = agent.invoke({"messages": internal_messages})
    # print("agent返回消息：",result)
    # 处理返回的消息，只保留非原始内部消息
    final_messages = []
    
    # 检查结果中的消息
    if 'messages' in result:
        for msg in result['messages']:
            # 如果是AI消息或Tool消息，转换为所需格式
            if isinstance(msg, (AIMessage, ToolMessage)):
                # 将消息转换为字典格式
                # message_dict = {
                #     "role": "assistant" if isinstance(msg, AIMessage) else "tool",
                #     "content": str(msg.content)
                # }
                final_messages.append(msg)
    
    
    # 返回转换后的消息
    # print("处理之后的消息：",final_messages)
    return {"messages": final_messages}
    # 正确返回格式化的状态，只添加新消息
    # return {"messages": [result]}

def message_format(state: ExtendedMessagesState):
    # 获取现有的 images 和 files 列表
    existing_images = state.get("images", [])
    existing_files = state.get("files", [])
    
    # 创建已存在的URL集合用于快速查找
    existing_image_urls = {img.get("url") for img in existing_images if "url" in img}
    existing_file_urls = {file.get("url") for file in existing_files if "url" in file}
    
    for mes in state["messages"]:
        if hasattr(mes, 'content') and isinstance(mes.content, list):
            for m in mes.content:
                if isinstance(m, dict):
                    if m.get("type") == "file":
                        file_url = m.get("url")
                        # 校验URL是否存在且不在现有文件列表中
                        if file_url is not None and file_url not in existing_file_urls:
                            # 添加消息ID到文件数据中
                            m_with_message_id = m.copy()
                            m_with_message_id['message_id'] = getattr(mes, 'id', None)
                            existing_files.append(m_with_message_id)
                            existing_file_urls.add(file_url)  # 更新URL集合
                            
                    elif m.get("type") == "image":
                        image_url = m.get("url")
                        # 校验URL是否存在且不在现有图片列表中
                        if image_url is not None and image_url not in existing_image_urls:
                            # 添加消息ID到图片数据中
                            m_with_message_id = m.copy()
                            m_with_message_id['message_id'] = getattr(mes, 'id', None)
                            existing_images.append(m_with_message_id)
                            existing_image_urls.add(image_url)  # 更新URL集合
    
    # 返回更新后的状态，不修改原始消息
    return {
        "images": existing_images,
        "files": existing_files
    }

def return_AImessage(state:ExtendedMessagesState):
    new_mes=AIMessage(content="[下载用户手册](http://localhost:5000/files/fd73d82bb1a7454cbab92847898df474.xlsx)", additional_kwargs={}, response_metadata={'finish_reason': 'tool_calls', 'model_name': 'deepseek-chat', 'system_fingerprint': 'fp_eaab8d114b_prod0820_fp8_kvcache', 'model_provider': 'deepseek'}, id='lc_run--019bf8d6-bcb5-7e43-96fa-88bfcc054342', tool_calls=[{'name': 'format_table_head', 'args': {'table_desciption': '解析表格的表结构信息', 'image_urls': ['http://localhost:5000/files/fdd40fb06d4a4d41b54fab6d33065972.png', 'http://localhost:5000/files/1798a458a94b45779109ede0821f9ff6.png']}, 'id': 'call_00_jLynvzpNVdaqwKUZ2V9znrlL', 'type': 'tool_call'}], invalid_tool_calls=[], usage_metadata={'input_tokens': 550, 'output_tokens': 148, 'total_tokens': 698, 'input_token_details': {'cache_read': 448}, 'output_token_details': {}})
    return {"messages": new_mes}

agent_builder = StateGraph(ExtendedMessagesState)

agent_builder.add_node("message_format",message_format)
agent_builder.add_node("write_file",write_file)
agent_builder.add_node("agent_call",agent_call)

# agent_builder.add_node("return_AImessage",return_AImessage)

agent_builder.add_edge(START,"message_format")
agent_builder.add_edge("message_format","agent_call")
agent_builder.add_edge("agent_call","write_file")
agent_builder.add_edge("write_file",END)

# agent_builder.add_edge(START,"return_AImessage")
# agent_builder.add_edge("return_AImessage",END)

test_graph = agent_builder.compile()
