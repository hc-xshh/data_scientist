# create_chat.py
import requests

url = "http://8.137.22.234:81/api/v1/chats_openai/a4ca90adfa7911f09725269aa1038e6c/chat/completions"
headers = {
    "Authorization": "Bearer ragflow-WAOfF27-0M1U5WsV19OVMdrc75jYvG2ugRWiA9RJXXo",
    "Content-Type": "application/json"
}
data = {
    "model": "model",
    "messages":[{"role":"user","content":"哈哈的电话号码是多少？"}],
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