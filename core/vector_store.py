import faiss
import sqlite3
import numpy as np
from typing import List, Dict, Tuple
import json

class VectorStore:
    def __init__(self, dimension: int = 384):
        """初始化向量存储"""
        # 创建FAISS索引
        self.index = faiss.IndexFlatL2(dimension)
        self.conn = sqlite3.connect('documents.db')
        self.setup_database()
        
    def setup_database(self):
        """设置SQLite数据库"""
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY,
            file_path TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            metadata TEXT,
            faiss_id INTEGER NOT NULL,
            UNIQUE(file_path, chunk_index)
        )
        ''')
        self.conn.commit()

    def add_document(self, 
                    file_path: str, 
                    chunks: List[str], 
                    embeddings: np.ndarray,
                    metadata: Dict = None):
        """添加文档到存储"""
        cursor = self.conn.cursor()
        
        # 获取当前FAISS索引的大小作为起始ID
        start_idx = self.index.ntotal
        
        # 添加向量到FAISS
        self.index.add(embeddings)
        
        # 添加文档信息到SQLite
        for i, chunk in enumerate(chunks):
            cursor.execute('''
            INSERT OR REPLACE INTO documents (file_path, chunk_index, chunk_text, metadata, faiss_id)
            VALUES (?, ?, ?, ?, ?)
            ''', (file_path, i, chunk, json.dumps(metadata or {}), start_idx + i))
            
        self.conn.commit()

        print(f"添加文档后，FAISS索引中的向量数量: {self.index.ntotal}")

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[str, float, Dict]]:
        """搜索最相似的文档"""
        # 搜索最相似的向量
        distances, indices = self.index.search(query_vector.reshape(1, -1), top_k)
        
        results = []
        cursor = self.conn.cursor()
        
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < 0:  # FAISS可能返回-1表示无结果
                continue
                
            # 使用faiss_id查询对应的文档信息
            cursor.execute('''
            SELECT file_path, chunk_text, metadata 
            FROM documents 
            WHERE faiss_id = ?
            ''', (idx,))
            
            row = cursor.fetchone()
            if row:
                file_path, chunk_text, metadata = row
                results.append((
                    file_path,
                    float(distance),
                    {
                        "chunk_text": chunk_text,
                        "metadata": json.loads(metadata)
                    }
                ))
                
        return results

    def clear_all(self):
        """清空所有数据"""
        # 清空 SQLite 数据
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM documents')
        self.conn.commit()
        
        # 重置 FAISS 索引
        dimension = self.index.d  # 保存当前维度
        self.index = faiss.IndexFlatL2(dimension)  # 创建新的空索引
        
        # 验证清空结果
        print(f"FAISS索引中的向量数量: {self.index.ntotal}")
        
        cursor.execute('SELECT COUNT(*) FROM documents')
        doc_count = cursor.fetchone()[0]
        print(f"数据库中的文档数量: {doc_count}")

    def __del__(self):
        """清理资源"""
        self.conn.close() 