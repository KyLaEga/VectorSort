# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules
import sys
import os

block_cipher = None

# Collect hidden imports for all ML libs
hidden_imports = []
hidden_imports += ['transformers.models.siglip', 'transformers.models.ast']
hidden_imports += ['PIL._tkinter_finder', 'faiss', 'librosa', 'soundfile']

excludes = ['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtNetwork', 'PySide6.QtQml', 'PySide6.QtSql', 'matplotlib', 'notebook', 'IPython', 'pytest', 'tkinter', 'scipy']

# Collect data files
datas = []
# Package UI icons/themes if they exist physically (though they are generated in code)
# we still add assets just in case
assets_path = 'assets'
if os.path.exists(assets_path):
    datas.append((assets_path, 'assets'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VectorSort',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # Set to False to hide the console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='NONE', # Can be set to a .ico / .icns later
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VectorSort',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='VectorSort.app',
        icon=None,
        bundle_identifier='com.kylaega.vectorsort',
    )
