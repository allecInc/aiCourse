#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系統測試腳本
用於驗證RAG系統的各項功能
"""

import os
import sys
import logging
from config import Config
from rag_system import RAGSystem

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_course_processor():
    """測試課程處理器"""
    print("🧪 測試課程處理器...")
    
    try:
        from course_processor import CourseProcessor
        processor = CourseProcessor("AI課程.json")
        
        # 載入課程
        courses = processor.load_courses()
        print(f"✅ 載入 {len(courses)} 筆課程數據")
        
        # 獲取類別
        categories = processor.get_course_categories()
        print(f"✅ 找到 {len(categories)} 個課程類別")
        for i, category in enumerate(categories[:5], 1):
            print(f"   {i}. {category}")
        
        # 準備向量化數據
        vector_data = processor.prepare_for_vectorization()
        print(f"✅ 準備 {len(vector_data)} 筆向量化數據")
        
        return True
        
    except Exception as e:
        print(f"❌ 課程處理器測試失敗: {e}")
        return False

def test_vector_store():
    """測試向量數據庫"""
    print("\n🧪 測試向量數據庫...")
    
    try:
        from vector_store import VectorStore
        vector_store = VectorStore()
        
        # 獲取統計
        stats = vector_store.get_collection_stats()
        print(f"✅ 向量數據庫統計: {stats}")
        
        # 測試搜尋
        test_queries = [
            "減肥燃脂",
            "瑜珈放鬆", 
            "游泳教學",
            "球類運動"
        ]
        
        for query in test_queries:
            results = vector_store.search_similar_courses(query, k=3)
            print(f"✅ 查詢「{query}」找到 {len(results)} 個相關課程")
            
            if results:
                for i, result in enumerate(results[:2], 1):
                    print(f"   {i}. {result['title']} (相似度: {result['similarity_score']:.3f})")
        
        return True
        
    except Exception as e:
        print(f"❌ 向量數據庫測試失敗: {e}")
        return False

def test_rag_system():
    """測試RAG系統"""
    print("\n🧪 測試RAG系統...")
    
    try:
        rag_system = RAGSystem()
        
        # 獲取系統統計
        stats = rag_system.get_system_stats()
        print(f"✅ 系統統計: {stats}")
        
        # 測試推薦功能（不需要API金鑰的部分）
        test_queries = [
            "我想要減肥的課程",
            "適合初學者的瑜珈課程",
            "游泳教學課程",
            "球類運動課程"
        ]
        
        for query in test_queries:
            # 只測試檢索部分
            retrieved_courses = rag_system.retrieve_relevant_courses(query)
            print(f"✅ 查詢「{query}」檢索到 {len(retrieved_courses)} 個相關課程")
            
            if retrieved_courses:
                for i, course in enumerate(retrieved_courses[:2], 1):
                    print(f"   {i}. {course['title']} - {course['category']}")
        
        # 測試類別功能
        categories = rag_system.get_all_categories()
        print(f"✅ 獲取 {len(categories)} 個課程類別")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG系統測試失敗: {e}")
        return False

def test_full_recommendation():
    """測試完整推薦流程（需要API金鑰）"""
    print("\n🧪 測試完整推薦流程...")
    
    config = Config()
    if config.OPENAI_API_KEY == "your_openai_api_key_here":
        print("⏭️  跳過完整推薦測試（需要設定OpenAI API金鑰）")
        return True
    
    try:
        rag_system = RAGSystem(config)
        
        test_query = "我想要減肥燃脂的課程"
        result = rag_system.get_course_recommendation(test_query)
        
        if result['success']:
            print(f"✅ 完整推薦測試成功")
            print(f"   查詢: {result['query']}")
            print(f"   找到 {len(result['retrieved_courses'])} 個相關課程")
            print(f"   推薦長度: {len(result['recommendation'])} 字符")
        else:
            print(f"⚠️  推薦測試未成功: {result['recommendation']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 完整推薦測試失敗: {e}")
        return False

def run_performance_test():
    """運行性能測試"""
    print("\n🧪 運行性能測試...")
    
    try:
        import time
        from rag_system import RAGSystem
        
        rag_system = RAGSystem()
        
        test_queries = [
            "減肥燃脂課程",
            "瑜珈放鬆課程", 
            "游泳教學課程",
            "球類運動課程",
            "高強度有氧運動"
        ]
        
        total_time = 0
        successful_queries = 0
        
        for query in test_queries:
            start_time = time.time()
            
            try:
                results = rag_system.retrieve_relevant_courses(query)
                end_time = time.time()
                
                query_time = end_time - start_time
                total_time += query_time
                successful_queries += 1
                
                print(f"✅ 查詢「{query}」耗時 {query_time:.2f}秒，找到 {len(results)} 個結果")
                
            except Exception as e:
                print(f"❌ 查詢「{query}」失敗: {e}")
        
        if successful_queries > 0:
            avg_time = total_time / successful_queries
            print(f"📊 平均查詢時間: {avg_time:.2f}秒")
            print(f"📊 成功率: {successful_queries}/{len(test_queries)} ({successful_queries/len(test_queries)*100:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ 性能測試失敗: {e}")
        return False

def main():
    """主測試流程"""
    print("🚀 開始系統測試...")
    print("=" * 60)
    
    # 檢查必要文件
    if not os.path.exists("AI課程.json"):
        print("❌ 找不到 AI課程.json 文件")
        sys.exit(1)
    
    test_results = []
    
    # 運行各項測試
    test_results.append(("課程處理器", test_course_processor()))
    test_results.append(("向量數據庫", test_vector_store()))
    test_results.append(("RAG系統", test_rag_system()))
    test_results.append(("完整推薦", test_full_recommendation()))
    test_results.append(("性能測試", run_performance_test()))
    
    # 總結測試結果
    print("\n" + "=" * 60)
    print("📋 測試結果總結:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 測試通過率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 所有測試通過！系統運行正常。")
        return 0
    else:
        print("⚠️  部分測試失敗，請檢查系統配置。")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
 