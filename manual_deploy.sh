#!/bin/bash

echo "=== 手動Linux部署腳本 ==="

# 1. 檢查當前目錄
echo "當前目錄: $(pwd)"
echo "檢查重要文件..."

# 檢查必要文件
files=("streamlit_app.py" "rag_system.py" "vector_store.py" "requirements.txt" "AI課程.json")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file 存在"
    else
        echo "❌ $file 不存在"
        exit 1
    fi
done

# 2. 檢查.env文件
if [ ! -f ".env" ]; then
    echo "創建.env文件..."
    cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
EOF
    echo "⚠️  請編輯 .env 文件，填入您的OpenAI API Key"
    echo "nano .env"
    read -p "完成後按Enter繼續..."
fi

# 3. 創建虛擬環境
echo "創建Python虛擬環境..."
python3 -m venv venv

# 4. 啟動虛擬環境
echo "啟動虛擬環境..."
source venv/bin/activate

# 5. 升級pip
echo "升級pip..."
pip install --upgrade pip

# 6. 安裝依賴
echo "安裝依賴套件..."
pip install --only-binary=all -r requirements.txt

# 7. 檢查ChromaDB目錄
if [ ! -d "chroma_db" ]; then
    echo "初始化向量數據庫..."
    python3 setup_database.py
fi

# 8. 測試啟動
echo "測試系統啟動..."
python3 -c "
try:
    from rag_system import RAGSystem
    print('✅ 系統導入成功')
    rag = RAGSystem()
    print('✅ RAG系統初始化成功')
except Exception as e:
    print(f'❌ 錯誤: {e}')
    exit(1)
"

# 9. 啟動Streamlit
echo "啟動Streamlit應用..."
echo "請在瀏覽器中訪問: http://localhost:8501"
streamlit run streamlit_app.py --server.address=0.0.0.0 --server.port=8501 