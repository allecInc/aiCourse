#!/bin/bash

echo "=== 快速啟動腳本 ==="

# 檢查.env文件
if [ ! -f ".env" ]; then
    echo "❌ 找不到.env文件"
    echo "請先創建.env文件並設置OPENAI_API_KEY"
    exit 1
fi

# 檢查虛擬環境
if [ ! -d "venv" ]; then
    echo "❌ 找不到虛擬環境"
    echo "請先執行 ./manual_deploy.sh 進行完整部署"
    exit 1
fi

# 啟動虛擬環境
echo "啟動虛擬環境..."
source venv/bin/activate

# 檢查向量數據庫
if [ ! -d "chroma_db" ]; then
    echo "初始化向量數據庫..."
    python3 setup_database.py
fi

# 啟動應用
echo "啟動課程推薦系統..."
echo "請在瀏覽器中訪問: http://localhost:8501"
streamlit run streamlit_app.py --server.address=0.0.0.0 --server.port=8501 