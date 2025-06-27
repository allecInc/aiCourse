#!/bin/bash
# AI課程推薦系統 - 服務啟動器 (Linux/Mac)

echo ""
echo "🤖 AI課程推薦系統 - 服務啟動器"
echo "同時啟動API服務 (FastAPI) 和網頁服務 (Streamlit)"
echo "======================================================================"
echo ""

# 檢查Python是否安裝
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ 未找到Python，請先安裝Python"
    exit 1
fi

# 選擇Python命令
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

echo "使用Python命令: $PYTHON_CMD"

# 檢查必要檔案
required_files=("api_server.py" "streamlit_app.py" "config.py" "rag_system.py")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ 缺少 $file 檔案"
        exit 1
    fi
done

echo "✅ 環境檢查通過"
echo ""

# 創建日誌目錄
mkdir -p logs

# 定義清理函數
cleanup() {
    echo ""
    echo "🛑 正在停止所有服務..."
    
    if [ ! -z "$API_PID" ]; then
        echo "停止API服務 (PID: $API_PID)"
        kill $API_PID 2>/dev/null
        wait $API_PID 2>/dev/null
    fi
    
    if [ ! -z "$STREAMLIT_PID" ]; then
        echo "停止Streamlit服務 (PID: $STREAMLIT_PID)"
        kill $STREAMLIT_PID 2>/dev/null
        wait $STREAMLIT_PID 2>/dev/null
    fi
    
    echo "✅ 所有服務已停止"
    exit 0
}

# 設定信號處理器
trap cleanup SIGINT SIGTERM

echo "🚀 正在啟動API服務..."
# 啟動API服務
$PYTHON_CMD -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload > logs/api.log 2>&1 &
API_PID=$!

echo "✅ API服務已啟動 (PID: $API_PID)"

# 等待2秒
sleep 2

echo "🚀 正在啟動Streamlit網頁服務..."
# 啟動Streamlit服務
$PYTHON_CMD -m streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true > logs/streamlit.log 2>&1 &
STREAMLIT_PID=$!

echo "✅ Streamlit服務已啟動 (PID: $STREAMLIT_PID)"

# 等待服務啟動
echo ""
echo "⏳ 等待服務啟動中..."
sleep 5

# 檢查服務是否正常運行
check_service() {
    local url=$1
    local name=$2
    
    if command -v curl &> /dev/null; then
        if curl -s --max-time 5 "$url" > /dev/null 2>&1; then
            echo "✅ $name 服務檢查通過"
            return 0
        else
            echo "⚠️  $name 服務可能還在初始化中"
            return 1
        fi
    else
        echo "⚠️  未安裝curl，無法檢查 $name 服務狀態"
        return 1
    fi
}

echo ""
echo "🔍 檢查服務狀態..."
check_service "http://localhost:8000/health" "API"
check_service "http://localhost:8501" "Streamlit"

echo ""
echo "======================================================================"
echo "✅ 所有服務已啟動！"
echo ""
echo "🌐 服務網址:"
echo "   • API服務:        http://localhost:8000"
echo "   • API文檔:        http://localhost:8000/docs"
echo "   • 網頁介面:       http://localhost:8501"
echo "   • 健康檢查:       http://localhost:8000/health"
echo ""
echo "📁 日誌檔案:"
echo "   • API日誌:        logs/api.log"
echo "   • Streamlit日誌:  logs/streamlit.log"
echo ""
echo "💡 提示:"
echo "   • 按 Ctrl+C 停止所有服務"
echo "   • 可使用 'tail -f logs/api.log' 查看API日誌"
echo "   • 可使用 'tail -f logs/streamlit.log' 查看Streamlit日誌"
echo "======================================================================"
echo ""

# 詢問是否要開啟瀏覽器 (僅在Mac上)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -n "是否要自動開啟瀏覽器? (y/n): "
    read -r open_browser
    if [[ $open_browser =~ ^[Yy]$ ]]; then
        echo "🌐 正在開啟瀏覽器..."
        open http://localhost:8501
        open http://localhost:8000/docs
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo -n "是否要自動開啟瀏覽器? (y/n): "
    read -r open_browser
    if [[ $open_browser =~ ^[Yy]$ ]]; then
        echo "🌐 正在開啟瀏覽器..."
        if command -v xdg-open &> /dev/null; then
            xdg-open http://localhost:8501 2>/dev/null &
            xdg-open http://localhost:8000/docs 2>/dev/null &
        else
            echo "⚠️  未找到瀏覽器開啟命令，請手動開啟網址"
        fi
    fi
fi

echo ""
echo "🔄 服務正在運行中，按 Ctrl+C 停止..."

# 保持腳本運行並監控進程
while true; do
    # 檢查API進程是否還在運行
    if ! kill -0 $API_PID 2>/dev/null; then
        echo "❌ API服務意外停止"
        cleanup
    fi
    
    # 檢查Streamlit進程是否還在運行
    if ! kill -0 $STREAMLIT_PID 2>/dev/null; then
        echo "❌ Streamlit服務意外停止"
        cleanup
    fi
    
    sleep 2
done 