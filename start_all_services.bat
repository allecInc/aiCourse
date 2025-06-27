@echo off
REM AI課程推薦系統 - 服務啟動器 (Windows)
echo.
echo 🤖 AI課程推薦系統 - 服務啟動器
echo 同時啟動API服務 (FastAPI) 和網頁服務 (Streamlit)
echo ====================================================================
echo.

REM 檢查Python是否安裝
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Python，請先安裝Python
    pause
    exit /b 1
)

REM 檢查必要檔案
if not exist "api_server.py" (
    echo ❌ 缺少 api_server.py 檔案
    pause
    exit /b 1
)

if not exist "streamlit_app.py" (
    echo ❌ 缺少 streamlit_app.py 檔案
    pause
    exit /b 1
)

echo ✅ 環境檢查通過
echo.

REM 創建新的命令提示符視窗來啟動API服務
echo 🚀 正在啟動API服務...
start "AI課程推薦API服務" cmd /k "python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload"

REM 等待2秒
timeout /t 2 /nobreak >nul

REM 創建新的命令提示符視窗來啟動Streamlit服務
echo 🚀 正在啟動Streamlit網頁服務...
start "AI課程推薦網頁服務" cmd /k "python -m streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0"

REM 等待服務啟動
echo.
echo ⏳ 等待服務啟動中...
timeout /t 5 /nobreak >nul

echo.
echo ====================================================================
echo ✅ 所有服務已啟動！
echo.
echo 🌐 服務網址:
echo    • API服務:        http://localhost:8000
echo    • API文檔:        http://localhost:8000/docs
echo    • 網頁介面:       http://localhost:8501
echo    • 健康檢查:       http://localhost:8000/health
echo.
echo 💡 提示:
echo    • 兩個服務會在分別的命令提示符視窗中運行
echo    • 關閉對應的命令提示符視窗即可停止服務
echo    • 或在各視窗中按 Ctrl+C 停止服務
echo ====================================================================
echo.

REM 詢問是否要開啟瀏覽器
set /p OPEN_BROWSER="是否要自動開啟瀏覽器? (y/n): "
if /i "%OPEN_BROWSER%"=="y" (
    echo 🌐 正在開啟瀏覽器...
    start http://localhost:8501
    start http://localhost:8000/docs
)

echo.
echo 按任意鍵結束此視窗...
pause >nul 