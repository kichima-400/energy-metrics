@echo off
setlocal

cd /d %~dp0

:: ログディレクトリ作成
if not exist logs mkdir logs

:: ログファイル（日付ごと）― PowerShell で環境非依存のYYYYMMDD形式を取得
for /f "tokens=*" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set TODAY=%%i
set LOGFILE=logs\collect_%TODAY%.log

echo ======================================== >> %LOGFILE% 2>&1
echo 収集開始: %date% %time% >> %LOGFILE% 2>&1
echo ======================================== >> %LOGFILE% 2>&1

:: Python仮想環境を有効化してデータ収集
call .venv\Scripts\activate.bat >> %LOGFILE% 2>&1
python run_all.py >> %LOGFILE% 2>&1
set COLLECT_RESULT=%ERRORLEVEL%

echo 収集終了: %date% %time%  (exit=%COLLECT_RESULT%) >> %LOGFILE% 2>&1

:: データに変更があればコミット・プッシュ
git diff --quiet data/
if %ERRORLEVEL% neq 0 (
    echo [GIT] 変更あり、コミット・プッシュします >> %LOGFILE% 2>&1
    git add data/ >> %LOGFILE% 2>&1
    git commit -m "chore: 自動データ収集 %date%" >> %LOGFILE% 2>&1
    git push >> %LOGFILE% 2>&1
    echo [GIT] プッシュ完了 >> %LOGFILE% 2>&1
) else (
    echo [GIT] 変更なし、スキップ >> %LOGFILE% 2>&1
)

echo 完了: %date% %time% >> %LOGFILE% 2>&1
endlocal
