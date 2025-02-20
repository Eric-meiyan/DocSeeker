"""
日志工具模块，提供统一的日志记录功能
"""

import logging
import os
from datetime import datetime

class Logger:
    """
    日志管理器
    提供统一的日志记录接口
    """
    
    _loggers = {}  # 用于缓存已创建的logger
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """
        获取指定名称的logger
        
        Args:
            name: logger名称，通常使用模块名
            
        Returns:
            配置好的logger实例
        """
        if name in Logger._loggers:
            return Logger._loggers[name]
            
        # 创建logger
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        
        # 确保日志目录存在
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # 创建文件处理器
        current_date = datetime.now().strftime("%Y%m%d")
        file_handler = logging.FileHandler(
            os.path.join(log_dir, f"{current_date}.log"),
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # 缓存logger
        Logger._loggers[name] = logger
        
        return logger 