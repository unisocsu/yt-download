@echo off
setlocal
if "%GITHUB_TOKEN%"=="" (
  echo Set GITHUB_TOKEN to a fine-grained token with Actions: Read and write access for unisocsu/yt-download.
  echo Example for this terminal only: set GITHUB_TOKEN=github_pat_...
  echo Then run this file again.
  pause
  exit /b 1
)
py -3 bridge.py
pause
