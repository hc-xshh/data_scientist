# create_chat.py
import requests
from pydantic import BaseModel, Field
from langchain_core.tools import tool


RAGFlow_Server = "8.137.22.234"
SVR_WEB_HTTP_PORT = 81
chat_id = "a4ca90adfa7911f09725269aa1038e6c"
API_KEY = "ragflow-WAOfF27-0M1U5WsV19OVMdrc75jYvG2ugRWiA9RJXXo"

question = "哈哈的电话号码是多少？"

url = f"http://{RAGFlow_Server}:{SVR_WEB_HTTP_PORT}/api/v1/chats_openai/{chat_id}/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
data = {
    "model": "model",
    "messages":[{"role":"user","content":question}],
    "stream": False,
    # "extra_body": {
    #       "reference": True,
    #       "metadata_condition": {
    #         "logic": "and",
    #         "conditions": [
    #           {
    #             "name": "author",
    #             "comparison_operator": "is",
    #             "value": "bob"
    #           }
    #         ]
    #       }
    #     }
}

response = requests.post(url, json=data, headers=headers)
print(response.status_code)
print(response.json())


class RAGQueryInput(BaseModel):
    """RAG查询输入参数"""
    query: str = Field(description="用户的查询问题")

@tool(args_schema=RAGQueryInput)
def get_ragflow_answer(query: str) -> str:
    data["messages"][0]["content"] = query
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        resp_json = response.json()
        if "choices" in resp_json and len(resp_json["choices"]) > 0:
            return resp_json["choices"][0]["message"]["content"]
        else:
            return "未找到相关答案"
    else:
        return f"请求失败，状态码：{response.status_code}"