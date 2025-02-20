"""
后台工作线程模块，处理耗时操作
"""

from PyQt6.QtCore import QThread, pyqtSignal
from typing import List, Dict
import os
from core.search_service import SearchService
from queue import Queue
import numpy as np
from utils.logger import Logger

class IndexingWorker(QThread):
    """
    后台索引线程
    
    用于在后台处理文档索引，避免阻塞UI线程
    
    Signals:
        progress (int): 发送索引进度 (0-100)
        finished: 索引完成时发送
        error (str): 发送错误信息
        batch_ready (list): 发送批处理数据
    """
    
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    batch_ready = pyqtSignal(list)  # 发送批处理数据
    
    def __init__(self, search_service: SearchService, directories: List[str], batch_size: int = 100):
        """
        初始化索引工作线程
        
        Args:
            search_service: 搜索服务实例
            directories: 要索引的目录列表
            batch_size: 批处理大小
        """
        super().__init__()
        self.search_service = search_service
        self.directories = directories
        self.batch_size = batch_size
        self.current_batch = []
        self.logger = Logger.get_logger(__name__)
        
    def run(self):
        """
        执行索引任务
        
        遍历所有目录，统计并处理文件，发送进度信息
        如果发生错误，发送错误信号
        """

        self.logger.info("run debug：函数开始")

        try:
            total_files = sum(1 for directory in self.directories 
                            for _, _, files in os.walk(directory) 
                            for _ in files)
            processed_files = 0

            self.logger.info(f"run debug：开始索引文档，总文件数: {total_files}")
            self.logger.info("run debug：开始索引文档")
            for directory in self.directories:
                for root, _, files in os.walk(directory):
                    for file in files:
                        try:
                            file_path = os.path.join(root, file)
                            self.logger.info(f"开始处理文件: {file_path}")
                            
                            # 处理单个文档
                            doc_info = self.search_service.doc_processor.parse_document(file_path)
                            if not doc_info["content"]:
                                self.logger.info(f"文件 {file_path} 内容为空，跳过。")
                                continue
                                
                            chunks = self.search_service.doc_processor.create_chunks(doc_info["content"])
                            if not chunks:
                                self.logger.info(f"文件 {file_path} 分块为空，跳过。")
                                continue
                                
                            embeddings = self.search_service.embedding_service.encode(chunks)
                            self.logger.info(f"文件 {file_path} 编码完成。")
                            
                            # 添加到当前批次
                            self.current_batch.append({
                                'file_path': file_path,
                                'chunks': chunks,
                                'embeddings': embeddings,
                                'metadata': doc_info["metadata"]
                            })
                            self.logger.info(f"文件 {file_path} 添加到批次中。")
                            
                            # 如果达到批处理大小，发送数据
                            if len(self.current_batch) >= self.batch_size:
                                self.batch_ready.emit(self.current_batch)
                                self.current_batch = []
                                self.logger.info("批次数据已发送。")
                            
                            processed_files += 1
                            progress = int((processed_files / total_files) * 100)
                            self.progress.emit(progress)
                            self.logger.info(f"索引进度: {progress}%")
                            
                        except Exception as e:
                            self.logger.error(f"处理文件出错 {file}: {str(e)}")
                            
            # 处理最后的批次
            if self.current_batch:
                self.batch_ready.emit(self.current_batch)
                self.logger.info("发送最后的批次数据。")
                
            self.finished.emit()
            self.logger.info("索引完成。")
            
        except Exception as e:
            self.error.emit(str(e)) 
            self.logger.error(f"索引过程出错: {str(e)}")