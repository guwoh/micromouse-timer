from pathlib import Path


project_root = Path(SPEC).resolve().parent.parent

a = Analysis(
    [str(project_root / "app" / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / "config" / "default.yaml"), "config"),
        (str(project_root / "assets"), "assets"),
        (str(project_root / "samples" / "mock_run_real.mp4"), "samples"),
        (str(project_root / "samples" / "mock_run.mp4"), "samples"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MicromouseTimer",
    icon=str(project_root / "assets" / "icons" / "micromouse.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="MicromouseTimer",
)
