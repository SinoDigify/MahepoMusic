# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['obfuscated\\music_downloader_v2.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('obfuscated\\pyarmor_runtime_000000', 'pyarmor_runtime_000000'),
        ('使用说明.txt', '.'),
        ('chrome_bundle\\chrome-win64', 'chrome-win64'),
        ('chrome_bundle\\chromedriver-win64', 'chromedriver-win64')
    ],
    hiddenimports=['pyperclip', 'selenium', 'selenium.webdriver', 'selenium.webdriver.chrome.options', 'selenium.webdriver.chrome.service', 'selenium.webdriver.common.by', 'selenium.webdriver.support.ui', 'selenium.webdriver.support.expected_conditions', 'selenium.common.exceptions'],
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
    name='music_downloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
