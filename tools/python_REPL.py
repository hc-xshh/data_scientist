from langchain_experimental.utilities import PythonREPL
from langchain_deepseek import ChatDeepSeek

# Initialize the Python REPL tool
python_repl = PythonREPL()

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

# 1. 定义提示词模板:告诉 AI 只返回代码
template = r"""编写 Python 代码来解决用户的问题。只返回 Markdown 格式的 Python 代码,不要包含任何解释文字。
例如:
```python
print(2 + 2)
```"""
prompt = ChatPromptTemplate.from_messages([
    ("system", template), 
    ("human", "{input}")
])

# 2. 初始化模型
model = ChatDeepSeek(model="deepseek-chat")

# 3. 定义清理函数：去掉 Markdown 代码块的包裹符
def _sanitize_output(text: str):
    # 去除 ```python 开头和 ``` 结尾
    lines = text.split('\n')
    if lines[0].startswith('```python'):
        lines = lines[1:]
    if lines[-1].strip() == '```':
        lines = lines[:-1]
    return '\n'.join(lines)

# 4. 构建 LangChain 链 (LCEL 语法)
chain = (
    prompt 
    | model 
    | StrOutputParser() # 将 LLM 输出转为字符串
    | _sanitize_output # 清理代码格式
    | python_repl.run # 执行代码
)

# result = chain.invoke({"input": "计算从 1 到 100 的所有整数的和。"})
# print("计算结果:", result)

# 测试：画图 (需要安装 matplotlib)
# result = chain.invoke({"input": "画一个正弦函数图像"})
# 这将返回图像数据或保存图像的路径

from langchain_experimental.tools.python.tool import PythonREPLTool

repl_tool = PythonREPLTool()

