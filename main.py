import sys
import os
import json
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QSystemTrayIcon,
                             QMenu, QAction, QMessageBox, QDialog, QLineEdit,
                             QFormLayout, QDialogButtonBox)
from PyQt5.QtCore import Qt, QTimer, QSettings
from PyQt5.QtGui import QIcon, QFont, QDragEnterEvent, QDropEvent

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文件分类设置")
        self.setModal(True)
        self.resize(400, 300)
        
        self.layout = QVBoxLayout()
        
        # 文件类型设置表单
        self.form_layout = QFormLayout()
        
        self.file_type_inputs = {}
        config = self.load_config()
        
        for file_type, folder_path in config.get("file_types", {}).items():
            line_edit = QLineEdit(folder_path)
            self.file_type_inputs[file_type] = line_edit
            self.form_layout.addRow(f".{file_type} 文件夹:", line_edit)
        
        self.layout.addLayout(self.form_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout.addWidget(button_box)
        
        self.setLayout(self.layout)
    
    def load_config(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"file_types": {}}
    
    def save_config(self):
        config = self.load_config()
        for file_type, line_edit in self.file_type_inputs.items():
            config["file_types"][file_type] = line_edit.text()
        
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

class FileOrganizerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_config()
        self.setup_tray_icon()
        
    def init_ui(self):
        # 设置窗口属性 - 移除无边框设置
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, False)  # 移除透明背景
        
        # 设置最小大小
        self.setMinimumSize(200, 150)
        
        # 主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 布局
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 标题栏
        title_bar = QHBoxLayout()
        self.title_label = QLabel("fileHome")
        self.title_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-weight: 600;
                font-size: 14px;
                padding: 2px 0px;
            }
        """)
        
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(18, 18)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: rgba(255, 255, 255, 0.8);
                font-weight: 300;
                font-size: 12px;
                border-radius: 9px;
            }
            QPushButton:hover {
                background-color: rgba(255, 59, 48, 0.8);
                border-color: rgba(255, 59, 48, 0.9);
            }
        """)
        self.close_btn.clicked.connect(self.hide_to_tray)
        
        title_bar.addWidget(self.title_label)
        title_bar.addStretch()
        title_bar.addWidget(self.close_btn)
        
        # 拖拽区域
        self.drop_label = QLabel("拖拽文件到这里进行分类")
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1.5px dashed rgba(255, 255, 255, 0.3);
                border-radius: 12px;
                color: rgba(255, 255, 255, 0.8);
                padding: 25px 15px;
                font-size: 13px;
                font-weight: 400;
            }
        """)
        self.drop_label.setMinimumSize(150, 80)
        
        layout.addLayout(title_bar)
        layout.addWidget(self.drop_label)
        
        central_widget.setLayout(layout)
        
        # 启用拖拽
        self.setAcceptDrops(True)
        
        # 设置窗口样式 - 苹果风格毛玻璃效果
        self.setStyleSheet("""
            QMainWindow {
                background-color: rgba(30, 30, 30, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
            }
            QMainWindow::separator {
                background-color: rgba(255, 255, 255, 0.1);
                height: 1px;
            }
        """)
    
    def load_config(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                window_settings = config.get("window_settings", {})
                
                # 设置窗口位置和大小
                self.move(window_settings.get("position_x", 100), 
                         window_settings.get("position_y", 100))
                self.resize(window_settings.get("width", 200), 
                           window_settings.get("height", 100))
                
                # 设置透明度
                opacity = window_settings.get("opacity", 0.8)
                self.setWindowOpacity(opacity)
                
        except Exception as e:
            print(f"加载配置失败: {e}")
    
    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        show_action = QAction("显示窗口", self)
        show_action.triggered.connect(self.show_normal)
        
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.show_settings)
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_application)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(settings_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("fileHome")
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
    
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_normal()
    
    def show_normal(self):
        self.show()
        self.activateWindow()
    
    def hide_to_tray(self):
        self.hide()
    
    def show_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            dialog.save_config()
            self.load_config()
    
    def quit_application(self):
        self.tray_icon.hide()
        QApplication.quit()
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(64, 156, 255, 0.2);
                    border: 1.5px dashed rgba(64, 156, 255, 0.6);
                    border-radius: 12px;
                    color: rgba(255, 255, 255, 0.9);
                    padding: 25px 15px;
                    font-size: 13px;
                    font-weight: 400;
                }
            """)
    
    def dragLeaveEvent(self, event):
        self.drop_label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1.5px dashed rgba(255, 255, 255, 0.3);
                border-radius: 12px;
                color: rgba(255, 255, 255, 0.8);
                padding: 25px 15px;
                font-size: 13px;
                font-weight: 400;
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        self.drop_label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1.5px dashed rgba(255, 255, 255, 0.3);
                border-radius: 12px;
                color: rgba(255, 255, 255, 0.8);
                padding: 25px 15px;
                font-size: 13px;
                font-weight: 400;
            }
        """)
        
        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                self.organize_file(file_path)
        
        event.acceptProposedAction()
    
    def organize_file(self, file_path):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            
            file_types = config.get("file_types", {})
            file_extension = os.path.splitext(file_path)[1].lower().lstrip('.')
            
            if file_extension in file_types:
                target_folder = file_types[file_extension]
                
                # 确保目标文件夹存在
                os.makedirs(target_folder, exist_ok=True)
                
                # 移动文件
                file_name = os.path.basename(file_path)
                target_path = os.path.join(target_folder, file_name)
                
                # 如果目标文件已存在，添加序号
                counter = 1
                base_name, ext = os.path.splitext(file_name)
                while os.path.exists(target_path):
                    target_path = os.path.join(target_folder, f"{base_name}_{counter}{ext}")
                    counter += 1
                
                shutil.move(file_path, target_path)
                
                # 显示成功消息
                self.tray_icon.showMessage(
                    "文件分类成功",
                    f"已将 {file_name} 移动到 {target_folder}",
                    QSystemTrayIcon.Information,
                    2000
                )
            else:
                self.tray_icon.showMessage(
                    "未知文件类型",
                    f"未找到 .{file_extension} 文件的分类规则",
                    QSystemTrayIcon.Warning,
                    2000
                )
                
        except Exception as e:
            self.tray_icon.showMessage(
                "分类失败",
                f"处理文件时出错: {str(e)}",
                QSystemTrayIcon.Critical,
                2000
            )
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, 'drag_position'):
            self.move(event.globalPos() - self.drag_position)
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    window = FileOrganizerWindow()
    window.show()
    
    sys.exit(app.exec_())
