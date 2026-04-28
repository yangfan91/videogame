# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/app_icon.png', 'assets'),
        ('assets/app_icon.ico', 'assets'),
        ('assets/button_check.svg', 'assets'),
        ('assets/button_play.svg', 'assets'),
        ('assets/checkbox_checked.svg', 'assets'),
        ('assets/dropdown_arrow.png', 'assets'),
        ('assets/spinbox_arrow_down.png', 'assets'),
        ('assets/spinbox_arrow_up.png', 'assets'),
        ('assets/generated/nav_console.png', 'assets/generated'),
        ('assets/generated/nav_settings.png', 'assets/generated'),
        ('assets/generated/nav_stats.png', 'assets/generated'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='电玩计时',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/app_icon.ico',
)
