#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
數據庫初始化腳本
用於首次設置向量數據庫和載入課程數據
"""

import os
import sys
import logging
from config import Config
from rag_system import RAGSystem

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主要設置流程"""
    try:
        logger.info("開始初始化AI課程推薦系統...")
        
        # 以 SQL Server 為主的初始化流程
        config = Config()
        print("📡 將從 SQL Server 載入課程資料並建立向量庫（如需連線請先設定 .env）")
        
        print("🚀 正在初始化AI課程推薦系統...")
        print("=" * 50)
        
        # 初始化RAG系統
        print("📋 載入配置...")
        rag_system = RAGSystem(config)
        
        print("🔧 初始化向量數據庫...")
        print("📚 載入課程數據（SQL Server）...")
        
        # 強制重建知識庫
        rag_system.initialize_knowledge_base(force_rebuild=True)
        
        # 獲取系統統計
        stats = rag_system.get_system_stats()
        
        print("=" * 50)
        print("✅ 系統初始化完成！")
        print(f"📊 統計資訊:")
        print(f"   • 總課程數: {stats.get('total_courses', 0)}")
        print(f"   • 課程類別數: {stats.get('total_categories', 0)}")
        print(f"   • 使用模型: {stats.get('model_name', 'N/A')}")
        print(f"   • 嵌入模型: {stats.get('embedding_model', 'N/A')}")
        
        # 顯示課程類別
        categories = stats.get('categories', [])
        if categories:
            print(f"\n📂 課程類別:")
            for i, category in enumerate(categories, 1):
                print(f"   {i}. {category}")
        
        print("\n🎉 設置完成！您現在可以運行以下命令啟動應用：")
        print("   streamlit run streamlit_app.py")
        print("\n💡 提醒：請確保已設定 OpenAI API 金鑰")
        
        # 測試查詢
        print("\n🧪 執行測試查詢...")
        test_query = "減肥燃脂課程"
        result = rag_system.get_course_recommendation(test_query)
        
        if result['success']:
            print(f"✅ 測試成功！找到 {len(result['retrieved_courses'])} 個相關課程")
        else:
            print("⚠️  測試查詢未找到結果，但系統運行正常")
        
        logger.info("系統初始化完成")
        
    except Exception as e:
        logger.error(f"初始化失敗: {e}")
        print(f"❌ 初始化失敗: {e}")
        print("請檢查錯誤日誌 setup.log 獲取詳細資訊")
        sys.exit(1)

if __name__ == "__main__":
    main() 
