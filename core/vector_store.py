import faiss
import sqlite3
import numpy as np
from typing import List, Dict, Tuple
import json
import os
from utils.logger import Logger
from queue import Queue
from threading import Lock
import tempfile

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
        
        with self.db_lock:  # 使用锁确保线程安全
            cursor = self.conn.cursor()
            try:
                # 开始事务
                cursor.execute('BEGIN TRANSACTION')
                
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
                    
                # 提交事务
                self.conn.commit()
                self.logger.info(f"添加文档成功，FAISS索引中的向量数量: {self.index.ntotal}")
                
            except Exception as e:
                # 回滚事务
                cursor.execute('ROLLBACK')
                # 回滚FAISS索引 - 移除刚添加的向量
                if self.index.ntotal > start_idx:
                    self._rollback_faiss(start_idx)
                self.logger.error(f"添加文档失败: {str(e)}")
                raise

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[str, float, Dict]]:
        """搜索最相似的文档"""
        self.logger.info("执行搜索，top_k: %d", top_k)
        
         #打印index中的向量数量
        print(f"FAISS索引中的向量数量: {self.index.ntotal}")

        #检查数据库状态
        #self.debug_check_database()

        # 检查索引是否为空
        if self.index.ntotal == 0:
            self.logger.warning("FAISS索引为空，无法执行搜索")
            return []
        
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
            else:
                # 记录不一致问题
                self.logger.error(f"数据不一致: FAISS索引包含ID {idx}，但在数据库中未找到对应记录")
                
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

    def _rollback_faiss(self, original_size):
        """回滚FAISS索引到指定大小"""
        if self.index.ntotal <= original_size:
            return
        
        # 创建新索引并只复制原始大小的向量
        temp_index = faiss.IndexFlatL2(self.dimension)
        
        if original_size > 0:
            # 获取原始向量
            vectors = faiss.rev_swig_ptr(self.index.get_xb(), original_size * self.dimension)
            vectors = vectors.reshape(original_size, self.dimension)
            
            # 添加到新索引
            temp_index.add(vectors)
        
        # 替换当前索引
        self.index = temp_index
        self.logger.info(f"FAISS索引已回滚到 {original_size} 个向量") 

    def check_consistency(self):
        """检查FAISS索引和SQLite数据库的一致性"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(DISTINCT faiss_id) FROM documents')
        db_count = cursor.fetchone()[0]
        
        faiss_count = self.index.ntotal
        
        if db_count != faiss_count:
            self.logger.warning(f"数据不一致: FAISS索引包含 {faiss_count} 个向量，但数据库有 {db_count} 条记录")
            return False
        
        # 检查faiss_id范围
        cursor.execute('SELECT MIN(faiss_id), MAX(faiss_id) FROM documents')
        min_id, max_id = cursor.fetchone()
        
        if min_id is not None and max_id is not None:
            if min_id != 0 or max_id != faiss_count - 1:
                self.logger.warning(f"数据ID不连续: faiss_id范围 [{min_id}, {max_id}]，但索引大小为 {faiss_count}")
                return False
        
        self.logger.info(f"数据一致性检查通过: {faiss_count} 个向量")
        return True 

    def export_data(self, index_path: str, db_path: str) -> bool:
        """导出FAISS索引和SQLite数据库"""
        try:
            with self.db_lock:
                # 确保目录存在
                index_dir = os.path.dirname(index_path)
                db_dir = os.path.dirname(db_path)
                
                os.makedirs(index_dir, exist_ok=True)
                os.makedirs(db_dir, exist_ok=True)
                
                # 标准化路径格式
                index_path = os.path.normpath(index_path)
                db_path = os.path.normpath(db_path)
                
                # 处理中文路径问题
                # 方案一：尝试使用临时文件
                temp_index_path = os.path.join(tempfile.gettempdir(), "temp_faiss.index")
                
                # 导出FAISS索引到临时文件
                faiss.write_index(self.index, temp_index_path)
                self.logger.info(f"FAISS索引已导出到临时文件，包含 {self.index.ntotal} 个向量")
                
                # 复制到目标位置
                import shutil
                shutil.copy2(temp_index_path, index_path)
                os.remove(temp_index_path)
                
                # 导出SQLite数据库
                dest_conn = sqlite3.connect(db_path)
                with dest_conn:
                    self.conn.backup(dest_conn)
                dest_conn.close()
                
                self.logger.info(f"数据导出完成")
                return True
                
        except Exception as e:
            self.logger.error(f"导出数据失败: {str(e)}")
            return False
        
    def import_data(self, index_path: str, db_path: str) -> bool:
        """导入FAISS索引和SQLite数据库
        
        Args:
            index_path: FAISS索引文件路径
            db_path: SQLite数据库文件路径
            
        Returns:
            bool: 是否成功导入
        """
        try:
            with self.db_lock:
                # 首先检查文件是否存在
                if not os.path.exists(index_path) or not os.path.exists(db_path):
                    self.logger.error("导入文件不存在")
                    return False
                    
                # 关闭当前连接
                self.conn.close()
                
                # 导入FAISS索引
                self.index = faiss.read_index(index_path)
                self.logger.info(f"已导入FAISS索引，包含 {self.index.ntotal} 个向量")
                
                # 备份当前数据库
                if os.path.exists('documents.db'):
                    backup_path = 'documents.db.bak'
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                    os.rename('documents.db', backup_path)
                    self.logger.info(f"已备份原数据库为 {backup_path}")
                
                # 复制新数据库
                import shutil
                shutil.copy2(db_path, 'documents.db')
                self.logger.info(f"已导入SQLite数据库")
                
                # 重新连接数据库
                self._setup_database()
                
                # 验证一致性
                is_consistent = self.check_consistency()
                self.logger.info(f"导入后数据一致性检查: {is_consistent}")
                
                return is_consistent
                
        except Exception as e:
            self.logger.error(f"导入数据失败: {str(e)}")
            # 尝试恢复数据库
            if os.path.exists('documents.db.bak'):
                if os.path.exists('documents.db'):
                    os.remove('documents.db')
                os.rename('documents.db.bak', 'documents.db')
                self.logger.info("已从备份恢复数据库")
                
            # 重新连接数据库
            try:
                self._setup_database()
            except:
                pass
                
            # 重新加载原始索引
            try:
                if os.path.exists(self.index_file):
                    self.index = faiss.read_index(self.index_file)
                else:
                    self.index = faiss.IndexFlatL2(self.dimension)
            except:
                self.index = faiss.IndexFlatL2(self.dimension)
                
            return False 