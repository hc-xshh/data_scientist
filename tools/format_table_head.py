from models.Qwen_Models import call_qwq3_vl_plus,call_qwq3_vl_flash
from langchain.tools import tool
from pydantic import BaseModel,Field
from tools.image_to_base64 import local_image_to_base64,web_image_to_base64

# 工具入参定义
class ExtractQuerySchema(BaseModel):
    table_desciption:str= Field(description="用户对于表信息的描述(例如：表的名称等)，辅助工具解析表头")
    image_urls: list[str] =Field(description="图片文件的路径，网络路径或者本地绝对路径、相对路径都可以,必须传入")


# 大模型格式化输出模型
# 字段模型
class Table_column(BaseModel):
    """数据字段(列)信息定义模型"""
    id:int | None = Field(description="字段序号，整数")
    column_name_ch:str = Field(description="字段中文名称，与字段英文名称对照")
    column_name_en:str = Field(description="字段英文名称，可为英文单词简写或拼音首字母组合，与字段中文名称对照")
    datatype:str = Field(description="定义字段的数据类型，用于创建MySQL数据库表，如varchar(20)、decimal(10,2)等")
# 表模型
class Table_info(BaseModel):
    """数据表结构信息定义模型"""
    table_name_cn:str = Field(description="数据表表格的中文名称，与数据数据表表格的英文名称对照")
    table_name_en:str = Field(description="数据表表格的英文名称，可为英文单词简写或拼音首字母组合，与数据数据表表格的中文名称对照")
    head_cnt:int | None = Field(description="表格中表头的行数")
    columns:list[Table_column] = Field(description="数据表格列名信息集合")
    

@tool(args_schema=ExtractQuerySchema)
def format_table_head(table_desciption:str,image_urls:list[str]):
    """
    一个通过表头图片解析excel文件表头的工具,只需要至少传入一张图片的链接地址，自动获取并解析图片，从中获取表结构信息，不需要太多额外的描述
    返回从图片解析出来的表结构信息。
    """
    # 如果传入图片的两个参数都为空 则不执行
    # print("传入base64：",len(image_base64),"，传入url：",len(image_url))
    # print(image_urls)
        
    # 创建模型
    vllm = call_qwq3_vl_flash(0.3)
    
    # 定义大模型的系统提示词
    system_promt = """
    识别图片中表格的表头信息，
    规则：表头可能存在多级表头的情况，需要将多级表头组合起来命名(注意合并单元格情况)，英文表名或字段名不能存在除'_'以外的特殊符号。
    你需要输出如下信息：
    - 数据表格的中文名称(table_name_cn)：可以由用户提供中文名称或用户提供的英文名称翻译为中文，无法理解或用户未提供则设置为None
    - 数据表格的英文名称(table_name_en)：可以由用户提供英文名称或用户提供的中文名称翻译为英文(简写或拼音首字母(不建议))，长度不能超过30个字符
    - 表头的行数(head_cnt):识别表头行一共有多少行
    - 列(字段)信息集合(columns)：[
        - 序号(id):整数类型，由图片中自带的excel序号转换而来，A-1，B-2，C-3...AA-27,如果无法识别，则从1开始自动编号
        - 字段中文名名称(column_name_ch):按规则从图片中提取，不能直接提取则从英文列名翻译、从数据中总结。
        - 字段英文名名称(column_name_en):按规则从图片中提取，不能直接提取则从中文列名翻译、从数据中总结。英文名称必须去除除'_'以外的特殊符号。
        - 数据类型(datatype):以MySQL的字段数据类型为标准(日期格式直接使用varchar()类型，数字使用decimal)，从样例数据中总结归纳,注意日期和数字格式
    ]
    用户可能传入一张表的多张表头图片，需要根据excel列序号去掉重复项。
    """

    # 构造用户消息列表
    user_content_blocks= [
                {
                    "type": "text",
                    "text": table_desciption
                },                
            ]
    
    for url in image_urls:
        is_network_path = url.lower().startswith(("http://","https://"))
        if is_network_path:
            image_base64=web_image_to_base64(url)
            user_content_blocks.append(
                {
                    "type": "image",
                    "base64": image_base64,
                    "mime_type": "image/jpeg",
                }
            )
        else:
            image_base64=local_image_to_base64(url)
            user_content_blocks.append(
                {
                    "type": "image",
                    "base64": image_base64,
                    "mime_type": "image/jpeg",
                }
            )
    
    # 拼接完整的消息
    input_messages=[
        {
            "role":"system",
            "content":[{
                "type":"text",
                "text":system_promt
            }]
        },
        {
            "role": "user",
            "content": user_content_blocks
        }
    ]
    vllm_ins = vllm.with_structured_output(Table_info)
    res =  vllm_ins.invoke(input_messages)
    # print("format_table_head工具消息：",res)
    # res_dict= res.model_dump()
    # print("文件结构化成功>>>>>>>")
    return res