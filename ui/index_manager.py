from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                            QTreeWidgetItem, QPushButton, QFileDialog,
                            QMessageBox, QHeaderView)
from PyQt6.QtCore import Qt
from datetime import datetime
import os
from utils.config import Config
from core.search_service import SearchService

class IndexManagerDialog(QDialog):
    def __init__(self, search_service: SearchService, parent=None):
        super().__init__(parent)
        self.search_service = search_service
        self.config = Config()
        self.init_ui()
        self.load_directories()
        
        # 跟踪目录状态变化
        self.dir_tree.itemChanged.connect(self.on_item_changed)
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle('索引管理')
        self.resize(800, 500)
        
        layout = QVBoxLayout()
        
        # 目录列表
        self.dir_tree = QTreeWidget()
        self.dir_tree.setHeaderLabels(['目录', '文档数量', '上次更新时间', '状态'])
        self.dir_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.dir_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.dir_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.dir_tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.dir_tree)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton('添加目录')
        self.remove_button = QPushButton('删除目录')
        self.refresh_button = QPushButton('刷新索引')
        self.rebuild_button = QPushButton('重建索引')
        
        self.add_button.clicked.connect(self.add_directory)
        self.remove_button.clicked.connect(self.remove_directory)
        self.refresh_button.clicked.connect(self.refresh_index)
        self.rebuild_button.clicked.connect(self.rebuild_index)
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.rebuild_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        self.ok_button = QPushButton('确定')
        self.cancel_button = QPushButton('取消')
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        bottom_layout.addWidget(self.ok_button)
        bottom_layout.addWidget(self.cancel_button)
        
        layout.addLayout(bottom_layout)
        
        self.setLayout(layout)
        
    def load_directories(self):
        """加载目录列表"""
        self.dir_tree.clear()
        
        for directory in self.search_service.get_directories():
            item = QTreeWidgetItem()
            item.setText(0, directory['path'])
            
            # 设置目录状态
            enabled = directory['enabled']
            item.setCheckState(0, Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
            
            # 获取目录信息
            doc_count = self.get_document_count(directory['path'])
            self.search_service.update_directory_status(
                directory['path'], 
                doc_count=doc_count
            )
            
            last_update = directory['last_update']
            if last_update:
                last_update = datetime.strptime(last_update, "%Y-%m-%d %H:%M:%S")
            status = "已启用" if enabled else "已禁用"
            
            item.setText(1, str(doc_count))
            item.setText(2, last_update.strftime("%Y-%m-%d %H:%M:%S") if last_update else "从未")
            item.setText(3, status)
            
            self.dir_tree.addTopLevelItem(item)
        
    def get_document_count(self, directory: str) -> int:
        """获取目录中的文档数量"""
        count = 0
        for root, _, files in os.walk(directory):
            count += sum(1 for f in files if any(f.lower().endswith(ext) 
                        for ext in self.config.get_file_extensions()))
        return count
        
    def add_directory(self):
        """添加新目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择文档目录")
        if directory:
            # 检查是否已存在
            existing = self.search_service.get_directories()
            if any(d['path'] == directory for d in existing):
                QMessageBox.warning(self, "警告", "该目录已存在！")
                return
                
            self.search_service.add_directory(directory)
            self.load_directories()
            
    def remove_directory(self):
        """删除选中的目录"""
        current_item = self.dir_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择要删除的目录！")
            return
            
        directory = current_item.text(0)
        reply = QMessageBox.question(self, '确认删除', 
                                   f"确定要删除目录 {directory} 吗？\n"
                                   "该操作不会删除目录中的文件，但会删除相关的索引。",
                                   QMessageBox.StandardButton.Yes | 
                                   QMessageBox.StandardButton.No,
                                   QMessageBox.StandardButton.No)
                                   
        if reply == QMessageBox.StandardButton.Yes:
            self.search_service.remove_directory(directory)
            self.load_directories()
            
    def refresh_index(self):
        """刷新选中目录的索引"""
        current_item = self.dir_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择要刷新的目录！")
            return
            
        directory = current_item.text(0)
        try:
            # 更新索引
            self.search_service.index_directory(directory)
            # 更新时间戳
            self.search_service.update_directory_status(directory, last_update=datetime.now().isoformat())
            self.load_directories()
            QMessageBox.information(self, "完成", f"目录 {directory} 的索引已更新！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"更新索引时出错：{str(e)}")
            
    def rebuild_index(self):
        """重建所有索引"""
        reply = QMessageBox.question(self, '确认重建', 
                                   "确定要重建所有索引吗？\n"
                                   "该操作可能需要较长时间。",
                                   QMessageBox.StandardButton.Yes | 
                                   QMessageBox.StandardButton.No,
                                   QMessageBox.StandardButton.No)
                                   
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.search_service.rebuild_index()
                # 更新所有目录的时间戳
                now = datetime.now()
                for directory in self.search_service.get_directories():
                    self.search_service.update_directory_status(directory['path'], last_update=now.isoformat())
                self.load_directories()
                QMessageBox.information(self, "完成", "索引重建完成！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"重建索引时出错：{str(e)}")

    def on_item_changed(self, item: QTreeWidgetItem, column: int):
        """处理目录项状态变化"""
        if column == 0:  # 复选框状态改变
            directory = item.text(0)
            enabled = item.checkState(0) == Qt.CheckState.Checked
            self.search_service.update_directory_status(directory, enabled=enabled)
            item.setText(3, "已启用" if enabled else "已禁用")
            
    def accept(self):
        """确定按钮处理"""
        try:
            # 保存所有目录的状态
            for i in range(self.dir_tree.topLevelItemCount()):
                item = self.dir_tree.topLevelItem(i)
                directory = item.text(0)
                enabled = item.checkState(0) == Qt.CheckState.Checked
                self.search_service.update_directory_status(directory, enabled=enabled)
            
            # 保存配置
            self.config.save_config()
            super().accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置时出错：{str(e)}")

    def check_index_health(self):
        """检查索引健康状态"""
        try:
            # 检查FAISS索引和数据库的一致性
            if not self.search_service.vector_store.check_consistency():
                reply = QMessageBox.question(
                    self, 
                    "索引不一致", 
                    "检测到索引数据不一致，是否要修复？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.rebuild_index()
                    return
                    
            # 检查文件实际存在性
            for directory in self.search_service.get_directories():
                if not os.path.exists(directory['path']):
                    QMessageBox.warning(
                        self,
                        "目录不存在",
                        f"目录不存在: {directory['path']}\n建议从索引中移除此目录。"
                    )
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"检查索引健康状态时出错：{str(e)}") 