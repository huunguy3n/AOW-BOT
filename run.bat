@echo off
setlocal
cd /d %~dp0
rem P13g-1: khong thua huong PYTHONPATH tro toi thu muc / worktree khac (26/11 09:17 nap nham aowbot cu)
set "PYTHONPATH="
start "" http://localhost:8080
python main.py --web --auto-all %*
pause
