# -*- mode: python ; coding: utf-8 -*-

# 快速启动优化配置
block_cipher = None

a = Analysis(
    ['music_downloader_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('使用说明.txt', '.'),
        ('chrome_bundle\\chrome-win64', 'chrome-win64'),
        ('chrome_bundle\\chromedriver-win64', 'chromedriver-win64')
    ],
    hiddenimports=['pyperclip', 'selenium', 'selenium.webdriver', 'selenium.webdriver.chrome.options', 'selenium.webdriver.chrome.service', 'selenium.webdriver.common.by', 'selenium.webdriver.support.ui', 'selenium.webdriver.support.expected_conditions', 'selenium.common.exceptions'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL',
        'pytest', 'setuptools', 'wheel', 'pip',
        'pydoc', 'doctest', 'asyncio'
    ],
    noarchive=False,
    optimize=2,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='马赫坡音乐',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=False,
    upx_exclude=[],
    name='马赫坡音乐',
)
