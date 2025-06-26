#!/bin/bash

# Linux部署腳本 - RAG課程推薦系統
echo "=== 開始部署RAG課程推薦系統到Linux ==="

# 1. 創建專案目錄
PROJECT_DIR="/opt/ai-course-recommender"
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR
cd $PROJECT_DIR

# 2. 複製專案文件 (假設已經上傳到伺服器)
echo "請確保已將以下文件上傳到 $PROJECT_DIR:"
echo "- *.py (所有Python文件)"
echo "- requirements.txt"
echo "- AI課程.json"
echo "- chroma_db/ (向量數據庫目錄)"

# 3. 創建Python虛擬環境
echo "創建Python虛擬環境..."
python3 -m venv venv
source venv/bin/activate

# 4. 升級pip
pip install --upgrade pip

# 5. 安裝依賴套件
echo "安裝依賴套件..."
pip install --only-binary=all -r requirements.txt

# 6. 創建環境變數文件
echo "創建環境變數文件..."
cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
EOF

echo "請編輯 .env 文件，填入您的OpenAI API Key:"
echo "nano .env"

# 7. 設置權限
chmod +x *.py
chmod 600 .env

# 8. 創建systemd服務文件
echo "創建systemd服務..."
sudo tee /etc/systemd/system/ai-course-recommender.service > /dev/null << EOF
[Unit]
Description=AI Course Recommender
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 9. 啟用並啟動服務
sudo systemctl daemon-reload
sudo systemctl enable ai-course-recommender
sudo systemctl start ai-course-recommender

echo "=== 部署完成! ==="
echo "服務狀態: sudo systemctl status ai-course-recommender"
echo "查看日誌: sudo journalctl -u ai-course-recommender -f"
echo "網站地址: http://your-server-ip:8501" 