@echo off
call C:\ProgramData\Anaconda3\Scripts\activate.bat young
cd /d "%~dp0image_analyzer"
python main.py
pause
