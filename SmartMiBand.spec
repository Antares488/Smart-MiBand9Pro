# Build on Windows: pyinstaller --clean --noconfirm SmartMiBand.spec
from PyInstaller.utils.hooks import collect_submodules

a = Analysis(['windows_app.py'], pathex=[],
    datas=[('config.example.json', '.'), ('index.dc.html', '.'),
           ('pulse.html', '.'), ('support.js', '.'), ('vendor', 'vendor')],
    hiddenimports=collect_submodules('serial.tools') + ['pystray._win32'],
    hookspath=[], runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='SmartMiBand',
          debug=False, strip=False, upx=False, console=False)
