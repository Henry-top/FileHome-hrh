import sys
import os
import json
import shutil
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QSystemTrayIcon,
    QMenu, QAction, QMessageBox, QDialog, QLineEdit,
    QFormLayout, QDialogButtonBox, QFileDialog
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import (
    QIcon, QFont, QDragEnterEvent, QDropEvent,
    QColor, QPen, QPixmap, QPainter
)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文件分类设置")
        self.setModal(True)
        self.resize(560, 460)
        # 去掉问号按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # 主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(12)

        # 顶部说明文字
        info_label = QLabel("为常见文件类型选择要保存到的目标文件夹：")
        info_label.setObjectName("infoLabel")
        info_label.setWordWrap(True)
        self.layout.addWidget(info_label)

        # 文件类型设置表单
        self.form_layout = QFormLayout()
        self.form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.form_layout.setFormAlignment(Qt.AlignTop)
        self.form_layout.setHorizontalSpacing(20)
        self.form_layout.setVerticalSpacing(8)

        self.file_type_inputs = {}

        config = self.load_config()
        file_types = config.get("file_types", {})

        # 排序后显示，列表更整齐
        for file_type in sorted(file_types.keys()):
            folder_path = file_types[file_type]

            # 左侧标签：高亮显示扩展名
            label = QLabel(f".{file_type} 保存到：")
            label.setProperty("fileTypeLabel", True)

            # 输入框 + 浏览按钮
            line_edit = QLineEdit(folder_path)
            line_edit.setPlaceholderText("选择或输入一个文件夹路径")

            browse_btn = QPushButton("选择...")
            browse_btn.setFixedWidth(72)
            browse_btn.clicked.connect(lambda _, ft=file_type: self.browse_folder(ft))

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)
            row_layout.addWidget(line_edit)
            row_layout.addWidget(browse_btn)

            self.file_type_inputs[file_type] = line_edit
            self.form_layout.addRow(label, row_widget)

        self.layout.addLayout(self.form_layout)

        # 底部按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("OK")
        button_box.button(QDialogButtonBox.Cancel).setText("Cancel")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout.addWidget(button_box)

        # 明亮、高对比度样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f3f4f6;
                color: #202124;
            }
            #infoLabel {
                font-size: 13px;
                color: #202124;
            }
            QLabel[fileTypeLabel="true"] {
                font-size: 13px;
                font-weight: 600;
                color: #111111;
                min-width: 80px;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #c3c4c7;
                border-radius: 4px;
                padding: 4px 6px;
                font-size: 13px;
                color: #202124;
            }
            QLineEdit:focus {
                border-color: #1a73e8;
            }
            QPushButton {
                background-color: #e8eaed;
                border-radius: 4px;
                border: 1px solid #c3c4c7;
                padding: 4px 10px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #dde0e3;
            }
            QPushButton:pressed {
                background-color: #d2d5d9;
            }
        """)

    def browse_folder(self, file_type: str):
        """弹出文件夹选择对话框"""
        line_edit = self.file_type_inputs.get(file_type)
        if not line_edit:
            return

        current_path = line_edit.text().strip() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(
            self,
            f"选择 .{file_type} 文件要保存到的文件夹",
            current_path,
        )
        if folder:
            line_edit.setText(folder)

    def load_config(self):
        """加载配置文件，确保始终返回字典"""
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"加载配置失败: {e}")
            config = {}

        config.setdefault("file_types", {})
        return config

    def save_config(self):
        config = self.load_config()
        for file_type, line_edit in self.file_type_inputs.items():
            config["file_types"][file_type] = line_edit.text().strip()

        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)


class FileOrganizerWindow(QMainWindow):
    # 用 bit 位标记四个方向，方便组合（角落）
    LEFT = 1
    RIGHT = 2
    TOP = 4
    BOTTOM = 8

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_config()
        self.setup_tray_icon()
        self.check_first_run()

        # 缩放/拖动状态
        self.resize_margin = 8          # 边缘 8 像素触发缩放
        self.resizing = False
        self.resize_region = 0
        self.drag_position = None

    # ========== 窗口大小/位置相关 ==========

    def get_screen_size(self):
        screen = QApplication.primaryScreen()
        rect = screen.availableGeometry()
        return rect.width(), rect.height()

    def calculate_window_size(self):
        screen_width, screen_height = self.get_screen_size()
        width = min(max(int(screen_width * 0.25), 300), 500)
        height = min(max(int(screen_height * 0.2), 200), 400)
        return width, height

    def calculate_window_position(self, width, height):
        screen_width, screen_height = self.get_screen_size()
        margin = 50
        x = screen_width - width - margin
        y = screen_height - height - margin
        return x, y

    def init_ui(self):
        # 无边框 + 工具窗体 + 置顶
        flags = Qt.Tool | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint
        self.setWindowFlags(flags)

        default_width, default_height = self.calculate_window_size()
        self.setMinimumSize(300, 200)
        self.resize(default_width, default_height)

        # 标题只用于任务栏 / Alt+Tab 显示
        self.setWindowTitle("fileHome - 智能文件管家")

        central_widget = QWidget()
        central_widget.setObjectName("central_widget")
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ===== 自定义“标题栏” =====
        title_bar_widget = QWidget()
        title_bar_widget.setObjectName("title_bar_widget")
        title_layout = QHBoxLayout(title_bar_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)

        self.title_label = QLabel("fileHome")
        self.title_label.setStyleSheet("""
            QLabel {
                color: #f5f5f7;
                font-weight: 600;
                font-size: 16px;
            }
        """)

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setToolTip("隐藏到系统托盘")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #38383a;
                border: 0px;
                color: #f5f5f7;
                font-weight: 300;
                font-size: 14px;
                border-radius: 11px;
            }
            QPushButton:hover {
                background-color: #ff3b30;
                color: #ffffff;
            }
        """)
        self.close_btn.clicked.connect(self.hide_to_tray)

        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.close_btn)

        # 标题栏可拖动窗口
        def start_drag(event, win=self):
            if event.button() == Qt.LeftButton:
                win.resizing = False
                win.drag_position = event.globalPos() - win.frameGeometry().topLeft()
                event.accept()

        def move_drag(event, win=self):
            if event.buttons() & Qt.LeftButton and win.drag_position is not None and not win.resizing:
                win.move(event.globalPos() - win.drag_position)
                event.accept()

        title_bar_widget.mousePressEvent = start_drag
        title_bar_widget.mouseMoveEvent = move_drag
        self.title_label.mousePressEvent = start_drag
        self.title_label.mouseMoveEvent = move_drag

        # ===== 描述区域 =====
        app_info_layout = QHBoxLayout()
        app_info_layout.setContentsMargins(0, 4, 0, 4)

        description_label = QLabel("智能文件管家\n拖拽文件到此处自动分类")
        description_label.setAlignment(Qt.AlignCenter)
        description_label.setStyleSheet("""
            QLabel {
                color: #d1d1d6;
                font-size: 13px;
                font-weight: 400;
            }
        """)
        app_info_layout.addWidget(description_label)

        # ===== 拖拽区域 =====
        self.drop_normal_style = """
            QLabel {
                background-color: #2c2c2e;
                border: 2px dashed #3a3a3c;
                border-radius: 14px;
                color: #f5f5f7;
                padding: 32px 20px;
                font-size: 14px;
                font-weight: 500;
                min-height: 80px;
            }
        """
        self.drop_hover_style = """
            QLabel {
                background-color: #323235;
                border: 2px dashed #409cff;
                border-radius: 14px;
                color: #f5f5f7;
                padding: 32px 20px;
                font-size: 14px;
                font-weight: 500;
                min-height: 80px;
            }
        """

        self.drop_label = QLabel("📁 拖拽文件到这里")
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setStyleSheet(self.drop_normal_style)

        # ===== 设置按钮 =====
        settings_btn = QPushButton("⚙️ 设置分类规则")
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3c;
                border-radius: 8px;
                border: 0px;
                color: #f5f5f7;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #48484a;
            }
        """)
        settings_btn.clicked.connect(self.show_settings)

        # 组合布局
        layout.addWidget(title_bar_widget)
        layout.addLayout(app_info_layout)
        layout.addWidget(self.drop_label)
        layout.addWidget(settings_btn)

        central_widget.setLayout(layout)

        # 启用拖拽
        self.setAcceptDrops(True)

        # 深色苹果风样式（不透明）
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1c1c1e;
                border: 1px solid #3a3a3c;
                border-radius: 16px;
            }
            #central_widget {
                background-color: transparent;
            }
        """)

        # 尝试用 SF Pro 文本（没有则回退）
        base_font = QFont("SF Pro Text", 10)
        self.setFont(base_font)

        # 鼠标跟踪用来更新边缘光标
        self.setMouseTracking(True)
        central_widget.setMouseTracking(True)

    # ========== 配置保存/加载 ==========

    def load_config(self):
        """加载配置文件，包含窗口位置/大小/透明度"""
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                window_settings = config.get("window_settings", {})

                if window_settings.get("width") and window_settings.get("height"):
                    self.move(
                        window_settings.get("position_x", 100),
                        window_settings.get("position_y", 100),
                    )
                    self.resize(
                        window_settings.get("width", 350),
                        window_settings.get("height", 250),
                    )
                else:
                    width, height = self.calculate_window_size()
                    x, y = self.calculate_window_position(width, height)
                    self.move(x, y)
                    self.resize(width, height)

                opacity = window_settings.get("opacity", 1.0)
                self.setWindowOpacity(opacity)
                return config
        except Exception as e:
            print(f"加载配置失败: {e}")
            width, height = self.calculate_window_size()
            x, y = self.calculate_window_position(width, height)
            self.move(x, y)
            self.resize(width, height)
            self.setWindowOpacity(1.0)
            return {"file_types": {}, "window_settings": {}}

    def save_window_settings(self):
        """保存窗口设置到 config.json"""
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            config = {}

        if "window_settings" not in config:
            config["window_settings"] = {}

        config["window_settings"]["position_x"] = self.x()
        config["window_settings"]["position_y"] = self.y()
        config["window_settings"]["width"] = self.width()
        config["window_settings"]["height"] = self.height()
        config["window_settings"]["opacity"] = self.windowOpacity()

        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

    def closeEvent(self, event):
        """真正关闭窗口（例如 Alt+F4）时，顺便保存一下"""
        self.save_window_settings()
        event.accept()

    def hide_to_tray(self):
        """点击圆形 × 时，只是隐藏到托盘"""
        self.save_window_settings()
        self.hide()

    # ========== 托盘 ==========

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)

        # 简单画一个小文件夹图标
        try:
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)

            painter.setBrush(QColor(74, 144, 226))
            painter.setPen(QPen(QColor(50, 100, 180), 2))
            painter.drawRoundedRect(4, 8, 24, 20, 4, 4)

            painter.setBrush(QColor(90, 160, 240))
            painter.setPen(QPen(QColor(60, 120, 200), 1))
            painter.drawRoundedRect(8, 4, 16, 6, 2, 2)

            painter.end()
            self.tray_icon.setIcon(QIcon(pixmap))
        except Exception as e:
            print(f"创建托盘图标失败: {e}")
            try:
                self.tray_icon.setIcon(QIcon.fromTheme("folder"))
            except Exception:
                pixmap = QPixmap(16, 16)
                pixmap.fill(Qt.transparent)
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setBrush(Qt.white)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(0, 0, 16, 16)
                painter.end()
                self.tray_icon.setIcon(QIcon(pixmap))

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
        self.tray_icon.setToolTip("fileHome - 智能文件管家")
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_normal()

    def show_normal(self):
        self.show()
        self.activateWindow()

    # ========== 首次启动引导 ==========

    def set_first_run_flag(self, value: bool):
        """在配置文件中记录是否已经完成首次运行引导"""
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            config = {}

        config.setdefault("file_types", {})
        config.setdefault("window_settings", {})
        config["first_run"] = bool(value)

        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

    def show_first_run(self):
        """显示首次运行设置窗口，只在第一次启动时弹出"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("欢迎使用 fileHome")
        msg_box.setText("欢迎使用 fileHome 智能文件管家！\n\n"
                        "在开始使用前，建议先设置文件分类规则。\n"
                        "您可以为不同类型的文件指定目标文件夹。")
        msg_box.setInformativeText("是否现在进行初始设置？")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.Yes)

        result = msg_box.exec_()
        if result == QMessageBox.Yes:
            self.show_settings()

        # 不管选没选“现在设置”，只弹这一回
        self.set_first_run_flag(False)

    def check_first_run(self):
        """检查是否需要展示首次运行引导"""
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            config = {}

        first_run = config.get("first_run", True)
        if first_run:
            QTimer.singleShot(500, self.show_first_run)

    # ========== 设置窗口 ==========

    def show_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            dialog.save_config()
            self.load_config()

    def quit_application(self):
        self.tray_icon.hide()
        QApplication.quit()

    # ========== 缩放辅助（四角/四边缩放） ==========

    def _get_resize_region(self, pos):
        """
        根据鼠标在窗口中的位置判断是否在可缩放区域：
        返回一个方向标记组合，例如 LEFT|TOP 表示左上角。
        """
        margin = self.resize_margin
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()

        region = 0
        if x <= margin:
            region |= self.LEFT
        elif x >= w - margin:
            region |= self.RIGHT

        if y <= margin:
            region |= self.TOP
        elif y >= h - margin:
            region |= self.BOTTOM

        return region

    def _update_cursor(self, pos):
        """根据当前鼠标位置更新光标形状"""
        region = self._get_resize_region(pos)

        if region in (self.LEFT | self.TOP, self.RIGHT | self.BOTTOM):
            self.setCursor(Qt.SizeFDiagCursor)
        elif region in (self.RIGHT | self.TOP, self.LEFT | self.BOTTOM):
            self.setCursor(Qt.SizeBDiagCursor)
        elif region in (self.LEFT, self.RIGHT):
            self.setCursor(Qt.SizeHorCursor)
        elif region in (self.TOP, self.BOTTOM):
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.unsetCursor()

    # ========== 拖拽分类 ==========

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_label.setStyleSheet(self.drop_hover_style)

    def dragLeaveEvent(self, event):
        self.drop_label.setStyleSheet(self.drop_normal_style)

    def dropEvent(self, event: QDropEvent):
        self.drop_label.setStyleSheet(self.drop_normal_style)

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

    # ========== 鼠标事件：拖动 + 缩放 ==========

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            region = self._get_resize_region(event.pos())
            if region != 0:
                # 开始缩放
                self.resizing = True
                self.resize_region = region
                self.start_geometry = self.geometry()
                self.start_mouse_pos = event.globalPos()
            else:
                # 普通拖动窗口（非标题栏区域也可以拖）
                self.resizing = False
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # 没按键时，只更新光标样式（在边缘/角落变成缩放光标）
        if not event.buttons():
            self._update_cursor(event.pos())
            super().mouseMoveEvent(event)
            return

        if (event.buttons() & Qt.LeftButton) and self.resizing:
            # 正在缩放
            diff = event.globalPos() - self.start_mouse_pos
            geo = self.start_geometry

            x, y = geo.x(), geo.y()
            w, h = geo.width(), geo.height()
            min_w, min_h = self.minimumWidth(), self.minimumHeight()

            # 水平方向
            if self.resize_region & self.LEFT:
                new_x = x + diff.x()
                new_w = w - diff.x()
                if new_w < min_w:
                    new_x = x + (w - min_w)
                    new_w = min_w
                x, w = new_x, new_w
            elif self.resize_region & self.RIGHT:
                new_w = w + diff.x()
                if new_w < min_w:
                    new_w = min_w
                w = new_w

            # 垂直方向
            if self.resize_region & self.TOP:
                new_y = y + diff.y()
                new_h = h - diff.y()
                if new_h < min_h:
                    new_y = y + (h - min_h)
                    new_h = min_h
                y, h = new_y, new_h
            elif self.resize_region & self.BOTTOM:
                new_h = h + diff.y()
                if new_h < min_h:
                    new_h = min_h
                h = new_h

            self.setGeometry(int(x), int(y), int(w), int(h))
            event.accept()
            return

        # 没在缩放，就按原来的逻辑拖动窗口
        if (event.buttons() & Qt.LeftButton) and self.drag_position is not None:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.resizing = False
            self.resize_region = 0
        super().mouseReleaseEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 关闭主窗口不自动退出，由托盘菜单“退出”控制
    app.setQuitOnLastWindowClosed(False)

    window = FileOrganizerWindow()
    window.show()

    sys.exit(app.exec_())
