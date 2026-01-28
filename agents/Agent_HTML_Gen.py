# 报告生成与可视化 Agent
# 生成数据分析报告与可视化图表
# 关键工具（示例）：matplotlib, seaborn, plotly, reportlab

from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek

model = ChatDeepSeek(model="deepseek-chat")

prompt = """
你是一位经验丰富的网页开发者，精通 HTML/JS/CSS/TailwindCSS，请使用这些技术来创建我需要的页面。

请以下面的格式提供代码，所有代码都需要放在一个 HTML 文件中：

```html
这里是 HTML 代码
```
"""

agent = create_agent(model=model, system_prompt=prompt)


