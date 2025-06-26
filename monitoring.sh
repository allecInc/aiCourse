#!/bin/bash

# 監控腳本 - RAG課程推薦系統
echo "=== RAG課程推薦系統監控報告 ==="
echo "時間: $(date)"
echo ""

# 1. 系統資源監控
echo "📊 系統資源使用情況:"
echo "CPU使用率: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "記憶體使用率: $(free | grep Mem | awk '{printf("%.1f%%"), $3/$2 * 100.0}')"
echo "磁碟使用率: $(df -h / | awk 'NR==2{printf "%s", $5}')"
echo ""

# 2. 服務狀態檢查
echo "🔧 服務狀態:"
if systemctl is-active --quiet ai-course-recommender; then
    echo "✅ ai-course-recommender 服務運行正常"
else
    echo "❌ ai-course-recommender 服務異常"
fi

if docker ps | grep -q ai-course-recommender; then
    echo "✅ Docker容器運行正常"
else
    echo "❌ Docker容器異常"
fi
echo ""

# 3. 網路連接檢查
echo "🌐 網路連接檢查:"
if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
    echo "✅ 應用程式健康檢查通過"
else
    echo "❌ 應用程式健康檢查失敗"
fi

if ping -c 1 api.openai.com > /dev/null 2>&1; then
    echo "✅ OpenAI API連接正常"
else
    echo "❌ OpenAI API連接異常"
fi
echo ""

# 4. 日誌檢查
echo "📝 最近錯誤日誌:"
if systemctl is-active --quiet ai-course-recommender; then
    journalctl -u ai-course-recommender --since "1 hour ago" | grep -i error | tail -5
fi

if docker ps | grep -q ai-course-recommender; then
    docker-compose logs --tail=5 ai-course-recommender | grep -i error
fi
echo ""

# 5. 磁碟空間檢查
echo "💾 ChromaDB資料庫大小:"
if [ -d "chroma_db" ]; then
    du -sh chroma_db/
fi
echo ""

# 6. 效能統計
echo "📈 應用程式效能統計:"
echo "最近1小時的查詢次數:"
if systemctl is-active --quiet ai-course-recommender; then
    journalctl -u ai-course-recommender --since "1 hour ago" | grep "開始處理查詢" | wc -l
fi

echo ""
echo "=== 監控報告結束 ===" 