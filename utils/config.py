import json
import os
from typing import Dict, List, Optional
from datetime import datetime

class Config:
    def __init__(self):
        self.config_file = "config.json"
        self.default_config = {
            "file_extensions": [".pdf", ".docx", ".doc", ".txt", ".pptx"],
            "model_name": "paraphrase-multilingual-MiniLM-L12-v2",
            "chunk_size": 512,
            "chunk_overlap": 50,
            "index_path": "documents.db",
            "first_run": True
        }
        # 移除 scan_directories 配置项
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception as e:
                self.config = self.default_config.copy()
        else:
            self.config = self.default_config.copy()
        
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {str(e)}")
            
    def get_file_extensions(self) -> List[str]:
        """获取支持的文件扩展名"""
        return self.config.get("file_extensions", [])
    
    def set_file_extensions(self, extensions: List[str]):
        """设置支持的文件扩展名"""
        self.config["file_extensions"] = extensions
        self.save_config()
        
    def get_model_name(self) -> str:
        """获取模型名称"""
        return self.config.get("model_name", "paraphrase-multilingual-MiniLM-L12-v2")
    
    def set_model_name(self, model_name: str):
        """设置模型名称"""
        self.config["model_name"] = model_name
        self.save_config()
        
    def is_first_run(self) -> bool:
        """检查是否首次运行"""
        return self.config.get("first_run", True)
    
    def set_first_run(self, value: bool):
        """设置首次运行标志"""
        self.config["first_run"] = value
        self.save_config()
        
    def get_value(self, key: str, default=None):
        """获取配置值"""
        keys = key.split('.')
        value = self.config
        try:
            for k in keys:
                value = value[k]
            return value
        except:
            return default
        
    def set_value(self, key: str, value):
        """设置配置值"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def get_directory_settings(self, directory: str) -> Dict:
        """获取目录的完整设置"""
        if "directory_settings" not in self.config:
            self.config["directory_settings"] = {}
            
        if directory not in self.config["directory_settings"]:
            self.config["directory_settings"][directory] = {
                "enabled": True,
                "last_update": None,
                "doc_count": 0
            }
            
        return self.config["directory_settings"][directory]
        
    def set_directory_settings(self, directory: str, settings: Dict):
        """设置目录的完整设置"""
        if "directory_settings" not in self.config:
            self.config["directory_settings"] = {}
            
        self.config["directory_settings"][directory] = settings
        self.save_config()
        
    def is_directory_enabled(self, directory: str) -> bool:
        """检查目录是否启用"""
        settings = self.get_directory_settings(directory)
        return settings.get("enabled", True)
        
    def set_directory_enabled(self, directory: str, enabled: bool):
        """设置目录启用状态"""
        settings = self.get_directory_settings(directory)
        settings["enabled"] = enabled
        self.set_directory_settings(directory, settings)
        
    def get_directory_last_update(self, directory: str) -> Optional[datetime]:
        """获取目录的最后更新时间"""
        settings = self.get_directory_settings(directory)
        last_update = settings.get("last_update")
        if isinstance(last_update, str):
            return datetime.strptime(last_update, "%Y-%m-%d %H:%M:%S")
        return None
        
    def set_directory_last_update(self, directory: str, timestamp: Optional[datetime]):
        """设置目录的最后更新时间"""
        settings = self.get_directory_settings(directory)
        settings["last_update"] = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else None
        self.set_directory_settings(directory, settings)
        
    def set_directory_doc_count(self, directory: str, count: int):
        """设置目录的文档数量"""
        settings = self.get_directory_settings(directory)
        settings["doc_count"] = count
        self.set_directory_settings(directory, settings)
        
    def get_index_status(self) -> Dict:
        """获取索引状态信息"""
        if "index_status" not in self.config:
            self.config["index_status"] = {
                "last_full_update": None,
                "total_documents": 0,
                "total_chunks": 0
            }
        return self.config["index_status"]

    def update_index_status(self, status: Dict):
        """更新索引状态信息"""
        self.config["index_status"] = status
        self.save_config()

    def get_enabled_directories(self) -> List[str]:
        """获取所有启用的目录"""
        return [d for d in self.get_scan_directories() 
                if self.is_directory_enabled(d)] 