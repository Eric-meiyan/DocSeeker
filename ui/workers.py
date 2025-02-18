"""
后台工作线程模块，处理耗时操作
"""

from PyQt6.QtCore import QThread, pyqtSignal
from typing import List
import os
from core.search_service import SearchService

class IndexingWorker(QThread):
    """
    后台索引线程
    
    用于在后台处理文档索引，避免阻塞UI线程
    
    Signals:
        progress (int): 发送索引进度 (0-100)
        finished: 索引完成时发送
        error (str): 发送错误信息
    """
    
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, search_service: SearchService, directories: List[str]):
        """
        初始化索引工作线程
        
        Args:
            search_service: 搜索服务实例
            directories: 要索引的目录列表
        """
        super().__init__()
        self.search_service = search_service
        self.directories = directories
        
    def run(self):
        """
        执行索引任务
        
        遍历所有目录，统计并处理文件，发送进度信息
        如果发生错误，发送错误信号
        """
        try:
            total_files = 0
            processed_files = 0
            
            # 计算总文件数
            for directory in self.directories:
                for root, _, files in os.walk(directory):
                    total_files += len(files)
            
            # 处理文件
            for directory in self.directories:
                for root, _, files in os.walk(directory):
                    for file in files:
                        try:
                            file_path = os.path.join(root, file)
                            self.search_service.index_document(file_path)
                            processed_files += 1
                            progress = int((processed_files / total_files) * 100)
                            self.progress.emit(progress)
                        except Exception as e:
                            print(f"Error processing {file}: {str(e)}")
                            
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e)) 