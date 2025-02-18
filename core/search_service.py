from typing import List, Dict
from .document_processor import DocumentProcessor
from .embedding import EmbeddingService
from .vector_store import VectorStore
import os

class SearchService:
    def __init__(self):
        """初始化搜索服务"""
        self.doc_processor = DocumentProcessor()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        
    def index_document(self, file_path: str):
        """索引单个文档"""
        # 解析文档
        doc_info = self.doc_processor.parse_document(file_path)
        
        if not doc_info["content"]:
            print(f"Warning: No content extracted from {file_path}")
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
        
    def index_directory(self, directory: str, file_extensions: List[str] = None):
        """索引整个目录"""
        if file_extensions is None:
            file_extensions = ['.pdf', '.docx', '.doc', '.txt', '.pptx']
            
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.lower().endswith(ext) for ext in file_extensions):
                    file_path = os.path.join(root, file)
                    self.index_document(file_path)
                    
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
