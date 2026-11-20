@echo off
where py >nul 2>nul
if errorlevel 1 (
  python "%~dp0patch.py" apply --game-dir "%~dp0.."
) else (
  py -3 "%~dp0patch.py" apply --game-dir "%~dp0.."
)
pause
