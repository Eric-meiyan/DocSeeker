import json
import os
from typing import Dict, List, Optional

class Config:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """加载配置文件"""
        default_config = {
            "scan_directories": ["D:\\test\\docs"],
            "file_extensions": [".pdf", ".docx", ".doc", ".txt", ".pptx"],
            "model_name": "paraphrase-multilingual-MiniLM-L12-v2",
            "chunk_size": 512,
            "chunk_overlap": 50,
            "index_path": "documents.db",
            "first_run": True
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 合并默认配置和加载的配置
                    default_config.update(loaded_config)
            except Exception as e:
                print(f"Error loading config: {str(e)}")
                
        return default_config
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {str(e)}")
            
    def get_scan_directories(self) -> List[str]:
        """获取扫描目录列表"""
        return self.config.get("scan_directories", [])
    
    def add_scan_directory(self, directory: str):
        """添加扫描目录"""
        if os.path.exists(directory) and directory not in self.config["scan_directories"]:
            self.config["scan_directories"].append(directory)
            self.save_config()
            
    def remove_scan_directory(self, directory: str):
        """移除扫描目录"""
        if directory in self.config["scan_directories"]:
            self.config["scan_directories"].remove(directory)
            self.save_config()
            
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