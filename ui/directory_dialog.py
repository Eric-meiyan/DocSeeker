class DirectoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vector_store = VectorStore()  # 用于操作directories表
        self.init_ui()
        
    def load_directories(self):
        """从数据库加载目录列表"""
        with self.vector_store.db_lock:
            cursor = self.vector_store.conn.cursor()
            cursor.execute('SELECT path, enabled FROM directories ORDER BY path')
            directories = cursor.fetchall()
            
        self.directory_list.clear()
        for path, enabled in directories:
            item = QListWidgetItem(path)
            item.setCheckState(Qt.Checked if enabled else Qt.Unchecked)
            self.directory_list.addItem(item)
    
    def save_directories(self):
        """保存目录列表到数据库"""
        with self.vector_store.db_lock:
            cursor = self.vector_store.conn.cursor()
            try:
                cursor.execute('BEGIN TRANSACTION')
                
                # 更新所有目录的状态
                for i in range(self.directory_list.count()):
                    item = self.directory_list.item(i)
                    path = item.text()
                    enabled = item.checkState() == Qt.Checked
                    
                    cursor.execute('''
                    INSERT OR REPLACE INTO directories (path, enabled)
                    VALUES (?, ?)
                    ''', (path, enabled))
                
                cursor.execute('COMMIT')
            except Exception as e:
                cursor.execute('ROLLBACK')
                raise
    
    def add_directory(self):
        """添加新目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择目录")
        if directory:
            # 检查是否已存在
            for i in range(self.directory_list.count()):
                if self.directory_list.item(i).text() == directory:
                    QMessageBox.warning(self, "警告", "该目录已存在！")
                    return
                    
            # 添加新目录
            item = QListWidgetItem(directory)
            item.setCheckState(Qt.Checked)  # 默认启用
            self.directory_list.addItem(item)
    
    def remove_directory(self):
        """移除选中的目录"""
        current_item = self.directory_list.currentItem()
        if current_item:
            directory = current_item.text()
            reply = QMessageBox.question(
                self, 
                "确认删除", 
                f"确定要删除目录 {directory} 吗？\n这将同时删除该目录的所有索引数据。",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 从数据库和FAISS中删除目录数据
                try:
                    self.vector_store.clear_directory(directory)
                    # 从列表中移除
                    self.directory_list.takeItem(self.directory_list.row(current_item))
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"删除目录失败：{str(e)}") 