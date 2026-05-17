@echo off
echo Building LAN Chat Client...
python -m PyInstaller client.spec --clean -y
echo Done.
pause
