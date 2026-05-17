@echo off
echo Building LAN Chat Server...
python -m PyInstaller server.spec --clean -y
echo Done.
pause
