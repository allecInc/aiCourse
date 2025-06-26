@echo off
echo === 快速啟動腳本（Windows版） ===

REM 檢查.env文件
if not exist ".env" (
    echo ❌ 找不到.env文件
    echo 請先創建.env文件並設置OPENAI_API_KEY
    pause
    exit /b 1
)

REM 檢查虛擬環境
if not exist "venv" (
    echo ❌ 找不到虛擬環境
    echo 正在創建虛擬環境...
    python -m venv venv
)

REM 啟動虛擬環境
echo 啟動虛擬環境...
call venv\Scripts\activate.bat

REM 安裝依賴
echo 安裝依賴套件...
pip install -r requirements_fixed.txt

REM 檢查向量數據庫
if not exist "chroma_db" (
    echo 初始化向量數據庫...
    python setup_database.py
)

REM 啟動應用
echo 啟動課程推薦系統...
echo 請在瀏覽器中訪問: http://localhost:8501
streamlit run streamlit_app.py --server.address=0.0.0.0 --server.port=8501

pause 