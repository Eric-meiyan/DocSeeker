"""
文件监控模块，用于监控文档目录变化并触发索引更新
"""

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import List, Callable
import os
import time
from threading import Lock

class FileMonitor:
    """
    文件监控器，用于监控文档目录的变化
    
    特点：
    1. 支持多目录监控
    2. 防抖动处理，避免频繁触发
    3. 支持文件过滤
    4. 线程安全
    """
    
    def __init__(self, 
                 directories: List[str], 
                 file_extensions: List[str],
                 callback: Callable[[str, str], None],
                 debounce_seconds: float = 1.0):
        """
        初始化文件监控器
        
        Args:
            directories: 要监控的目录列表
            file_extensions: 要监控的文件扩展名列表
            callback: 文件变化时的回调函数，接收事件类型和文件路径两个参数
            debounce_seconds: 防抖动时间，单位秒
        """
        self.directories = directories
        self.file_extensions = [ext.lower() for ext in file_extensions]
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        
        self.observer = Observer()
        self.lock = Lock()
        self.last_event_time = 0
        self.handler = self._create_event_handler()
        
    def _create_event_handler(self) -> FileSystemEventHandler:
        """创建文件系统事件处理器"""
        
        monitor = self
        
        class Handler(FileSystemEventHandler):
            def on_any_event(self, event):
                # 忽略目录事件
                if event.is_directory:
                    return
                    
                # 检查文件扩展名
                if not any(event.src_path.lower().endswith(ext) 
                          for ext in monitor.file_extensions):
                    return
                    
                with monitor.lock:
                    current_time = time.time()
                    # 防抖动处理
                    if current_time - monitor.last_event_time < monitor.debounce_seconds:
                        return
                    monitor.last_event_time = current_time
                    
                # 调用回调函数
                monitor.callback(event.event_type, event.src_path)
                
        return Handler()
        
    def start(self):
        """启动文件监控"""
        for directory in self.directories:
            if os.path.exists(directory):
                self.observer.schedule(self.handler, directory, recursive=True)
            else:
                print(f"Warning: Directory not found: {directory}")
                
        self.observer.start()
        
    def stop(self):
        """停止文件监控"""
        self.observer.stop()
        self.observer.join()
        
    def update_directories(self, directories: List[str]):
        """更新监控目录列表"""
        self.stop()
        self.directories = directories
        self.start()
        
    def update_extensions(self, extensions: List[str]):
        """更新监控文件类型"""
        self.file_extensions = [ext.lower() for ext in extensions] 