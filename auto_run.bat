@echo off
chcp 65001 > nul
echo [%date% %time%] 분석 시작...

cd /d C:\Users\SRPOST\Projects\toss-stock
call venv\Scripts\activate.bat
python analyzer.py

echo [%date% %time%] 완료!
pause
