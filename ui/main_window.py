import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (QDialog, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
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
from ui.settings_dialog import SettingsDialog
from .index_manager import IndexManagerDialog
from datetime import datetime

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
        self.showMaximized()
        self.setWindowIcon(QIcon('icons/app.ico'))
        
        # 创建主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout()  # 改回垂直布局
        main_widget.setLayout(main_layout)
        
        # 搜索区域
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('输入搜索内容...')
        self.search_button = QPushButton('搜索')
        self.search_button.clicked.connect(self.perform_search)
        # 连接回车键到搜索功能
        self.search_input.returnPressed.connect(self.perform_search)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        main_layout.addLayout(search_layout)
        
        # 结果显示区域
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.show_result_detail)
        main_layout.addWidget(self.results_list)
        
        # 详情显示区域
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        main_layout.addWidget(self.detail_text)
        
        # 底部工具栏
        tools_layout = QHBoxLayout()
        self.index_button = QPushButton('更新索引')
        self.index_button.clicked.connect(self.start_indexing)
        tools_layout.addWidget(self.index_button)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        tools_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(tools_layout)
        
        # 创建菜单栏
        self._create_menu_bar()
        
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
        
        # 添加导入导出菜单
        export_action = file_menu.addAction('导出数据')
        export_action.triggered.connect(self._export_data)
        
        import_action = file_menu.addAction('导入数据')
        import_action.triggered.connect(self._import_data)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction('退出')
        exit_action.triggered.connect(self.close)
        
        # 设置菜单
        settings_menu = menubar.addMenu('设置')
        
        index_manage_action = settings_menu.addAction('索引管理') 
        index_manage_action.triggered.connect(self._index_manage)

        file_types_action = settings_menu.addAction('选项')
        file_types_action.triggered.connect(self._manage_file_types)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = help_menu.addAction('关于')
        about_action.triggered.connect(self._show_about)

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
        self.search_service.vector_store.clear_all()
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
        self.index_worker.start()
        
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
        
    def indexing_finished(self):
        """索引完成处理"""
        # 更新所有已处理目录的时间戳
        now = datetime.now()
        for directory in self.config.get_scan_directories():
            self.config.set_directory_last_update(directory, now)
        
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
                # 更新目录时间戳
                directory = os.path.dirname(file_path)
                self.config.set_directory_last_update(directory, datetime.now())
                self.statusBar().showMessage(f"已更新文件索引: {os.path.basename(file_path)}", 3000)
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
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            print("选项框确认")
        else:
            print("选项框取消")
    
    def _index_manage(self):
        """打开索引管理器"""
        dialog = IndexManagerDialog(self.search_service, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 更新文件监控
            enabled_dirs = self.search_service.get_enabled_directories()
            if hasattr(self, 'file_monitor'):
                self.file_monitor.update_directories(enabled_dirs)
            
            # 更新状态栏显示
            directories = self.search_service.get_directories()
            enabled_count = sum(1 for d in directories if d['enabled'])
            total_docs = sum(d['doc_count'] for d in directories if d['enabled'])
            self.statusBar().showMessage(
                f'已启用 {enabled_count} 个目录，共 {total_docs} 个文档', 
                3000
            )

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
            directories = self.search_service.get_directories()
            if not directories:
                self.logger.warning("未配置扫描目录")
                QMessageBox.warning(self, "警告", "请先添加要索引的目录！")
                return
                
            self.statusBar().showMessage('正在建立索引...')
            self.setEnabled(False)  # 禁用整个窗口
            
            # 直接在主线程中处理所有文件
            for directory in directories:
                for root, _, files in os.walk(directory['path']):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in self.config.get_file_extensions()):
                            file_path = os.path.join(root, file)
                            try:
                                self.search_service.index_document(file_path)
                            except Exception as e:
                                print(f"Error processing {file}: {str(e)}")
            
            # 添加更新时间戳代码
            now = datetime.now()
            for directory in directories:
                self.search_service.update_directory_status(directory['path'], last_update=now.isoformat())
            
            # 显式保存索引
            self.search_service.save_index()
            
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

    def _export_data(self):
        """导出索引和数据库"""
        try:
            export_dir = QFileDialog.getExistingDirectory(self, "选择导出目录")
            if not export_dir:
                return
            
            # 标准化路径格式
            export_dir = os.path.normpath(export_dir)
            
            # 确保目录存在
            os.makedirs(export_dir, exist_ok=True)
            
            # 提示用户正在处理
            self.statusBar().showMessage('正在导出数据...')
            self.setEnabled(False)  # 禁用界面
            
            # 生成没有中文字符的文件名
            # 可以改用时间戳或其他方式命名
            import time
            timestamp = int(time.time())
            index_path = os.path.join(export_dir, f"faiss_export_{timestamp}.index")
            db_path = os.path.join(export_dir, f"sqlite_export_{timestamp}.db")
            
            # 调用导出方法
            success = self.search_service.vector_store.export_data(index_path, db_path)
            
            if success:
                self.statusBar().showMessage('数据导出成功', 3000)
                QMessageBox.information(self, "成功", f"数据已导出到:\n{export_dir}")
            else:
                self.statusBar().showMessage('数据导出失败', 3000)
                QMessageBox.warning(self, "失败", "数据导出过程中出现错误")
        
        except Exception as e:
            self.logger.error(f"导出数据时出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"导出数据时出错：{str(e)}")
        
        finally:
            self.setEnabled(True)  # 重新启用界面

    def _import_data(self):
        """导入索引和数据库"""
        try:
            import_dir = QFileDialog.getExistingDirectory(self, "选择导入目录")
            if not import_dir:
                return
            
            index_path = os.path.join(import_dir, "faiss_export.index")
            db_path = os.path.join(import_dir, "sqlite_export.db")
            
            # 检查文件是否存在
            if not os.path.exists(index_path) or not os.path.exists(db_path):
                QMessageBox.warning(self, "文件不存在", 
                                  f"导入目录中缺少必要的文件:\n"
                                  f"{'faiss_export.index 不存在' if not os.path.exists(index_path) else ''}\n"
                                  f"{'sqlite_export.db 不存在' if not os.path.exists(db_path) else ''}")
                return
            
            # 确认导入操作
            reply = QMessageBox.question(self, '确认导入', 
                                       "导入将覆盖当前的索引和数据库，确定继续吗？", 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                       QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.No:
                return
            
            self.statusBar().showMessage('正在导入数据...')
            self.setEnabled(False)  # 禁用界面
            
            # 调用vector_store的导入方法
            success = self.search_service.vector_store.import_data(index_path, db_path)
            
            if success:
                self.statusBar().showMessage('数据导入成功', 3000)
                QMessageBox.information(self, "成功", "数据导入成功")
            else:
                self.statusBar().showMessage('数据导入失败', 3000)
                QMessageBox.warning(self, "失败", "数据导入过程中出现错误")
            
        except Exception as e:
            self.logger.error(f"导入数据时出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"导入数据时出错：{str(e)}")
            
        finally:
            self.setEnabled(True)  # 重新启用界面 