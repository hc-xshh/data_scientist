from langchain_core.tools import tool
from langchain_community.vectorstores import Chroma  # 改用 Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.document_loaders import (
    PyPDFLoader, 
    DirectoryLoader
)
from langchain_community.document_loaders.text import TextLoader
from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field
from typing import List
import os

class RAGQueryInput(BaseModel):
    """RAG查询输入参数"""
    query: str = Field(description="用户的查询问题")
    top_k: int = Field(default=3, description="返回的相关文档数量")

# 全局向量存储实例
_vectorstore = None

def _init_vectorstore():
    """初始化向量存储"""
    global _vectorstore
    
    if _vectorstore is not None:
        return _vectorstore
    
    kb_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "kb", "documents","tobacco")
    vectorstore_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "kb", "vectorstore")
    
    # 确保向量库目录存在
    os.makedirs(vectorstore_path, exist_ok=True)
    
    # 初始化 embeddings
    from config import settings
    embeddings = DashScopeEmbeddings(
        model="text-embedding-v1",
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
    )
    
    # 检查向量库是否已存在
    if os.path.exists(vectorstore_path) and os.listdir(vectorstore_path):
        print("加载已存在的向量库...")
        _vectorstore = Chroma(
            persist_directory=vectorstore_path,
            embedding_function=embeddings
        )
        print(f"向量库加载完成")
        return _vectorstore
    
    # 向量库不存在，需要创建
    print("创建新的向量库...")
    
    # 加载文档
    documents = []
    
    # 定义支持UTF-8编码的TextLoader
    class UTF8TextLoader(TextLoader):
        def __init__(self, file_path: str):
            super().__init__(file_path, encoding='utf-8')
    
    # 支持多种文档格式
    loaders = [
        DirectoryLoader(kb_path, glob="**/*.pdf", loader_cls=PyPDFLoader),
        DirectoryLoader(kb_path, glob="**/*.txt", loader_cls=UTF8TextLoader),
        DirectoryLoader(kb_path, glob="**/*.md", loader_cls=UTF8TextLoader),
        DirectoryLoader(kb_path, glob="**/*.docx", loader_cls=Docx2txtLoader)
    ]
    
    for loader in loaders:
        try:
            documents.extend(loader.load())
        except Exception as e:
            print(f"加载文档时出错: {e}")
    
    if not documents:
        print("警告: 未找到任何文档")
        return None
    
    # 文档切分
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", "!", "?", ".", "!", "?", " "]
    )
    doc_splits = text_splitter.split_documents(documents)
    
    # 创建并持久化向量存储
    _vectorstore = Chroma.from_documents(
        documents=doc_splits,
        embedding=embeddings,
        persist_directory=vectorstore_path
    )
    
    print(f"向量库创建完成，共 {len(doc_splits)} 个文档片段，已保存到 {vectorstore_path}")
    return _vectorstore

@tool(args_schema=RAGQueryInput)
def retrieve_documents(query: str, top_k: int = 3) -> str:
    """
    【优先使用】从知识库中检索相关文档。对于所有用户问题，都应该先调用此工具。
    
    强制使用场景：
    - 所有用户提出的问题（无论是否看起来是隐私信息）
    - 任何需要事实性回答的问题
    - 即使你认为问题涉及隐私，也应该先检索确认知识库中是否有信息
    
    参数：
    - query: 用户的原始问题
    - top_k: 返回的相关文档数量，默认3
    """
    vectorstore = _init_vectorstore()
    
    if vectorstore is None:
        return "知识库未初始化或为空,请先上传文档。"
    
    # 检索相关文档
    retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})
    docs = retriever.invoke(query)
    
    if not docs:
        return "未找到相关文档。"
    
    # 格式化返回结果
    context = "\n\n---\n\n".join([
        f"文档 {i+1}:\n{doc.page_content}\n来源: {doc.metadata.get('source', '未知')}"
        for i, doc in enumerate(docs)
    ])
    
    return context

@tool
def refresh_knowledge_base() -> str:
    """
    刷新知识库，重新加载所有文档。
    
    使用场景：
    - 用户上传了新文档
    - 知识库需要更新
    """
    global _vectorstore
    _vectorstore = None
    
    # 删除旧的向量库
    vectorstore_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "kb", "vectorstore")
    if os.path.exists(vectorstore_path):
        import shutil
        shutil.rmtree(vectorstore_path)
        print("已删除旧的向量库")
    
    _init_vectorstore()
    return "知识库已刷新"