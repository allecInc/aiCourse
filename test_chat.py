#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試AI聊天室功能腳本
"""

import sys
import os
from config import Config
from rag_system import RAGSystem

def test_chat_functionality():
    """測試聊天功能"""
    print("=== 測試AI聊天室功能 ===")
    
    try:
        # 檢查環境變量
        config = Config()
        if not config.OPENAI_API_KEY:
            print("警告: 未設定OpenAI API金鑰，無法測試聊天功能")
            return
        
        # 初始化RAG系統
        rag_system = RAGSystem(config)
        
        # 初始化知識庫
        print("初始化知識庫...")
        rag_system.initialize_knowledge_base(force_rebuild=False)
        
        # 創建對話會話
        session_id = rag_system.create_conversation_session("chat_test_user")
        print(f"創建聊天會話: {session_id}\n")
        
        # 測試對話流程
        test_messages = [
            "你好！",
            "你能做什麼？",
            "我想要減肥的課程",
            "有沒有週末的課程？",
            "費用大概多少？",
            "謝謝你的推薦"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"第{i}輪對話:")
            print(f"用戶: {message}")
            
            # 發送消息給AI
            chat_result = rag_system.chat_with_user(session_id, message)
            
            if chat_result['success']:
                print(f"AI: {chat_result['ai_response']}")
                
                # 如果有推薦課程，顯示課程信息
                if chat_result['courses']:
                    print(f"推薦了 {len(chat_result['courses'])} 個課程:")
                    for course in chat_result['courses'][:2]:  # 只顯示前2個
                        print(f"  - {course['title']} ({course['category']})")
                
                # 顯示是否被識別為課程查詢
                print(f"課程查詢: {'是' if chat_result['is_course_query'] else '否'}")
            else:
                print(f"AI回應失敗: {chat_result['ai_response']}")
            
            print("-" * 50)
        
        # 顯示對話歷史統計
        print("\n對話歷史統計:")
        history = rag_system.get_conversation_history(session_id)
        if history:
            messages = history.get('messages', [])
            print(f"總消息數: {len(messages)}")
            
            user_messages = [m for m in messages if m['type'] == 'user_message']
            ai_responses = [m for m in messages if m['type'] == 'ai_response']
            
            print(f"用戶消息: {len(user_messages)}")
            print(f"AI回應: {len(ai_responses)}")
            
            if history.get('user_preferences'):
                print(f"學習到的用戶偏好: {history['user_preferences']}")
        
        # 清理測試會話
        rag_system.clear_conversation(session_id)
        print("\n聊天功能測試完成！")
        
    except Exception as e:
        print(f"聊天功能測試出錯: {e}")
        import traceback
        traceback.print_exc()

def interactive_chat_test():
    """互動式聊天測試"""
    print("\n=== 互動式聊天測試 ===")
    print("輸入 'quit' 退出測試")
    
    try:
        config = Config()
        if not config.OPENAI_API_KEY:
            print("未設定OpenAI API金鑰，無法進行互動測試")
            return
        
        rag_system = RAGSystem(config)
        rag_system.initialize_knowledge_base(force_rebuild=False)
        
        session_id = rag_system.create_conversation_session("interactive_test")
        print(f"會話ID: {session_id}")
        print("開始與AI聊天吧！\n")
        
        while True:
            try:
                user_input = input("您: ").strip()
                
                if user_input.lower() in ['quit', 'exit', '退出', '結束']:
                    print("結束互動測試")
                    break
                
                if not user_input:
                    continue
                
                # 發送消息
                chat_result = rag_system.chat_with_user(session_id, user_input)
                
                if chat_result['success']:
                    print(f"AI: {chat_result['ai_response']}")
                    
                    if chat_result['courses']:
                        print(f"\n推薦了 {len(chat_result['courses'])} 個課程:")
                        for course in chat_result['courses'][:3]:
                            print(f"  📚 {course['title']} ({course['category']})")
                        print()
                else:
                    print(f"AI: {chat_result['ai_response']}")
                
                print()
                
            except KeyboardInterrupt:
                print("\n\n收到中斷信號，結束測試")
                break
            except EOFError:
                print("\n\n輸入結束，退出測試")
                break
        
        # 清理
        rag_system.clear_conversation(session_id)
        
    except Exception as e:
        print(f"互動測試出錯: {e}")

def main():
    """主測試函數"""
    print("AI聊天室功能測試")
    print("=" * 50)
    
    # 自動測試
    test_chat_functionality()
    
    # 詢問是否進行互動測試
    while True:
        try:
            choice = input("\n要進行互動式聊天測試嗎？(y/n): ").strip().lower()
            if choice in ['y', 'yes', '是', 'Y']:
                interactive_chat_test()
                break
            elif choice in ['n', 'no', '否', 'N']:
                print("跳過互動測試")
                break
            else:
                print("請輸入 y 或 n")
        except (KeyboardInterrupt, EOFError):
            print("\n跳過互動測試")
            break
    
    print("\n所有測試完成！")

if __name__ == "__main__":
    main() 