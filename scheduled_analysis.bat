@echo off
chcp 65001 > nul

echo ============================================
echo 토스증권 자동 분석 시작: %date% %time%
echo ============================================

cd /d C:\Users\SRPOST\Projects\toss-stock

:: 가상환경 활성화 및 분석 실행
call venv\Scripts\activate.bat
python analyzer.py

echo ============================================
echo 분석 완료: %date% %time%
echo ============================================

:: 로그 저장
echo [%date% %time%] 분석 완료 >> logs\scheduler.log
