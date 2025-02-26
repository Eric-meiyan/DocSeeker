from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                            QTreeWidgetItem, QStackedWidget, QPushButton, 
                            QWidget, QCheckBox, QLabel, QSpinBox, QComboBox,
                            QLineEdit, QFileDialog, QListWidget, QFrame)
from PyQt6.QtCore import Qt
from utils.config import Config
import os

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = Config()
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle('选项')
        self.resize(800, 600)
        
        # 主布局
        layout = QHBoxLayout()
        
        # 左侧分类树
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderHidden(True)
        self.category_tree.setFixedWidth(150)
        self.category_tree.setFrameShape(QTreeWidget.Shape.Box)
        self.category_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #a0a0a0;
                border-radius: 2px;
            }
        """)
        self.setup_category_tree()
        layout.addWidget(self.category_tree)
        
        # 右侧设置区域
        right_layout = QVBoxLayout()
        
        # 设置页面堆栈
        self.stack_widget = QStackedWidget()
        self.setup_setting_pages()
        right_layout.addWidget(self.stack_widget)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_button = QPushButton('确定')
        self.cancel_button = QPushButton('取消')
        self.apply_button = QPushButton('应用')
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.apply_button.clicked.connect(self.apply_settings)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.apply_button)
        
        right_layout.addLayout(button_layout)
        
        # 添加右侧布局到主布局
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        layout.addWidget(right_widget)
        
        self.setLayout(layout)
        
        # 连接信号
        self.category_tree.currentItemChanged.connect(self.on_category_changed)
        
    def setup_category_tree(self):
        """设置分类树"""
        # 常规
        general = QTreeWidgetItem(self.category_tree, ['常规'])
        QTreeWidgetItem(general, ['界面'])
        QTreeWidgetItem(general, ['搜索'])
        QTreeWidgetItem(general, ['结果'])
        
        # 索引
        index = QTreeWidgetItem(self.category_tree, ['索引'])
        QTreeWidgetItem(index, ['文件类型'])
        QTreeWidgetItem(index, ['索引目录'])
        QTreeWidgetItem(index, ['更新策略'])
        
        # 高级
        advanced = QTreeWidgetItem(self.category_tree, ['高级'])
        QTreeWidgetItem(advanced, ['向量模型'])
        QTreeWidgetItem(advanced, ['性能调优'])
        QTreeWidgetItem(advanced, ['调试选项'])
        
        self.category_tree.expandAll()
        
    def setup_setting_pages(self):
        """设置各个配置页面"""
        # 界面设置页
        self.ui_page = QWidget()
        ui_layout = QVBoxLayout()
        
        # 界面选项
        self.show_taskbar = QCheckBox('后台运行')
        self.show_icon = QCheckBox('显示托盘图标')
        self.real_time_search = QCheckBox('实时搜索')
        self.click_select_text = QCheckBox('点击时选中所有文字')
        
        ui_layout.addWidget(self.show_taskbar)
        ui_layout.addWidget(self.show_icon)
        ui_layout.addWidget(self.real_time_search)
        ui_layout.addWidget(self.click_select_text)
        ui_layout.addStretch()
        
        self.ui_page.setLayout(ui_layout)
        self.stack_widget.addWidget(self.ui_page)
        
        # 搜索设置页
        self.search_page = QWidget()
        search_layout = QVBoxLayout()
        
        # 搜索选项
        self.chunk_size_label = QLabel('文本块大小:')
        self.chunk_size = QSpinBox()
        self.chunk_size.setRange(128, 2048)
        self.chunk_size.setSingleStep(128)
        
        self.overlap_label = QLabel('重叠长度:')
        self.overlap = QSpinBox()
        self.overlap.setRange(0, 256)
        self.overlap.setSingleStep(32)
        
        search_layout.addWidget(self.chunk_size_label)
        search_layout.addWidget(self.chunk_size)
        search_layout.addWidget(self.overlap_label)
        search_layout.addWidget(self.overlap)
        search_layout.addStretch()
        
        self.search_page.setLayout(search_layout)
        self.stack_widget.addWidget(self.search_page)
        
        # 文件类型页
        self.file_types_page = QWidget()
        file_types_layout = QVBoxLayout()
        
        self.file_types_list = QListWidget()
        self.add_type_button = QPushButton('添加')
        self.remove_type_button = QPushButton('删除')
        
        file_types_layout.addWidget(self.file_types_list)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_type_button)
        button_layout.addWidget(self.remove_type_button)
        file_types_layout.addLayout(button_layout)
        
        self.file_types_page.setLayout(file_types_layout)
        self.stack_widget.addWidget(self.file_types_page)
        
        # 索引目录页
        self.directories_page = QWidget()
        directories_layout = QVBoxLayout()
        
        self.directories_list = QListWidget()
        self.add_dir_button = QPushButton('添加')
        self.remove_dir_button = QPushButton('删除')
        
        directories_layout.addWidget(self.directories_list)
        dir_button_layout = QHBoxLayout()
        dir_button_layout.addWidget(self.add_dir_button)
        dir_button_layout.addWidget(self.remove_dir_button)
        directories_layout.addLayout(dir_button_layout)
        
        self.directories_page.setLayout(directories_layout)
        self.stack_widget.addWidget(self.directories_page)
        
        # 向量模型页
        self.model_page = QWidget()
        model_layout = QVBoxLayout()
        
        self.model_label = QLabel('向量模型:')
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            'paraphrase-multilingual-MiniLM-L12-v2',
            'all-MiniLM-L6-v2',
            'all-mpnet-base-v2'
        ])
        
        model_layout.addWidget(self.model_label)
        model_layout.addWidget(self.model_combo)
        model_layout.addStretch()
        
        self.model_page.setLayout(model_layout)
        self.stack_widget.addWidget(self.model_page)
        
        # 添加其他页面...
        
    def on_category_changed(self, current, previous):
        """处理分类切换"""
        if not current:
            return
            
        # 根据选中项切换页面
        category = current.text(0)
        if category == '界面':
            self.stack_widget.setCurrentWidget(self.ui_page)
        elif category == '搜索':
            self.stack_widget.setCurrentWidget(self.search_page)
        elif category == '文件类型':
            self.stack_widget.setCurrentWidget(self.file_types_page)
        elif category == '索引目录':
            self.stack_widget.setCurrentWidget(self.directories_page)
        elif category == '向量模型':
            self.stack_widget.setCurrentWidget(self.model_page)
            
    def load_settings(self):
        """加载设置"""
        # 加载界面设置
        self.show_taskbar.setChecked(self.config.get_value('ui.show_taskbar', True))
        self.show_icon.setChecked(self.config.get_value('ui.show_icon', True))
        self.real_time_search.setChecked(self.config.get_value('ui.real_time_search', True))
        self.click_select_text.setChecked(self.config.get_value('ui.click_select_text', True))
        
        # 加载搜索设置
        self.chunk_size.setValue(self.config.get_value('search.chunk_size', 512))
        self.overlap.setValue(self.config.get_value('search.overlap', 50))
        
        # 加载文件类型
        self.file_types_list.clear()
        for ext in self.config.get_file_extensions():
            self.file_types_list.addItem(ext)
            
        # 加载索引目录
        self.directories_list.clear()
        for directory in self.config.get_scan_directories():
            self.directories_list.addItem(directory)
            
        # 加载模型设置
        model_name = self.config.get_value('model.name', 'paraphrase-multilingual-MiniLM-L12-v2')
        index = self.model_combo.findText(model_name)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
            
    def apply_settings(self):
        """应用设置"""
        # 保存界面设置
        self.config.set_value('ui.show_taskbar', self.show_taskbar.isChecked())
        self.config.set_value('ui.show_icon', self.show_icon.isChecked())
        self.config.set_value('ui.real_time_search', self.real_time_search.isChecked())
        self.config.set_value('ui.click_select_text', self.click_select_text.isChecked())
        
        # 保存搜索设置
        self.config.set_value('search.chunk_size', self.chunk_size.value())
        self.config.set_value('search.overlap', self.overlap.value())
        
        # 保存文件类型
        file_types = []
        for i in range(self.file_types_list.count()):
            file_types.append(self.file_types_list.item(i).text())
        self.config.set_file_extensions(file_types)
        
        # 保存索引目录
        directories = []
        for i in range(self.directories_list.count()):
            directories.append(self.directories_list.item(i).text())
        self.config.set_scan_directories(directories)
        
        # 保存模型设置
        self.config.set_value('model.name', self.model_combo.currentText())
        
        # 保存配置文件
        self.config.save_config()
        
    def accept(self):
        """确定按钮处理"""
        self.apply_settings()
        super().accept() 