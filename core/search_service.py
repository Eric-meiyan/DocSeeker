from typing import List, Dict
from .document_processor import DocumentProcessor
from .embedding import EmbeddingService
from .vector_store import VectorStore
import os
from utils.logger import Logger

class SearchService:
    def __init__(self, index_file: str = "faiss.index"):
        """
        初始化搜索服务
        
        Args:
            index_file: FAISS索引文件路径
        """
        self.logger = Logger.get_logger(__name__)
        self.logger.info("初始化搜索服务")
        self.doc_processor = DocumentProcessor()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore(index_file=index_file)
        
    def index_document(self, file_path: str):
        """索引单个文档"""
        self.logger.info("开始索引文档: %s", file_path)
        # 解析文档
        doc_info = self.doc_processor.parse_document(file_path)
        
        if not doc_info["content"]:
            self.logger.warning("未能从文档提取内容: %s", file_path)
            return
            
        # 分块
        chunks = self.doc_processor.create_chunks(doc_info["content"])
        
        if not chunks:
            print(f"Warning: No chunks created for {file_path}")
            return
            
        # 生成向量
        embeddings = self.embedding_service.encode(chunks)
        
        # 存储
        self.vector_store.add_document(
            file_path=file_path,
            chunks=chunks,
            embeddings=embeddings,
            metadata=doc_info["metadata"]
        )
        
    def index_directory(self, directory: str):
        """索引单个目录"""
        if not os.path.exists(directory):
            raise FileNotFoundError(f"目录不存在: {directory}")
        
        # 获取目录下的所有文件
        files = []
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                if any(filename.lower().endswith(ext) for ext in self.config.get_file_extensions()):
                    files.append(os.path.join(root, filename))
                
        # 处理所有文件
        for file in files:
            self.index_document(file)
        
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """搜索文档"""
        # 生成查询向量
        query_vector = self.embedding_service.encode(query)
        
        # 搜索
        results = self.vector_store.search(query_vector, top_k)
        
        # 格式化结果
        formatted_results = []
        for file_path, score, info in results:
            formatted_results.append({
                "file_path": file_path,
                "score": 1.0 / (1.0 + score),  # 转换距离为相似度分数
                "chunk_text": info["chunk_text"],
                "metadata": info["metadata"]
            })
            
        return formatted_results 
    
    def clear_all(self):
        """清空所有数据"""
        self.vector_store.clear_all()   

    def save_index(self):
        """保存索引"""
        self.vector_store.save_index()   

    def rebuild_index(self):
        """重建所有索引"""
        # 清空现有索引
        self.vector_store.clear_all()
        
        # 获取所有启用的目录
        enabled_dirs = [d for d in self.config.get_scan_directories() 
                       if self.config.is_directory_enabled(d)]
        
        # 重新索引所有启用的目录
        for directory in enabled_dirs:
            self.index_directory(directory)   
