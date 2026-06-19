import os
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFileDialog, QMessageBox, QProgressBar,
    QComboBox, QApplication
)
from PySide6.QtCore import Qt, QSettings, QUrl
from PySide6.QtGui import QDesktopServices
from gui.worker import SyncWorker
from gui.theme import ThemeManager
from gui.translations import tr, Translator

class SettingsDialog(QDialog):
    def __init__(self, parent=None, engine=None):
        super().__init__(parent)
        self.engine = engine
        self.setWindowTitle(tr("settings_title"))
        self.setMinimumWidth(500)
        
        self.setObjectName("card")
        self.settings = QSettings("MyCompany", "NSFWFilter")
        
        layout = QVBoxLayout(self)
        
        # Header
        self.title_label = QLabel(tr("settings_title"))
        self.title_label.setProperty("txt", "h1")
        layout.addWidget(self.title_label)
        
        layout.addSpacing(10)
        
        # Base Directory
        self.base_label = QLabel(tr("settings_base_dir"))
        self.base_label.setProperty("txt", "h2")
        layout.addWidget(self.base_label)
        
        h_layout = QHBoxLayout()
        self.base_dir_input = QLineEdit()
        self.base_dir_input.setReadOnly(True)
        
        default_base = os.path.expanduser("~/NSFW_Arbitrage")
        saved_base = self.settings.value("base_dir", default_base)
        self.base_dir_input.setText(saved_base)
        
        self.btn_browse = QPushButton(tr("settings_btn_change"))
        self.btn_browse.setObjectName("secondary")
        self.btn_browse.clicked.connect(self.browse_base)
        
        h_layout.addWidget(self.base_dir_input)
        h_layout.addWidget(self.btn_browse)
        layout.addLayout(h_layout)
        
        # Open Folder Buttons
        h_open_layout = QHBoxLayout()
        self.btn_open_ref = QPushButton(tr("settings_btn_open_ref"))
        self.btn_open_ref.setObjectName("secondary")
        self.btn_open_ref.clicked.connect(self.open_reference)
        
        self.btn_open_trash = QPushButton(tr("settings_btn_open_trash"))
        self.btn_open_trash.setObjectName("secondary")
        self.btn_open_trash.clicked.connect(self.open_trash)
        
        h_open_layout.addWidget(self.btn_open_ref)
        h_open_layout.addWidget(self.btn_open_trash)
        layout.addLayout(h_open_layout)
        
        layout.addSpacing(15)

        # Theme & Language
        appearance_layout = QHBoxLayout()
        
        # Theme
        theme_layout = QVBoxLayout()
        self.theme_label = QLabel(tr("settings_theme"))
        self.theme_label.setProperty("txt", "h2")
        theme_layout.addWidget(self.theme_label)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(tr("theme_dark"), "dark")
        self.theme_combo.addItem(tr("theme_light"), "light")
        self.theme_combo.addItem(tr("theme_system"), "system")
        
        saved_theme = self.settings.value("theme", "dark")
        index = self.theme_combo.findData(saved_theme)
        if index >= 0: self.theme_combo.setCurrentIndex(index)
        self.theme_combo.currentIndexChanged.connect(self.change_theme)
        theme_layout.addWidget(self.theme_combo)
        
        # Language
        lang_layout = QVBoxLayout()
        self.lang_label = QLabel(tr("settings_lang"))
        self.lang_label.setProperty("txt", "h2")
        lang_layout.addWidget(self.lang_label)
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(tr("lang_ru"), "ru")
        self.lang_combo.addItem(tr("lang_en"), "en")
        
        saved_lang = self.settings.value("language", "ru")
        index = self.lang_combo.findData(saved_lang)
        if index >= 0: self.lang_combo.setCurrentIndex(index)
        self.lang_combo.currentIndexChanged.connect(self.change_lang)
        lang_layout.addWidget(self.lang_combo)
        
        appearance_layout.addLayout(theme_layout)
        appearance_layout.addLayout(lang_layout)
        layout.addLayout(appearance_layout)
        
        layout.addSpacing(15)
        
        # Sync Section
        self.sync_label = QLabel(tr("settings_sync_title"))
        self.sync_label.setProperty("txt", "h2")
        layout.addWidget(self.sync_label)
        
        self.sync_desc = QLabel(tr("settings_sync_desc"))
        self.sync_desc.setProperty("txt", "caption")
        self.sync_desc.setWordWrap(True)
        layout.addWidget(self.sync_desc)
        
        self.btn_sync = QPushButton(tr("settings_btn_sync"))
        self.btn_sync.setObjectName("action")
        self.btn_sync.setIcon(ThemeManager.make_icon("scan", "#FFFFFF"))
        self.btn_sync.clicked.connect(self.run_sync)
        if not self.engine:
            self.btn_sync.setEnabled(False)
            self.btn_sync.setText(tr("settings_wait_init"))
        layout.addWidget(self.btn_sync)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.status_label.setProperty("txt", "caption")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Bottom Actions
        self.btn_close = QPushButton(tr("settings_btn_close"))
        self.btn_close.setObjectName("primary")
        self.btn_close.clicked.connect(self.accept)
        layout.addWidget(self.btn_close, alignment=Qt.AlignRight)

    def retranslate_ui(self):
        self.setWindowTitle(tr("settings_title"))
        self.title_label.setText(tr("settings_title"))
        self.base_label.setText(tr("settings_base_dir"))
        self.btn_browse.setText(tr("settings_btn_change"))
        self.btn_open_ref.setText(tr("settings_btn_open_ref"))
        self.btn_open_trash.setText(tr("settings_btn_open_trash"))
        self.theme_label.setText(tr("settings_theme"))
        self.theme_combo.setItemText(0, tr("theme_dark"))
        self.theme_combo.setItemText(1, tr("theme_light"))
        self.theme_combo.setItemText(2, tr("theme_system"))
        self.lang_label.setText(tr("settings_lang"))
        self.lang_combo.setItemText(0, tr("lang_ru"))
        self.lang_combo.setItemText(1, tr("lang_en"))
        self.sync_label.setText(tr("settings_sync_title"))
        self.sync_desc.setText(tr("settings_sync_desc"))
        self.btn_sync.setText(tr("settings_btn_sync"))
        if not self.engine:
            self.btn_sync.setText(tr("settings_wait_init"))
        self.btn_close.setText(tr("settings_btn_close"))

    def change_theme(self):
        theme_val = self.theme_combo.currentData()
        self.settings.setValue("theme", theme_val)
        app = QApplication.instance()
        if theme_val == "dark":
            ThemeManager.apply_modern_dark(app)
        elif theme_val == "light":
            ThemeManager.apply_modern_light(app)
        else:
            ThemeManager.apply_system_theme(app)

    def change_lang(self):
        lang_val = self.lang_combo.currentData()
        if lang_val != Translator._lang:
            self.settings.setValue("language", lang_val)
            Translator.set_language(lang_val)
            self.retranslate_ui()
            if hasattr(self.parent(), "retranslate_ui"):
                self.parent().retranslate_ui()

    def browse_base(self):
        d = QFileDialog.getExistingDirectory(self, tr("msg_choose_base"))
        if d:
            self.base_dir_input.setText(d)
            self.settings.setValue("base_dir", d)
            QMessageBox.information(self, tr("msg_restart_title"), tr("msg_restart_text"))

    def open_reference(self):
        base = self.base_dir_input.text()
        path = os.path.join(base, "Reference_Matrix")
        os.makedirs(path, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def open_trash(self):
        base = self.base_dir_input.text()
        path = os.path.join(base, "Trash_Matrix")
        os.makedirs(path, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def run_sync(self):
        if not self.engine: return
        self.btn_sync.setEnabled(False)
        self.btn_browse.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setVisible(True)
        self.status_label.setText(tr("status_preparing"))
        
        self.sync_worker = SyncWorker(self.engine)
        self.sync_worker.progress.connect(self.update_progress)
        self.sync_worker.error.connect(lambda e: QMessageBox.critical(self, tr("msg_error"), e))
        self.sync_worker.finished.connect(self.on_sync_finished)
        self.sync_worker.start()

    def update_progress(self, value, text):
        self.progress_bar.setValue(value)
        self.status_label.setText(text)

    def on_sync_finished(self):
        self.btn_sync.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(tr("status_done"))
        QMessageBox.information(self, "OK", tr("msg_sync_done"))
