#!/bin/bash

# Docker部署腳本 - RAG課程推薦系統
echo "=== Docker部署RAG課程推薦系統 ==="

# 1. 檢查Docker是否安裝
if ! command -v docker &> /dev/null; then
    echo "Docker未安裝，正在安裝..."
    # Ubuntu/Debian
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "請重新登入以應用Docker群組權限"
    exit 1
fi

# 2. 檢查Docker Compose是否安裝
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose未安裝，正在安裝..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# 3. 創建環境變數文件
if [ ! -f .env ]; then
    echo "創建環境變數文件..."
    cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
EOF
    echo "請編輯 .env 文件，填入您的OpenAI API Key:"
    echo "nano .env"
    echo "完成後按任意鍵繼續..."
    read -n 1
fi

# 4. 構建和啟動容器
echo "構建Docker映像..."
docker-compose build

echo "啟動服務..."
docker-compose up -d

# 5. 顯示狀態
echo "=== 部署完成! ==="
echo "容器狀態:"
docker-compose ps

echo ""
echo "查看日誌: docker-compose logs -f"
echo "停止服務: docker-compose down"
echo "重啟服務: docker-compose restart"
echo "網站地址: http://your-server-ip:8501"

# 6. 等待服務啟動
echo "等待服務啟動..."
sleep 10

# 7. 檢查健康狀態
if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
    echo "✅ 服務已成功啟動!"
else
    echo "⚠️ 服務可能還在啟動中，請稍後檢查"
fi 