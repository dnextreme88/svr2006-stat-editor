# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the SVR 2006 Stat Editor.
# Build with:  pyinstaller Stat_Editor_GUI.spec --noconfirm

import os

datas = [
    ('country.txt', '.'),
    ('province.txt', '.'),
    ('weight.txt', '.'),
    ('attire.txt', '.'),
    ('height.txt', '.'),
    ('stat-editor.ico', '.'),
]

# bpe.exe is only needed for saving; include it if it is present
if os.path.exists('bpe.exe'):
    datas.append(('bpe.exe', '.'))

a = Analysis(
    ['Stat_Editor_GUI.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=['numpy', 'tkinter', 'PyQt5.QtWebEngineWidgets',
              'PyQt5.QtNetwork', 'PyQt5.QtQml', 'PyQt5.QtQuick',
              'PyQt5.QtSql', 'PyQt5.QtTest', 'PyQt5.QtBluetooth',
              'PyQt5.QtMultimedia', 'PyQt5.QtPositioning'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Stat_Editor_GUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,              # no console window (original was a console build)
    icon='stat-editor.ico',
)
