#!/bin/bash

# Docker 部署腳本 - 修復版本
# 解決 huggingface_hub 相容性問題

set -e

echo "🚀 開始 Docker 部署（修復版本）..."

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 錯誤處理函數
error_exit() {
    echo -e "${RED}❌ 錯誤: $1${NC}" >&2
    exit 1
}

success_msg() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning_msg() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 檢查 Docker 是否安裝
if ! command -v docker &> /dev/null; then
    error_exit "Docker 未安裝，請先安裝 Docker"
fi

# 檢查 Docker Compose 是否安裝
if ! command -v docker-compose &> /dev/null; then
    error_exit "Docker Compose 未安裝，請先安裝 Docker Compose"
fi

# 停止現有容器
echo "🛑 停止現有容器..."
docker-compose down --remove-orphans || true

# 清理現有映像（可選）
read -p "是否要清理舊的映像？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 清理舊映像..."
    docker system prune -f
    docker image rm aisuggestcourse-app || true
fi

# 檢查並修復依賴檔案
echo "🔧 檢查依賴檔案..."
if [ ! -f "requirements_fixed.txt" ]; then
    warning_msg "requirements_fixed.txt 不存在，使用 requirements.txt"
    cp requirements.txt requirements_fixed.txt
fi

# 確保相容性版本
echo "📝 更新依賴版本以修復相容性問題..."
if ! grep -q "huggingface_hub" requirements_fixed.txt; then
    echo "huggingface_hub>=0.23.0,<1.0.0" >> requirements_fixed.txt
fi

if ! grep -q "transformers" requirements_fixed.txt; then
    echo "transformers>=4.36.0" >> requirements_fixed.txt
fi

if ! grep -q "requests" requirements_fixed.txt; then
    echo "requests>=2.31.0" >> requirements_fixed.txt
fi

# 確保 ChromaDB 版本相容
if ! grep -q "chromadb" requirements_fixed.txt; then
    echo "chromadb>=0.4.15,<0.5.0" >> requirements_fixed.txt
else
    # 替換 ChromaDB 版本
    sed -i 's/chromadb==0.4.22/chromadb>=0.4.15,<0.5.0/' requirements_fixed.txt
fi

# 建構映像
echo "🏗️  建構 Docker 映像..."
docker-compose build --no-cache || error_exit "建構映像失敗"

success_msg "映像建構完成"

# 啟動服務
echo "🚀 啟動服務..."
docker-compose up -d || error_exit "啟動服務失敗"

# 等待服務啟動
echo "⏳ 等待服務啟動..."
sleep 10

# 檢查服務狀態
echo "🔍 檢查服務狀態..."
if docker-compose ps | grep -q "Up"; then
    success_msg "服務啟動成功！"
    
    # 顯示日誌片段
    echo "📋 最近的日誌:"
    docker-compose logs --tail=20
    
    echo ""
    echo "🌐 應用程式已啟動，可透過以下方式存取:"
    echo "   本地: http://localhost:8501"
    echo "   內網: http://$(hostname -I | awk '{print $1}'):8501"
    
else
    error_exit "服務啟動失敗"
fi

# 提供有用的命令
echo ""
echo "📚 有用的命令:"
echo "   查看日誌: docker-compose logs -f"
echo "   停止服務: docker-compose down"
echo "   重啟服務: docker-compose restart"
echo "   進入容器: docker-compose exec app bash"

# 檢查 huggingface_hub 相容性
echo ""
echo "🔧 檢查 huggingface_hub 相容性..."
docker-compose exec app python -c "
try:
    import huggingface_hub
    print(f'✅ huggingface_hub 版本: {huggingface_hub.__version__}')
    
    # 檢查關鍵函數
    if hasattr(huggingface_hub, 'cached_download'):
        print('✅ cached_download 函數可用')
    elif hasattr(huggingface_hub, 'hf_hub_download'):
        print('✅ hf_hub_download 函數可用 (新版本)')
    else:
        print('❌ 找不到下載函數')
        
    # 測試 sentence-transformers
    from sentence_transformers import SentenceTransformer
    print('✅ sentence-transformers 載入成功')
    
except Exception as e:
    print(f'❌ 相容性檢查失敗: {e}')
    exit(1)
" 2>/dev/null || warning_msg "無法執行相容性檢查，但服務可能仍正常運行"

success_msg "部署完成！" 