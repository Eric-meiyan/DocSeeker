import faiss
import sqlite3
import numpy as np
from typing import List, Dict, Tuple
import json
import os
from utils.logger import Logger
from queue import Queue
from threading import Lock

class VectorStore:
    def __init__(self, dimension: int = 384, index_file: str = "faiss.index"):
        """
        初始化向量存储
        
        Args:
            dimension: 向量维度
            index_file: FAISS索引文件路径
        """
        self.logger = Logger.get_logger(__name__)
        self.logger.info("初始化向量存储，维度: %d, 索引文件: %s", dimension, index_file)
        self.index_file = index_file
        self.dimension = dimension
        self.db_lock = Lock()
        
        # 加载FAISS索引
        if os.path.exists(index_file):
            try:
                self.index = faiss.read_index(index_file)
                self.logger.info("已加载现有索引，包含 %d 个向量", self.index.ntotal)
            except Exception as e:
                self.logger.error("加载索引失败: %s，创建新索引", str(e))
                self.index = faiss.IndexFlatL2(dimension)
        else:
            self.index = faiss.IndexFlatL2(dimension)
            
        # 连接数据库
        self._setup_database()
        
    def _setup_database(self):
        """在当前线程中设置数据库连接"""
        self.conn = sqlite3.connect('documents.db')
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

    def add_document_batch(self, documents: List[Dict]):
        """批量添加文档，在同一个事务中处理"""
        with self.db_lock:
            cursor = self.conn.cursor()
            try:
                cursor.execute('BEGIN TRANSACTION')
                
                start_idx = self.index.ntotal
                all_embeddings = []
                
                for doc in documents:
                    embeddings = doc['embeddings']
                    all_embeddings.extend(embeddings)
                    
                    for i, chunk in enumerate(doc['chunks']):
                        cursor.execute('''
                        INSERT OR REPLACE INTO documents 
                        (file_path, chunk_index, chunk_text, metadata, faiss_id)
                        VALUES (?, ?, ?, ?, ?)
                        ''', (
                            doc['file_path'],
                            i,
                            chunk,
                            json.dumps(doc.get('metadata', {})),
                            start_idx + i
                        ))
                    
                    start_idx += len(doc['chunks'])
                
                # 批量添加向量到FAISS
                if all_embeddings:
                    self.index.add(np.array(all_embeddings))
                
                cursor.execute('COMMIT')
                self.logger.info(f"批量添加完成，新增 {len(all_embeddings)} 个向量")
                
            except Exception as e:
                cursor.execute('ROLLBACK')
                self.logger.error(f"批量添加失败: {str(e)}")
                raise

    def add_document(self, 
                    file_path: str, 
                    chunks: List[str], 
                    embeddings: np.ndarray,
                    metadata: Dict = None):
        """添加文档到存储"""
        self.logger.info("添加文档: %s, 块数: %d", file_path, len(chunks))
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
        self.logger.info("执行搜索，top_k: %d", top_k)
       
        #打印index中的向量数量
        print(f"FAISS索引中的向量数量: {self.index.ntotal}")

        #检查数据库状态
        self.debug_check_database()
        
        # 搜索最相似的向量
        distances, indices = self.index.search(query_vector.reshape(1, -1), top_k)
        
        results = []
        cursor = self.conn.cursor()
        
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < 0:  # FAISS可能返回-1表示无结果
                continue
                
            #打印idx的值
            print(f"idx的值: {idx}")

            # 使用faiss_id查询对应的文档信息
            print(f"正在执行SQL查询: faiss_id = {idx}")
            cursor.execute('''
            SELECT COUNT(*) FROM documents
            ''')
            total_count = cursor.fetchone()[0]
            print(f"数据库中总记录数: {total_count}")

            #查询faiss_id等于76的值，查询语句中不用占位符，直接写76
            # cursor.execute('''
            # SELECT file_path, chunk_text, metadata FROM documents
            # WHERE faiss_id = 76
            # ''')
      
            # 先拼接SQL语句
            sql = f'''
            SELECT file_path, chunk_text, metadata FROM documents
            WHERE faiss_id = {idx}
            '''
            # 执行拼接后的SQL语句
            cursor.execute(sql)
            
            # 检查SQL执行是否成功
            if cursor.rowcount == -1:
                print("查询执行成功，但没有找到匹配记录")
            else:
                print(f"查询找到 {cursor.rowcount} 条记录")
            
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

    def save_index(self):
        """保存FAISS索引到文件"""
        try:
            faiss.write_index(self.index, self.index_file)
            print(f"索引已保存，包含 {self.index.ntotal} 个向量")
        except Exception as e:
            print(f"保存索引失败: {e}")
            
    def clear_all(self):
        """清空所有数据"""
        # 清空 SQLite 数据
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM documents')
        self.conn.commit()
        
        # 重置 FAISS 索引
        dimension = self.index.d  # 保存当前维度
        self.index = faiss.IndexFlatL2(dimension)  # 创建新的空索引
        
        # 删除索引文件
        if os.path.exists(self.index_file):
            os.remove(self.index_file)
            
        print("所有数据已清空")

    def __del__(self):
        """清理资源"""
        self.save_index()  # 保存索引
        self.conn.close()  # 关闭数据库连接 

    def debug_check_database(self):
        """检查数据库中的记录"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT faiss_id, file_path FROM documents ORDER BY faiss_id')
        records = cursor.fetchall()
        print("数据库中的记录:")
        for record in records:
            print(f"faiss_id: {record[0]}, file_path: {record[1]}") 