# PyInstaller recipe. Built automatically by build.bat - you never run this by hand.
from PyInstaller.utils.hooks import collect_submodules
import sys
sys.path.insert(0, SPECPATH)   # lets the spec import product.py
import product

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    datas=[("templates", "templates"), ("static", "static")],
    hiddenimports=["app", "licensing", "license_pub", "product", "waitress"]
                  + collect_submodules("webview") + ["clr_loader", "pythonnet"],
    excludes=["tkinter", "unittest", "pydoc"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=product.APP_NAME,
          console=False, icon="assets/icon.ico")          # console=False -> no black window
coll = COLLECT(exe, a.binaries, a.datas, name=product.APP_NAME)
