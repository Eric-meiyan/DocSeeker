import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLineEdit, QPushButton, QTextEdit, QListWidget, 
                            QFileDialog, QProgressBar, QMessageBox, QLabel,
                            QApplication)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon
from typing import List, Dict
from core.search_service import SearchService
from core.workers import IndexingWorker
from utils.config import Config
from utils.file_monitor import FileMonitor
from utils.logger import Logger

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = Logger.get_logger(__name__)
        self.logger.info("初始化主窗口")
        self.config = Config()
        self.search_service = SearchService()
        self.init_ui()
        
        # # 首次运行检查
        # if self.config.is_first_run():
        #     self.show_first_run_dialog()
        
        # # 初始化文件监控
        # self.file_monitor = FileMonitor(
        #     directories=self.config.get_scan_directories(),
        #     file_extensions=self.config.get_file_extensions(),
        #     callback=self.handle_file_change
        # )
        # self.file_monitor.start()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle('DocSeeker')
        #启动后，窗口是最大化状态
        self.showMaximized()
        self.setWindowIcon(QIcon('icons/app.ico'))
        
        # 主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # 搜索区域
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('输入搜索内容...')
        self.search_button = QPushButton('搜索')
        self.search_button.clicked.connect(self.perform_search)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)
        
        # 结果显示区域
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.show_result_detail)
        layout.addWidget(self.results_list)
        
        # 详情显示区域
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        layout.addWidget(self.detail_text)
        
        # 底部工具栏
        tools_layout = QHBoxLayout()
        self.index_button = QPushButton('更新索引')
        self.index_button.clicked.connect(self.start_indexing)
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        tools_layout.addWidget(self.index_button)
        tools_layout.addWidget(self.progress_bar)
        layout.addLayout(tools_layout)
        
        # 添加状态栏
        self.statusBar().showMessage('就绪')
        
        # 添加菜单栏
        self._create_menu_bar()
        
    def show_first_run_dialog(self):
        """显示首次运行配置对话框"""
        msg = QMessageBox()
        msg.setWindowTitle("首次运行配置")
        msg.setText("欢迎使用语义文档搜索！\n请选择要索引的文档目录。")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        
        # 选择目录
        directory = QFileDialog.getExistingDirectory(self, "选择文档目录")
        if directory:
            self.config.add_scan_directory(directory)
            self.config.set_first_run(False)
            self.start_indexing()
            
    def perform_search(self):
        self.logger.info("执行搜索")
        query = self.search_input.text()
        if not query:
            self.logger.warning("搜索内容为空")
            return
            
        self.results_list.clear()
        results = self.search_service.search(query)
        
        for result in results:
            item_text = f"{os.path.basename(result['file_path'])} - {result['score']:.2f}"
            self.results_list.addItem(item_text)
            # 存储完整结果数据
            self.results_list.item(self.results_list.count() - 1).setData(Qt.ItemDataRole.UserRole, result)
            
    def show_result_detail(self, item):
        """显示结果详情"""
        result = item.data(Qt.ItemDataRole.UserRole)
        detail = f"文件: {result['file_path']}\n"
        detail += f"相关度: {result['score']:.2f}\n"
        detail += f"匹配内容:\n{result['chunk_text']}"
        self.detail_text.setText(detail)
        
    def start_indexing(self):
        """开始索引文档"""
        directories = self.config.get_scan_directories()
        if not directories:
            QMessageBox.warning(self, "警告", "请先添加要索引的目录！")
            return
            
        self.index_button.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        
        # 创建并启动索引线程
        self.index_worker = IndexingWorker(self.search_service, directories)
        self.index_worker.progress.connect(self.update_progress)
        self.index_worker.finished.connect(self.indexing_finished)
        self.index_worker.error.connect(self.indexing_error)
        self.index_worker.batch_ready.connect(self.process_index_batch)
        self.logger.info("debug：self.index_worker.batch_ready.connect(self.process_index_batch)")
        self.index_worker.start()
        print("debug：self.index_worker.start()")
        
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
        
    def indexing_finished(self):
        """索引完成处理"""
        self.index_button.setEnabled(True)
        self.progress_bar.hide()
        QMessageBox.information(self, "完成", "文档索引更新完成！")
        
    def indexing_error(self, error_msg):
        """索引错误处理"""
        self.index_button.setEnabled(True)
        self.progress_bar.hide()
        QMessageBox.critical(self, "错误", f"索引过程出错：{error_msg}")
        
    def handle_file_change(self, event_type: str, file_path: str):
        """处理文件变化事件"""
        try:
            if event_type in ['created', 'modified']:
                # 更新单个文件的索引
                self.search_service.index_document(file_path)
                self.status_bar().showMessage(f"已更新文件索引: {os.path.basename(file_path)}", 3000)
        except Exception as e:
            self.status_bar().showMessage(f"索引更新失败: {str(e)}", 5000)

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        try:
            # 保存索引
            self.search_service.save_index()
            # 停止文件监控
            if hasattr(self, 'file_monitor'):
                self.file_monitor.stop()
            event.accept()
        except Exception as e:
            print(f"关闭窗口时出错: {e}")
            event.accept()

    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        add_dir_action = file_menu.addAction('添加目录')
        add_dir_action.triggered.connect(self._add_directory)
        
        manage_dirs_action = file_menu.addAction('管理目录')
        manage_dirs_action.triggered.connect(self._manage_directories)
        
        # 添加建立索引菜单项
        index_action = file_menu.addAction('建立索引')
        index_action.triggered.connect(self._build_index)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction('退出')
        exit_action.triggered.connect(self.close)
        
        # 设置菜单
        settings_menu = menubar.addMenu('设置')
        
        file_types_action = settings_menu.addAction('文件类型')
        file_types_action.triggered.connect(self._manage_file_types)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = help_menu.addAction('关于')
        about_action.triggered.connect(self._show_about)

    def _add_directory(self):
        """添加新的扫描目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择文档目录")
        if directory:
            self.config.add_scan_directory(directory)
            self.file_monitor.update_directories(self.config.get_scan_directories())
            self.start_indexing()

    def _manage_directories(self):
        """管理扫描目录"""
        # 这里可以添加一个新的对话框来管理目录列表
        pass

    def _manage_file_types(self):
        """管理文件类型"""
        # 这里可以添加一个新的对话框来管理文件类型
        pass

    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, 
                         "关于语义文档搜索",
                         "语义文档搜索 v1.0\n\n"
                         "基于深度学习的本地文档语义搜索工具\n"
                         "支持多种文档格式，实时索引更新")

    def _build_index(self):
        self.logger.info("开始建立索引")
        try:
            directories = self.config.get_scan_directories()
            if not directories:
                self.logger.warning("未配置扫描目录")
                QMessageBox.warning(self, "警告", "请先添加要索引的目录！")
                return
                
            self.statusBar().showMessage('正在建立索引...')
            self.setEnabled(False)  # 禁用整个窗口
            
            # 直接在主线程中处理所有文件
            for directory in directories:
                for root, _, files in os.walk(directory):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in self.config.get_file_extensions()):
                            file_path = os.path.join(root, file)
                            try:
                                self.search_service.index_document(file_path)
                            except Exception as e:
                                print(f"Error processing {file}: {str(e)}")
            
            self.statusBar().showMessage('索引建立完成', 3000)
            QMessageBox.information(self, "完成", "索引建立完成！")
            
        except Exception as e:
            self.logger.error("建立索引时出错: %s", str(e))
            QMessageBox.critical(self, "错误", f"建立索引时出错：{str(e)}")
            
        finally:
            self.setEnabled(True)  # 重新启用窗口 

    def process_index_batch(self, batch: List[Dict]):
        """在主线程中处理索引批次"""
        try:
            self.search_service.vector_store.add_document_batch(batch)
        except Exception as e:
            self.logger.error(f"处理索引批次失败: {str(e)}") 