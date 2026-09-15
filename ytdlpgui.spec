# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置：pyinstaller ytdlpgui.spec
# 产物 dist/ytdlpgui.exe（单文件、无控制台，双击即用）

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("frontend", "frontend"),
        # 只打包静态注册表文件：整个目录会带入源码模式下的运行时数据
        # （config.json 含用户路径、history/presets），随 exe 分发即泄露
        ("backend/app/data/options_registry.json", "backend/app/data"),
        ("backend/app/data/options_zh.json", "backend/app/data"),
    ],
    hiddenimports=[
        "backend.app.main",
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        # pywebview 原生窗口（Windows Edge WebView2 / WinForms 宿主）
        "webview",
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
    ],
    hookspath=[],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ytdlpgui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # 双击不弹黑框；如需排错改为 True 重新打包
    icon=None,
)
