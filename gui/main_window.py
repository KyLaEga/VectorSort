import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QMessageBox, 
    QProgressBar, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QStackedWidget, QFrame
)
from PySide6.QtCore import Qt, QSettings
from gui.worker import EngineInitWorker, RouteWorker
from gui.settings_dialog import SettingsDialog
from gui.theme import ThemeManager
from gui.translations import tr

class DropZone(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("card")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        self.icon_label = QLabel()
        icon = ThemeManager.make_icon("scan", ThemeManager.colors().get("text", "#DBDEE1"))
        self.icon_label.setPixmap(icon.pixmap(64, 64))
        layout.addWidget(self.icon_label, alignment=Qt.AlignCenter)
        
        layout.addSpacing(20)
        
        self.text = QLabel(tr("dropzone_title"))
        self.text.setProperty("txt", "h1")
        layout.addWidget(self.text, alignment=Qt.AlignCenter)
        
        self.subtext = QLabel(tr("dropzone_sub"))
        self.subtext.setProperty("txt", "caption")
        layout.addWidget(self.subtext, alignment=Qt.AlignCenter)
        
        layout.addSpacing(20)
        
        self.btn_browse = QPushButton(tr("btn_browse"))
        self.btn_browse.setObjectName("primary")
        layout.addWidget(self.btn_browse, alignment=Qt.AlignCenter)
        
        self.setProperty("state", "normal")
        
    def retranslate_ui(self):
        self.text.setText(tr("dropzone_title"))
        self.subtext.setText(tr("dropzone_sub"))
        self.btn_browse.setText(tr("btn_browse"))
        icon = ThemeManager.make_icon("scan", ThemeManager.colors().get("text", "#DBDEE1"))
        self.icon_label.setPixmap(icon.pixmap(64, 64))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.setProperty("class", "hover")
            self.style().unpolish(self)
            self.style().polish(self)
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty("class", "")
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event):
        self.setProperty("class", "")
        self.style().unpolish(self)
        self.style().polish(self)
        
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path):
                self.parent().parent().parent().start_scan(path)
            else:
                QMessageBox.warning(self, tr("msg_warning"), tr("msg_drop_folder"))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("app_title"))
        self.setMinimumSize(900, 700)
        
        self.engine = None
        self.settings = QSettings("MyCompany", "NSFWFilter")
        
        # Основной виджет
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # --- Top Header ---
        header_layout = QHBoxLayout()
        self.title_label = QLabel(tr("app_title"))
        self.title_label.setProperty("txt", "h1")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.btn_settings = QPushButton()
        self.btn_settings.setObjectName("secondary")
        self.btn_settings.setIcon(ThemeManager.make_icon("settings", "#DBDEE1"))
        self.btn_settings.clicked.connect(self.open_settings)
        header_layout.addWidget(self.btn_settings)
        
        layout.addLayout(header_layout)
        layout.addSpacing(20)
        
        # --- Stacked Widget for Loading vs Main Content ---
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        # 1. Loading Screen
        loading_widget = QWidget()
        loading_layout = QVBoxLayout(loading_widget)
        loading_layout.setAlignment(Qt.AlignCenter)
        
        self.loading_label = QLabel(tr("loading_title"))
        self.loading_label.setProperty("txt", "h2")
        loading_layout.addWidget(self.loading_label, alignment=Qt.AlignCenter)
        
        self.loading_sub = QLabel(tr("loading_sub"))
        self.loading_sub.setProperty("txt", "caption")
        loading_layout.addWidget(self.loading_sub, alignment=Qt.AlignCenter)
        
        self.stack.addWidget(loading_widget)
        
        # 2. Main Content
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # Drop Zone
        self.drop_zone = DropZone()
        self.drop_zone.btn_browse.clicked.connect(self.browse_target_dir)
        content_layout.addWidget(self.drop_zone)
        
        content_layout.addSpacing(20)
        
        # Dashboard (Results Table)
        self.tree = QTreeWidget()
        self.tree.setObjectName("tree")
        self.tree.setHeaderLabels([tr("col_file"), tr("col_status"), tr("col_reason")])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        content_layout.addWidget(self.tree)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        content_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel()
        self.status_label.setProperty("txt", "caption")
        self.status_label.setVisible(False)
        content_layout.addWidget(self.status_label)
        
        self.stack.addWidget(content_widget)
        
        self.drop_zone.dropEvent = self.drop_zone_drop_event
        
        self.init_engine()

    def retranslate_ui(self):
        self.setWindowTitle(tr("app_title"))
        self.title_label.setText(tr("app_title"))
        if not self.engine:
            self.loading_label.setText(tr("loading_title"))
            self.loading_sub.setText(tr("loading_sub"))
        self.drop_zone.retranslate_ui()
        self.tree.setHeaderLabels([tr("col_file"), tr("col_status"), tr("col_reason")])

    def drop_zone_drop_event(self, event):
        self.drop_zone.setProperty("class", "")
        self.drop_zone.style().unpolish(self.drop_zone)
        self.drop_zone.style().polish(self.drop_zone)
        
        if not self.engine: return
        
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path):
                self.start_scan(path)
            else:
                QMessageBox.warning(self, tr("msg_warning"), tr("msg_drop_folder"))

    def init_engine(self):
        saved_base = self.settings.value("base_dir", "")
        
        if not saved_base or not os.path.exists(saved_base):
            reply = QMessageBox.question(
                self, tr("msg_first_run_title"), 
                tr("msg_first_run_text"),
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                d = QFileDialog.getExistingDirectory(self, tr("msg_choose_base"))
                if d:
                    saved_base = d
                    self.settings.setValue("base_dir", saved_base)
                    os.makedirs(os.path.join(saved_base, "Reference_Matrix"), exist_ok=True)
                    os.makedirs(os.path.join(saved_base, "Trash_Matrix"), exist_ok=True)
                    QMessageBox.information(self, tr("msg_setup_done_title"), tr("msg_setup_done_text"))
                else:
                    QMessageBox.warning(self, tr("msg_warning"), tr("msg_no_base_warning"))
                    saved_base = os.path.expanduser("~/NSFW_Arbitrage")
            else:
                saved_base = os.path.expanduser("~/NSFW_Arbitrage")
                
        base_dir = saved_base
        
        self.stack.setCurrentIndex(0) # Show loading
        
        self.init_worker = EngineInitWorker(base_dir)
        self.init_worker.error.connect(lambda e: QMessageBox.critical(self, tr("msg_error"), e))
        self.init_worker.finished.connect(self.on_engine_initialized)
        self.init_worker.start()

    def on_engine_initialized(self, engine):
        if engine:
            self.engine = engine
            self.stack.setCurrentIndex(1) # Show main content
        else:
            self.loading_label.setText(tr("loading_error"))
            self.loading_label.setStyleSheet("color: #ED4245;")
            self.loading_sub.setText(tr("loading_error_sub"))

    def open_settings(self):
        dlg = SettingsDialog(self, self.engine)
        dlg.exec()

    def browse_target_dir(self):
        d = QFileDialog.getExistingDirectory(self, tr("btn_browse"))
        if d:
            self.start_scan(d)

    def start_scan(self, target_dir):
        if not self.engine: return
        
        self.drop_zone.setVisible(False)
        self.tree.clear()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setVisible(True)
        self.status_label.setText(tr("status_scanning"))
        self.btn_settings.setEnabled(False)
        
        self.scan_worker = RouteWorker(self.engine, target_dir)
        self.scan_worker.progress.connect(self.update_progress)
        self.scan_worker.result.connect(self.add_tree_item)
        self.scan_worker.error.connect(lambda e: QMessageBox.critical(self, tr("msg_error"), e))
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.start()

    def update_progress(self, value, text):
        self.progress_bar.setValue(value)
        self.status_label.setText(text)

    def add_tree_item(self, filename, status, reason):
        item = QTreeWidgetItem([filename, status, reason])
        
        if status == "ACCEPTED":
            item.setForeground(1, ThemeManager.colors().get("text"))
        elif status == "REJECTED" or status == "CORRUPTED" or status == "ERROR":
            item.setForeground(1, Qt.red)
        elif status == "REVIEW":
            item.setForeground(1, Qt.yellow)
        elif status == "DUPLICATE":
            item.setForeground(1, Qt.gray)
            item.setText(2, tr("status_reason_dup"))
        elif status == "NO_AUDIO":
            item.setForeground(1, Qt.gray)
            item.setText(2, tr("status_reason_no_audio"))
            
        if "Сбой тензоризации" in reason or "ERROR" in status:
             item.setText(2, tr("status_reason_tensor_fail"))
            
        self.tree.addTopLevelItem(item)
        self.tree.scrollToItem(item)

    def on_scan_finished(self):
        self.btn_settings.setEnabled(True)
        self.drop_zone.setVisible(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(tr("status_done"))
        QMessageBox.information(self, "OK", tr("msg_scan_done"))
