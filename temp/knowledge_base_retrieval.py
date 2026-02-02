import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, CSVLoader, 
    UnstructuredHTMLLoader, UnstructuredMarkdownLoader,
    UnstructuredExcelLoader, Docx2txtLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.tools.retriever import create_retriever_tool
from langchain_community.document_loaders import DirectoryLoader
from langchain.tools import tool
import hashlib

class MultiFormatDocumentLoader:
    """支持多种格式的文档加载器"""
    
    def __init__(self, directory_path: str):
        self.directory_path = Path(directory_path)
        self.loader_mapping = {
            '.txt': TextLoader,
            '.pdf': PyPDFLoader,
            '.csv': CSVLoader,
            '.html': UnstructuredHTMLLoader,
            '.htm': UnstructuredHTMLLoader,
            '.md': UnstructuredMarkdownLoader,
            '.mdx': UnstructuredMarkdownLoader,
            '.markdown': UnstructuredMarkdownLoader,
            '.xlsx': UnstructuredExcelLoader,
            '.xls': UnstructuredExcelLoader,
            '.docx': Docx2txtLoader,
            '.properties': TextLoader,
            '.vtt': TextLoader
        }
    
    def load_documents(self) -> List[Any]:
        """加载目录下的所有文档"""
        all_documents = []
        
        for file_path in self.directory_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.loader_mapping:
                try:
                    loader_class = self.loader_mapping[file_path.suffix.lower()]
                    
                    # 特殊处理CSV文件
                    if file_path.suffix.lower() == '.csv':
                        loader = CSVLoader(
                            file_path=str(file_path),
                            encoding='utf-8'
                        )
                    # 特殊处理Excel文件
                    elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                        loader = UnstructuredExcelLoader(
                            str(file_path),
                            mode="elements"
                        )
                    else:
                        loader = loader_class(str(file_path))
                    
                    documents = loader.load()
                    
                    # 添加元数据
                    for doc in documents:
                        doc.metadata.update({
                            'source': str(file_path),
                            'file_type': file_path.suffix.lower(),
                            'file_name': file_path.name
                        })
                    
                    all_documents.extend(documents)
                    print(f"成功加载: {file_path}")
                    
                except Exception as e:
                    print(f"加载文件 {file_path} 时出错: {e}")
        
        return all_documents

