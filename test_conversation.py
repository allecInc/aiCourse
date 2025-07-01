#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試對話功能腳本
"""

import sys
import os
from config import Config
from conversation_manager import ConversationManager
from rag_system import RAGSystem

def test_conversation_manager():
    """測試對話管理器"""
    print("=== 測試對話管理器 ===")
    
    # 初始化對話管理器
    cm = ConversationManager()
    
    # 創建會話
    session_id = cm.create_session("test_user")
    print(f"創建會話: {session_id}")
    
    # 添加用戶查詢
    cm.add_message(session_id, "user_query", "我想要減肥的課程")
    
    # 添加系統回應
    cm.add_message(session_id, "system_response", "推薦您以下課程...")
    
    # 添加用戶反饋
    cm.add_user_feedback(
        session_id, "dissatisfied", "時間不合適", 
        rejected_courses=["某課程"], reasons=["時間安排"]
    )
    
    # 獲取對話上下文
    context = cm.get_conversation_context(session_id)
    print(f"對話上下文: {context}")
    
    # 生成追問問題
    questions = cm.generate_followup_questions(session_id, "時間不合適")
    print(f"追問問題: {questions}")
    
    # 優化查詢
    refined_query = cm.get_refined_query(session_id, "減肥課程")
    print(f"優化查詢: {refined_query}")
    
    # 清理會話
    cm.clear_session(session_id)
    print("測試完成！")

def test_rag_system_with_conversation():
    """測試帶對話功能的RAG系統"""
    print("\n=== 測試RAG系統對話功能 ===")
    
    try:
        # 檢查環境變量
        config = Config()
        if not config.OPENAI_API_KEY:
            print("警告: 未設定OpenAI API金鑰，跳過RAG系統測試")
            return
        
        # 初始化RAG系統
        rag_system = RAGSystem(config)
        
        # 初始化知識庫
        print("初始化知識庫...")
        rag_system.initialize_knowledge_base(force_rebuild=False)
        
        # 創建對話會話
        session_id = rag_system.create_conversation_session("test_user_2")
        print(f"創建對話會話: {session_id}")
        
        # 第一次查詢
        print("\n第一次查詢...")
        result1 = rag_system.get_course_recommendation("我想要減肥的課程", session_id=session_id)
        print(f"推薦結果: {result1['success']}")
        if result1['success']:
            print(f"推薦數量: {len(result1['retrieved_courses'])}")
        
        # 添加反饋
        print("\n添加用戶反饋...")
        feedback_result = rag_system.handle_user_feedback(
            session_id, "時間不合適，費用太高", "dissatisfied",
            rejected_courses=[], reasons=["時間安排", "費用問題"]
        )
        print(f"反饋處理結果: {feedback_result}")
        
        # 第二次查詢（帶上下文）
        print("\n第二次查詢（帶反饋上下文）...")
        result2 = rag_system.get_course_recommendation("推薦時間彈性且便宜的減肥課程", session_id=session_id)
        print(f"第二次推薦結果: {result2['success']}")
        
        # 獲取對話歷史
        print("\n對話歷史...")
        history = rag_system.get_conversation_history(session_id)
        print(f"對話消息數: {len(history.get('messages', []))}")
        print(f"用戶偏好: {history.get('user_preferences', {})}")
        
        # 清理
        rag_system.clear_conversation(session_id)
        print("RAG系統測試完成！")
        
    except Exception as e:
        print(f"RAG系統測試出錯: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主測試函數"""
    print("開始測試新的對話功能...\n")
    
    # 測試對話管理器
    test_conversation_manager()
    
    # 測試RAG系統對話功能
    test_rag_system_with_conversation()
    
    print("\n所有測試完成！")

if __name__ == "__main__":
    main() 