' Launches the Redmi Watch Live service hidden (no console window).
Set sh = CreateObject("WScript.Shell")
appdir = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%\RedmiWatchLive")
pyw = "D:\MyProjectWatch\redmi-watch-live\redmi-watch-live\.venv\Scripts\pythonw.exe"
sh.CurrentDirectory = appdir
sh.Run """" & pyw & """ """ & appdir & "\service.py""", 0, False