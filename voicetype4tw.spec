# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('assets', 'assets'), ('soul', 'soul'), ('config.json', '.')]
binaries = []
hiddenimports = ['keyboard', 'pystray', 'PIL.Image', 'sounddevice', 'soundfile', 'pyperclip', 'zhconv', 'accelerate', 'safetensors', 'PyQt6.QtMultimedia', 'numba', 'librosa']
for pkg in ['qwen_asr', 'nagisa']:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['rthook_torch.py'],
    excludes=['mlx', 'mlx_whisper', 'mlx_qwen3_asr', 'rumps', 'tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VoiceType4TW',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VoiceType4TW',
)
