import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor, QIcon, QPixmap
from PySide6.QtCore import QByteArray
from PySide6 import QtSvg

class ThemeManager:
    _ICONS_SUBDIR = os.path.join("assets", "icons")
    _THEMES_SUBDIR = os.path.join("assets", "themes")

    DARK = {
        "bg": "#1E1F22",
        "surface": "#2B2D31",
        "text": "#DBDEE1",
        "border": "#4E5058",
    }
    LIGHT = {
        "bg": "#F2F3F5",
        "surface": "#FFFFFF",
        "text": "#313338",
        "border": "#E3E5E8",
    }

    FONT_CAPTION = 11
    FONT_BASE = 13
    FONT_HEADER = 16
    FONT_H1 = 20

    BUTTON_HEIGHT_PRIMARY = 40
    BUTTON_HEIGHT_ICON = 40

    ICON_GLYPHS = {
        "play": "M8 5v14l11-7z",
        "pause": "M6 19h4V5H6v14zm8-14v14h4V5h-4z",
        "stop": "M6 6h12v12H6z",
        "scan": ("M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 "
                 "13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 "
                 "4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 "
                 "11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"),
        "volume": ("M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05"
                   "c1.48-.73 2.5-2.25 2.5-4.02z"),
        "volume_muted": ("M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45"
                         "c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64"
                         "l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86"
                         "-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3 3 4.27 "
                         "7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 "
                         "1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 "
                         "19.73l-9-9L4.27 3zM12 4 9.91 6.09 12 8.18V4z"),
        "settings": ("M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.06-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 "
                     "l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 "
                     "h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.73,8.87 "
                     "C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.8,11.69,4.8,12s0.02,0.64,0.06,0.94l-2.03,1.58 "
                     "c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 "
                     "C9.24,21.83,9.44,22,9.68,22h3.84c0.24,0,0.43-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 "
                     "c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.49-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 "
                     "s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z")
    }

    @classmethod
    def make_icon(cls, glyph_name: str, color: str) -> QIcon:
        path_d = cls.ICON_GLYPHS.get(glyph_name)
        if not path_d:
            return QIcon()
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            f'width="48" height="48"><path fill="{color}" d="{path_d}"/></svg>'
        )
        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(svg.encode("utf-8")), "SVG")
        return QIcon(pixmap)

    _active = DARK

    @classmethod
    def colors(cls) -> dict:
        return cls._active

    @staticmethod
    def _resource_root() -> Path:
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            if sys.platform == "darwin":
                mac_resources = exe_dir.parent / "Resources"
                if mac_resources.exists():
                    return mac_resources
            return exe_dir
        return Path(__file__).resolve().parent.parent

    @classmethod
    def asset_path(cls, relative: str) -> str:
        return str(cls._resource_root() / relative)

    @classmethod
    def icon_path(cls, filename: str) -> str:
        return str(cls._resource_root() / cls._ICONS_SUBDIR / filename)

    @classmethod
    def load_icon(cls, filename: str) -> QIcon:
        path = cls.icon_path(filename)
        if os.path.exists(path):
            icon = QIcon(path)
            if not icon.isNull():
                return icon
        return QIcon()

    @classmethod
    def _load_stylesheet(cls, theme_name: str, fallback_qss: str) -> str:
        qss_path = cls._resource_root() / cls._THEMES_SUBDIR / f"{theme_name}.qss"
        try:
            if qss_path.is_file():
                text = qss_path.read_text(encoding="utf-8")
                if text.strip():
                    return text
        except OSError:
            pass
        return fallback_qss

    @classmethod
    def _typography_qss(cls) -> str:
        return (
            f'QLabel[txt="h1"] {{ font-size: {cls.FONT_H1}px; font-weight: bold; }}'
            f'QLabel[txt="h2"] {{ font-size: {cls.FONT_HEADER}px; font-weight: bold; }}'
            f'QLabel[txt="body"] {{ font-size: {cls.FONT_BASE}px; }}'
            f'QLabel[txt="caption"] {{ font-size: {cls.FONT_CAPTION}px; }}'
        )

    @classmethod
    def apply_modern_dark(cls, app: QApplication):
        cls._active = cls.DARK
        app.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(cls.DARK["bg"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(cls.DARK["text"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(cls.DARK["surface"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(cls.DARK["text"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(64, 66, 73))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(cls.DARK["text"]))
        app.setPalette(palette)

        qss = """
        QMainWindow, QWidget#sidebar { background-color: #1E1F22; }
        QWidget#card { background-color: #2B2D31; border-radius: 8px; border: 2px dashed transparent; }
        QWidget#card[class="hover"] { border: 2px dashed #5865F2; background-color: #313338; }
        QWidget#toolbar_flat { background-color: #2B2D31; border-radius: 6px; }
        QWidget#controls_panel, QWidget#bottom_btns, QWidget#multi_slider_panel { background-color: #2B2D31; border-top: 1px solid #1E1F22; }
        QWidget#video_bg { background-color: #2B2D31; }
        
        QPushButton { 
            background-color: #404249; color: #DBDEE1; 
            border: none; border-radius: 6px; 
            padding: 5px 12px; font-weight: 500; 
        }
        QPushButton:hover { background-color: #4E5058; }
        QPushButton:pressed { background-color: #313338; }
        QPushButton:disabled { background-color: #313338; color: #5C5E66; }
        
        QPushButton#primary { background-color: #23A559; color: white; font-weight: bold; }
        QPushButton#primary:hover { background-color: #1D8A4A; }
        QPushButton#action { background-color: #5865F2; color: white; }
        QPushButton#action:hover { background-color: #4752C4; }
        
        QPushButton#secondary { 
            background-color: transparent; 
            border: 1px solid #4E5058; 
            border-radius: 6px;
            padding: 4px 10px; 
            color: #DBDEE1;
        }
        QPushButton#secondary:hover { background-color: #3F4147; border: 1px solid #5865F2; }
        
        QPushButton#collapser { background-color: transparent; color: #949BA4; padding: 4px 8px; }
        QPushButton#collapser:hover { background-color: #3F4147; color: #FFFFFF; }
        
        QPushButton#player_btn { background-color: transparent; color: #FFFFFF; font-weight: bold; padding: 0px; }
        QPushButton#player_btn:hover { color: #5865F2; }
        
        QLineEdit { 
            background-color: #1E1F22; color: #FFFFFF; 
            border: 1px solid #4E5058; border-radius: 6px; 
            padding: 4px 10px; selection-background-color: #5865F2;
        }
        QLineEdit:focus { border: 1px solid #5865F2; }
        
        QCheckBox { spacing: 8px; color: #DBDEE1; }
        QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; border-radius: 4px; border: 2px solid #5865F2; background: transparent; }
        QRadioButton::indicator { border-radius: 8px; }
        QCheckBox::indicator:checked, QRadioButton::indicator:checked { background: #5865F2; border: 2px solid #5865F2; }
        
        QTreeWidget#tree { background-color: #2B2D31; border: none; outline: none; border-radius: 8px; padding: 5px; color: #DBDEE1; }
        QTreeWidget::item { padding: 4px; border-radius: 4px; }
        QTreeWidget::item:selected { background-color: #3F4147; color: white; }
        QHeaderView::section { background-color: #1E1F22; color: #949BA4; border: none; padding: 4px 8px; font-weight: bold; }
        
        QComboBox {
            background-color: transparent; color: #DBDEE1;
            border: 1px solid #4E5058; border-radius: 6px;
            padding: 4px 6px 4px 6px;
            combobox-popup: 0;
            outline: none;
        }
        QComboBox:hover { background-color: #3F4147; border: 1px solid #5865F2; }
        QComboBox:focus, QComboBox:on { border: 1px solid #5865F2; }
        QComboBox::drop-down {
            subcontrol-origin: padding; subcontrol-position: center right;
            width: 20px; border: none; background: transparent;
        }
        QComboBox::down-arrow { width: 12px; height: 12px; }
        QComboBox::down-arrow:on { top: 1px; }

        QComboBox QAbstractItemView {
            background-color: #2B2D31; color: #DBDEE1;
            border: 1px solid #4E5058; border-radius: 6px;
            padding: 4px; outline: none;
            selection-background-color: #5865F2; selection-color: #FFFFFF;
        }
        QComboBox QAbstractItemView::item {
            min-height: 26px; padding: 4px 10px;
            border: none; border-radius: 4px;
        }
        QComboBox QAbstractItemView::item:hover { background-color: #3F4147; color: #FFFFFF; }
        QComboBox QAbstractItemView::item:selected { background-color: #5865F2; color: #FFFFFF; }
        
        QLabel { color: #DBDEE1; }
        QLabel#status, QLabel#elide_label { color: #949BA4; }
        QLabel#stat_val { color: #23A559; font-weight: bold; }
        QLabel#player_time { color: #FFFFFF; font-weight: bold; }
        
        QSplitter::handle:horizontal { width: 1px; background-color: #2B2D31; }
        QSplitter::handle:vertical { height: 1px; background-color: #2B2D31; }
        QSplitter::handle:hover { background-color: #5865F2; }
        QSplitter::handle:pressed { background-color: #4752C4; }
        QProgressBar { border: none; background-color: #1E1F22; border-radius: 2px; }
        QProgressBar::chunk { background-color: #5865F2; border-radius: 2px; }
        
        QSlider { background: transparent; height: 24px; }
        QSlider::groove:horizontal { border: none; height: 4px; background: #1E1F22; border-radius: 2px; }
        QSlider::sub-page:horizontal { background: #5865F2; border-radius: 2px; }
        QSlider::handle:horizontal { background: #FFFFFF; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; border: 1px solid #1E1F22; }
        QSlider::handle:horizontal:hover { background: #4D8BFF; }
        """
        app.setStyleSheet(cls._load_stylesheet("dark", qss) + cls._typography_qss())

    @classmethod
    def apply_modern_light(cls, app: QApplication):
        cls._active = cls.LIGHT
        app.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(cls.LIGHT["bg"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(cls.LIGHT["text"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(cls.LIGHT["surface"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(cls.LIGHT["text"]))
        palette.setColor(QPalette.ColorRole.Button, QColor("#E3E5E8"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(cls.LIGHT["text"]))
        app.setPalette(palette)

        qss = """
        QMainWindow, QWidget#sidebar { background-color: #F2F3F5; }
        QWidget#card { background-color: #FFFFFF; border-radius: 8px; border: 2px dashed transparent; }
        QWidget#card[class="hover"] { border: 2px dashed #5865F2; background-color: #F2F3F5; }
        QWidget#toolbar_flat { background-color: #FFFFFF; border-radius: 6px; }
        QWidget#controls_panel, QWidget#bottom_btns, QWidget#multi_slider_panel { background-color: #FFFFFF; border-top: 1px solid #E3E5E8; }
        QWidget#video_bg { background-color: #FFFFFF; }
        
        QPushButton { 
            background-color: #E3E5E8; color: #313338; 
            border: none; border-radius: 6px; 
            padding: 5px 12px; font-weight: 500; 
        }
        QPushButton:hover { background-color: #D1D3D6; }
        QPushButton:pressed { background-color: #C1C3C6; }
        QPushButton:disabled { background-color: #E3E5E8; color: #949BA4; }
        
        QPushButton#primary { background-color: #23A559; color: white; font-weight: bold; }
        QPushButton#primary:hover { background-color: #1D8A4A; }
        QPushButton#action { background-color: #5865F2; color: white; }
        QPushButton#action:hover { background-color: #4752C4; }
        
        QPushButton#secondary { 
            background-color: transparent; 
            border: 1px solid #E3E5E8; 
            border-radius: 6px;
            padding: 4px 10px; 
            color: #313338;
        }
        QPushButton#secondary:hover { background-color: #F2F3F5; border: 1px solid #5865F2; }
        
        QPushButton#collapser { background-color: transparent; color: #949BA4; padding: 4px 8px; }
        QPushButton#collapser:hover { background-color: #E3E5E8; color: #313338; }
        
        QPushButton#player_btn { background-color: transparent; color: #313338; font-weight: bold; padding: 0px; }
        QPushButton#player_btn:hover { color: #5865F2; }
        
        QLineEdit { 
            background-color: #FFFFFF; color: #313338; 
            border: 1px solid #E3E5E8; border-radius: 6px; 
            padding: 4px 10px; selection-background-color: #5865F2;
        }
        QLineEdit:focus { border: 1px solid #5865F2; }
        
        QCheckBox { spacing: 8px; color: #313338; }
        QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; border-radius: 4px; border: 2px solid #5865F2; background: transparent; }
        QRadioButton::indicator { border-radius: 8px; }
        QCheckBox::indicator:checked, QRadioButton::indicator:checked { background: #5865F2; border: 2px solid #5865F2; }
        
        QTreeWidget#tree { background-color: #FFFFFF; border: none; outline: none; border-radius: 8px; padding: 5px; color: #313338; }
        QTreeWidget::item { padding: 4px; border-radius: 4px; }
        QTreeWidget::item:selected { background-color: #F2F3F5; color: #313338; }
        QHeaderView::section { background-color: #F2F3F5; color: #949BA4; border: none; padding: 4px 8px; font-weight: bold; }
        
        QComboBox {
            background-color: transparent; color: #313338;
            border: 1px solid #E3E5E8; border-radius: 6px;
            padding: 4px 6px 4px 6px;
            combobox-popup: 0;
            outline: none;
        }
        QComboBox:hover { background-color: #F2F3F5; border: 1px solid #5865F2; }
        QComboBox:focus, QComboBox:on { border: 1px solid #5865F2; }
        QComboBox::drop-down {
            subcontrol-origin: padding; subcontrol-position: center right;
            width: 20px; border: none; background: transparent;
        }
        QComboBox::down-arrow { width: 12px; height: 12px; }
        QComboBox::down-arrow:on { top: 1px; }

        QComboBox QAbstractItemView {
            background-color: #FFFFFF; color: #313338;
            border: 1px solid #E3E5E8; border-radius: 6px;
            padding: 4px; outline: none;
            selection-background-color: #5865F2; selection-color: #FFFFFF;
        }
        QComboBox QAbstractItemView::item {
            min-height: 26px; padding: 4px 10px;
            border: none; border-radius: 4px;
        }
        QComboBox QAbstractItemView::item:hover { background-color: #F2F3F5; color: #313338; }
        QComboBox QAbstractItemView::item:selected { background-color: #5865F2; color: #FFFFFF; }
        
        QLabel { color: #313338; }
        QLabel#status, QLabel#elide_label { color: #949BA4; }
        QLabel#stat_val { color: #23A559; font-weight: bold; }
        QLabel#player_time { color: #313338; font-weight: bold; }
        
        QSplitter::handle:horizontal { width: 1px; background-color: #E3E5E8; }
        QSplitter::handle:vertical { height: 1px; background-color: #E3E5E8; }
        QSplitter::handle:hover { background-color: #5865F2; }
        QSplitter::handle:pressed { background-color: #4752C4; }
        QProgressBar { border: none; background-color: #F2F3F5; border-radius: 2px; }
        QProgressBar::chunk { background-color: #5865F2; border-radius: 2px; }
        
        QSlider { background: transparent; height: 24px; }
        QSlider::groove:horizontal { border: none; height: 4px; background: #E3E5E8; border-radius: 2px; }
        QSlider::sub-page:horizontal { background: #5865F2; border-radius: 2px; }
        QSlider::handle:horizontal { background: #FFFFFF; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; border: 1px solid #E3E5E8; }
        QSlider::handle:horizontal:hover { background: #4D8BFF; }
        """
        app.setStyleSheet(cls._load_stylesheet("light", qss) + cls._typography_qss())

    @classmethod
    def apply_system_theme(cls, app: QApplication):
        try:
            from PySide6.QtGui import Qt
            if hasattr(Qt, 'ColorScheme'):
                if app.styleHints().colorScheme() == Qt.ColorScheme.Dark:
                    cls.apply_modern_dark(app)
                else:
                    cls.apply_modern_light(app)
                return
        except Exception:
            pass
        
        palette = app.palette()
        window_color = palette.color(QPalette.ColorRole.Window)
        if window_color.lightness() < 128:
            cls.apply_modern_dark(app)
        else:
            cls.apply_modern_light(app)