class KnowledgeBaseAgent:
    def __init__(
        self,
        knowledge_base_path: str,
        persist_directory: str = "./chroma_db",
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.1,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        初始化知识库Agent
        
        Args:
            knowledge_base_path: 知识库文件夹路径
            persist_directory: 向量数据库存储路径
            model_name: 使用的模型名称
            temperature: 模型温度参数
            chunk_size: 文本分割大小
            chunk_overlap: 文本分割重叠大小
        """
        self.knowledge_base_path = knowledge_base_path
        self.persist_directory = persist_directory
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 初始化LLM
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            streaming=False
        )
        
        # 初始化嵌入模型
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small"
        )
        
        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "？", "！", "；", "，", " ", ""]
        )
        
        self.retriever = None
        self.agent_executor = None
        
    def create_vector_store(self, force_recreate: bool = False):
        """
        创建向量存储
        
        Args:
            force_recreate: 是否强制重新创建向量库
        """
        # 计算知识库内容的哈希值
        current_hash = self._calculate_knowledge_base_hash()
        hash_file = Path(self.persist_directory) / "kb_hash.txt"
        
        # 检查是否需要重新创建
        if not force_recreate and hash_file.exists():
            with open(hash_file, 'r') as f:
                stored_hash = f.read().strip()
            if stored_hash == current_hash:
                print("检测到已有向量库，直接加载...")
                self._load_existing_vector_store()
                return
        
        print("开始创建新的向量库...")
        
        # 加载文档
        loader = MultiFormatDocumentLoader(self.knowledge_base_path)
        documents = loader.load_documents()
        
        if not documents:
            raise ValueError("未找到任何可处理的文档")
        
        print(f"共加载 {len(documents)} 个文档")
        
        # 分割文档
        texts = self.text_splitter.split_documents(documents)
        print(f"分割为 {len(texts)} 个文本块")
        
        # 创建向量存储
        vectorstore = Chroma.from_documents(
            documents=texts,
            embedding=self.embeddings,
            persist_directory=self.persist_directory
        )
        vectorstore.persist()
        
        # 保存哈希值
        hash_file.parent.mkdir(parents=True, exist_ok=True)
        with open(hash_file, 'w') as f:
            f.write(current_hash)
        
        self.retriever = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}  # 返回最相关的5个结果
        )
        
        print("向量库创建完成")
    
    def _calculate_knowledge_base_hash(self) -> str:
        """计算知识库内容的哈希值"""
        hash_obj = hashlib.md5()
        
        for file_path in Path(self.knowledge_base_path).rglob('*'):
            if file_path.is_file():
                try:
                    # 添加文件路径和大小到哈希计算
                    hash_obj.update(str(file_path).encode())
                    hash_obj.update(str(file_path.stat().st_size).encode())
                    
                    # 对于文本文件，添加内容到哈希计算
                    if file_path.suffix.lower() in ['.txt', '.md', '.mdx', '.markdown', '.properties']:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            hash_obj.update(content.encode())
                except:
                    continue
        
        return hash_obj.hexdigest()
    
    def _load_existing_vector_store(self):
        """加载已存在的向量存储"""
        vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings
        )
        
        self.retriever = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
        print("向量库加载完成")
    
    def create_retriever_tool(self):
        """创建检索工具"""
        if self.retriever is None:
            raise ValueError("请先创建向量存储")
        
        retriever_tool = create_retriever_tool(
            self.retriever,
            "knowledge_base_search",
            "在知识库中搜索相关信息。当用户询问关于公司、产品、政策、文档内容等问题时使用此工具。"
        )
        
        return retriever_tool
    
    @tool
    def knowledge_base_summary(self) -> str:
        """获取知识库的摘要信息"""
        summary = []
        
        # 统计文件类型
        file_types = {}
        total_size = 0
        
        for file_path in Path(self.knowledge_base_path).rglob('*'):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                file_types[suffix] = file_types.get(suffix, 0) + 1
                total_size += file_path.stat().st_size
        
        summary.append("知识库统计信息:")
        summary.append(f"总文件数: {sum(file_types.values())}")
        summary.append(f"总大小: {total_size / 1024 / 1024:.2f} MB")
        summary.append("文件类型分布:")
        for file_type, count in sorted(file_types.items()):
            summary.append(f"  {file_type}: {count} 个")
        
        return "\n".join(summary)
    
    def create_agent(self):
        """创建Agent"""
        if self.retriever is None:
            self.create_vector_store()
        
        # 获取工具
        retriever_tool = self.create_retriever_tool()
        tools = [retriever_tool, self.knowledge_base_summary]
        
        # 创建提示模板
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的知识库助手，专门帮助用户查询和分析本地知识库中的信息。
            
            重要指导原则：
            1. 当用户询问具体信息时，务必使用知识库检索工具
            2. 如果知识库中没有相关信息，请如实告知
            3. 引用信息时要注明来源
            4. 保持回答专业、准确
            5. 不要编造信息
            
            当前知识库位置：{kb_path}
            """),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        # 创建Agent
        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=tools,
            prompt=prompt
        )
        
        # 创建Agent执行器
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )
        
        return self.agent_executor
    
    def query(self, question: str, **kwargs) -> str:
        """查询知识库"""
        if self.agent_executor is None:
            self.create_agent()
        
        try:
            response = self.agent_executor.invoke({
                "input": question,
                "kb_path": self.knowledge_base_path,
                **kwargs
            })
            return response["output"]
        except Exception as e:
            return f"查询过程中出现错误: {str(e)}"
    
    def batch_query(self, questions: List[str]) -> List[str]:
        """批量查询"""
        results = []
        for question in questions:
            result = self.query(question)
            results.append(result)
        return results

# 3. 使用示例
def main():
    # 设置OpenAI API密钥
    os.environ["OPENAI_API_KEY"] = "your-openai-api-key"
    
    # 初始化Agent
    agent = KnowledgeBaseAgent(
        knowledge_base_path="./knowledge_base",  # 你的知识库文件夹路径
        persist_directory="./chroma_db",
        model_name="gpt-3.5-turbo",
        chunk_size=1000,
        chunk_overlap=200
    )
    
    # 创建向量库（第一次运行时会自动创建）
    print("正在初始化知识库...")
    agent.create_vector_store()
    
    # 创建Agent
    print("正在创建Agent...")
    agent.create_agent()
    
    # 示例查询
    while True:
        question = input("\n请输入您的问题 (输入'quit'退出): ")
        if question.lower() == 'quit':
            break
        
        print("\n思考中...")
        response = agent.query(question)
        print(f"\n回答: {response}")

# 4. 高级功能扩展
class AdvancedKnowledgeBaseAgent(KnowledgeBaseAgent):
    """扩展的知识库Agent，包含更多功能"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_history = []
    
    @tool
    def search_by_metadata(self, file_type: Optional[str] = None, 
                          source_contains: Optional[str] = None) -> str:
        """
        根据元数据搜索文档
        
        Args:
            file_type: 文件类型，如 '.pdf', '.docx'
            source_contains: 来源路径包含的字符串
        """
        # 这里可以添加更复杂的元数据搜索逻辑
        # 当前简化实现，实际中可能需要修改Chroma的检索方式
        
        return "元数据搜索功能需要进一步实现Chroma的元数据过滤"
    
    def get_query_history(self, limit: int = 10) -> List[Dict]:
        """获取查询历史"""
        return self.query_history[-limit:]
    
    def clear_history(self):
        """清除查询历史"""
        self.query_history.clear()

if __name__ == "__main__":
    main()