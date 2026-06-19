import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
from gui.main_window import MainWindow
from gui.theme import ThemeManager
from gui.translations import Translator

def main():
    if hasattr(sys, 'frozen'):
        os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
        
    app = QApplication(sys.argv)
    
    settings = QSettings("MyCompany", "NSFWFilter")
    
    # Загружаем язык
    lang = settings.value("language", "ru")
    Translator.set_language(lang)
    
    # Загружаем тему
    theme = settings.value("theme", "dark")
    if theme == "dark":
        ThemeManager.apply_modern_dark(app)
    elif theme == "light":
        ThemeManager.apply_modern_light(app)
    else:
        ThemeManager.apply_system_theme(app)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
