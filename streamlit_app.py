import streamlit as st
import pandas as pd
from typing import Dict, Any
import logging
import os
from config import Config
from openai import OpenAI
from rag_system import RAGSystem

# 設定頁面配置
st.set_page_config(
    page_title="AI課程推薦機器人",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 自定義CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .course-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border-left: 4px solid #1f77b4;
    }
    .similarity-score {
        background-color: #e8f4f8;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .category-tag {
        background-color: #ff6b6b;
        color: white;
        padding: 0.2rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        margin-right: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def initialize_rag_system():
    """初始化RAG系統（使用快取避免重複初始化）"""
    try:
        from auto_file_monitor import get_file_monitor
        
        # 初始化檔案監控器
        monitor = get_file_monitor()
        if monitor.last_mtime is None:
            monitor.initialize()
        
        config = Config()
        rag_system = RAGSystem(config)
        
        # 檢查並初始化知識庫（讓系統自動判斷是否需要重建）
        try:
            with st.spinner("正在初始化知識庫..."):
                rag_system.initialize_knowledge_base(force_rebuild=False)
        except Exception as init_error:
            st.warning(f"初始知識庫建立失敗: {init_error}")
            # 嘗試強制重建
            try:
                st.info("嘗試強制重建知識庫...")
                with st.spinner("正在重建知識庫..."):
                    rag_system.initialize_knowledge_base(force_rebuild=True)
                st.success("知識庫重建成功！")
            except Exception as rebuild_error:
                st.error(f"強制重建也失敗: {rebuild_error}")
                raise
        
        return rag_system
    except Exception as e:
        st.error(f"初始化RAG系統失敗: {e}")
        return None

def display_course_card(course: Dict[str, Any], show_similarity: bool = True):
    """顯示課程卡片"""
    with st.container():
        st.markdown('<div class="course-card">', unsafe_allow_html=True)
        
        # 課程標題和類別
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### {course['title']}")
        with col2:
            st.markdown(f'<span class="category-tag">{course["category"]}</span>', 
                       unsafe_allow_html=True)
        
        # 相似度分數
        if show_similarity and 'similarity_score' in course:
            st.markdown(f'<span class="similarity-score">相似度: {course["similarity_score"]:.1%}</span>', 
                       unsafe_allow_html=True)
        
        # 課程描述
        st.write(course['description'])
        
        # 額外資訊
        metadata = course.get('metadata', {})
        additional_info = []
        
        for key in ['meta_授課教師', 'meta_年齡限制', 'meta_上課時間', 'meta_課程費用', 'meta_體驗費用']:
            if key in metadata and metadata[key]:
                field_name = key.replace('meta_', '')
                additional_info.append(f"**{field_name}**: {metadata[key]}")
        
        if additional_info:
            st.markdown("**詳細資訊:**")
            for info in additional_info:
                st.markdown(f"- {info}")
        
        st.markdown('</div>', unsafe_allow_html=True)

def main():
    """主應用程式"""
    
    # 標題
    st.markdown('<h1 class="main-header">🤖 AI課程推薦機器人</h1>', 
                unsafe_allow_html=True)
    
    # 初始化RAG系統
    rag_system = initialize_rag_system()
    
    if rag_system is None:
        st.error("無法初始化RAG系統，請檢查配置。")
        st.stop()
    
    # 啟動時自動檢查檔案更新（只在第一次載入時執行）
    if 'auto_check_done' not in st.session_state:
        from auto_file_monitor import check_and_update_data
        try:
            update_result = check_and_update_data()
            if update_result['updated']:
                st.info("🔄 檢測到資料檔案更新，正在重新載入...")
                st.cache_resource.clear()
                st.rerun()
        except Exception as e:
            st.warning(f"自動更新檢查失敗: {e}")
        finally:
            st.session_state['auto_check_done'] = True
    

    
    # 側邊欄
    with st.sidebar:
        st.header("⚙️ 系統設定")
        
        # API 金鑰設定（從 session/.env/Config 自動帶入預設值）
        placeholder = 'your_openai_api_key_here'
        env_api = os.getenv('OPENAI_API_KEY', '')
        config_api = getattr(rag_system.config, 'OPENAI_API_KEY', '') if rag_system else ''
        default_api_key = (
            st.session_state.get('api_key')
            or (env_api if env_api else '')
            or (config_api if config_api and config_api != placeholder else '')
        )
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=default_api_key,
            help="請輸入您的 OpenAI API 金鑰"
        )
        if api_key:
            st.session_state['api_key'] = api_key
            rag_system.config.OPENAI_API_KEY = api_key
            # 以新 Key 重新建立 OpenAI 客戶端（v1 寫法）
            try:
                rag_system.openai_client = OpenAI(api_key=api_key)
            except Exception as _:
                pass
        
        # 系統資訊（保留）
        st.subheader("📊 系統統計")
        stats = rag_system.get_system_stats()
        st.metric("總課程數", stats.get('total_courses', 0))
        st.metric("課程類別數", stats.get('total_categories', 0))
        
        # 已移除「資料檔案資訊」區塊，僅保留必要設定與統計
    
    # 主要內容區域
    tab1, tab2, tab3, tab4 = st.tabs(["💬 AI聊天室", "📜 對話記錄", "📚 瀏覽課程", "ℹ️ 關於系統"])
    
    with tab1:
        st.header("💬 AI課程推薦聊天室")
        st.write("與AI助手聊天，詢問任何關於課程的問題！AI會記住我們的對話內容。")
        
        # 初始化會話狀態
        if 'conversation_session_id' not in st.session_state:
            st.session_state.conversation_session_id = rag_system.create_conversation_session()
        
        if 'chat_input' not in st.session_state:
            st.session_state.chat_input = ""
        
        if 'processing_ai_response' not in st.session_state:
            st.session_state.processing_ai_response = False
            
        if 'just_sent_message' not in st.session_state:
            st.session_state.just_sent_message = False
        
        # 聊天界面
        chat_container = st.container()
        
        # 顯示聊天歷史
        with chat_container:
            # 獲取對話歷史
            conversation_history = rag_system.get_conversation_history(st.session_state.conversation_session_id)
            
            if conversation_history and conversation_history.get('messages'):
                messages = conversation_history['messages']
                
                # 顯示歷史消息
                for message in messages:
                    timestamp = message.get('timestamp', '')
                    time_str = timestamp.split('T')[1][:5] if 'T' in timestamp else ''
                    
                    if message['type'] in ['user_message', 'user_query']:
                        # 用戶消息
                        st.markdown(f"""
                        <div style="text-align: right; margin-bottom: 10px;">
                            <div style="background-color: #DCF8C6; padding: 10px; border-radius: 10px; display: inline-block; max-width: 70%; text-align: left;">
                                {message['content']}
                            </div>
                            <div style="font-size: 0.8em; color: #666; margin-top: 5px;">
                                您 {time_str}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    elif message['type'] in ['ai_response', 'system_response']:
                        # AI回應
                        st.markdown(f"""
                        <div style="text-align: left; margin-bottom: 10px;">
                            <div style="background-color: #F1F1F1; padding: 10px; border-radius: 10px; display: inline-block; max-width: 70%;">
                                {message['content']}
                            </div>
                            <div style="font-size: 0.8em; color: #666; margin-top: 5px;">
                                AI助手 {time_str}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 如果有推薦課程，顯示課程卡片
                        if message.get('courses'):
                            st.write("**推薦課程：**")
                            for course in message['courses'][:3]:  # 最多顯示3個
                                with st.expander(f"📚 {course['title']} ({course['category']})"):
                                    display_course_card(course, show_similarity=False)
            else:
                # 歡迎消息
                st.markdown(f"""
                <div style="text-align: left; margin-bottom: 20px;">
                    <div style="background-color: #F1F1F1; padding: 15px; border-radius: 10px; display: inline-block; max-width: 70%;">
                        您好！我是您的AI課程推薦助手 😊<br><br>
                        您可以：<br>
                        • 詢問任何課程相關問題<br>
                        • 直接說出您的需求，我會推薦適合的課程<br><br>
                        試著問問我：「有什麼適合減肥的課程？」
                    </div>
                    <div style="font-size: 0.8em; color: #666; margin-top: 5px;">
                        AI助手
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # 檢查是否需要處理AI回應（在顯示聊天歷史之後）
        conversation_history = rag_system.get_conversation_history(st.session_state.conversation_session_id)
        needs_ai_response = False
        
        if conversation_history and conversation_history.get('messages'):
            messages = conversation_history['messages']
            # 檢查最後一條消息是否是用戶消息且沒有AI回應
            if messages and messages[-1]['type'] == 'user_message':
                # 檢查是否有對應的AI回應
                last_user_msg = messages[-1]
                has_ai_response = False
                
                # 檢查是否已經有AI回應這條用戶消息
                for i in range(len(messages) - 1, -1, -1):
                    if messages[i]['type'] in ['ai_response', 'system_response']:
                        # 找到最近的AI回應，檢查時間戳
                        ai_timestamp = messages[i].get('timestamp', '')
                        user_timestamp = last_user_msg.get('timestamp', '')
                        if ai_timestamp >= user_timestamp:
                            has_ai_response = True
                        break
                
                if not has_ai_response:
                    needs_ai_response = True
        
        # 如果需要AI回應，根據狀態決定是否處理
        if needs_ai_response and api_key:
            if st.session_state.just_sent_message:
                # 剛發送消息，先讓用戶看到消息，然後設置觸發AI回應
                st.session_state.just_sent_message = False
                st.session_state.processing_ai_response = True
                # 顯示一個提示並在短時間後自動觸發AI回應
                st.info("🤖 AI正在準備回應...")
                import time
                time.sleep(0.1)  # 短暫延遲讓用戶看到自己的消息
                st.rerun()
            elif not st.session_state.processing_ai_response:
                # 開始處理AI回應
                st.session_state.processing_ai_response = True
                st.rerun()
            else:
                # 正在處理AI回應
                st.info("🤖 AI正在思考回應中...")
                
                # 自動處理AI回應
                try:
                    last_user_input = messages[-1]['content']
                    
                    # 使用聊天功能（但不添加用戶消息，因為已經添加了）
                    with st.spinner("正在生成回應..."):
                        chat_result = rag_system.process_user_query_for_existing_message(
                            st.session_state.conversation_session_id, 
                            last_user_input
                        )
                        
                        if chat_result['success']:
                            # 重置狀態並重新載入頁面顯示AI回應
                            st.session_state.processing_ai_response = False
                            st.rerun()
                        else:
                            st.error("AI回應時出現錯誤，請重試。")
                            st.session_state.processing_ai_response = False
                            
                except Exception as e:
                    st.error(f"AI回應時發生錯誤: {e}")
                    st.session_state.processing_ai_response = False
        
        # 快速範例
        st.write("**💡 快速開始：**")
        col1, col2, col3, col4 = st.columns(4)
        
        quick_examples = {
            "👋 打招呼": "你好！",
            "🔥 減肥課程": "有什麼減肥課程？",
            "🧘 瑜珈課程": "推薦瑜珈課程",
            "🏊 游泳課程": "我想學游泳"
        }
        
        cols = [col1, col2, col3, col4]
        for i, (button_text, example_text) in enumerate(quick_examples.items()):
            with cols[i]:
                if st.button(button_text, key=f"quick_{i}"):
                    st.session_state.chat_input = example_text
                    st.rerun()
        
        # 聊天輸入區域
        st.divider()
        
        # 使用表單來處理輸入
        with st.form("chat_form", clear_on_submit=True):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                user_input = st.text_input(
                    "輸入消息",
                    value=st.session_state.chat_input,
                    placeholder="輸入您的消息...",
                    key="current_input",
                    label_visibility="collapsed"
                )
            
            with col2:
                send_button = st.form_submit_button("發送 📤", type="primary")
            
            # 處理發送
            if send_button and user_input.strip():
                if not api_key:
                    st.error("請先在側邊欄輸入OpenAI API金鑰！")
                else:
                    # 清空輸入
                    st.session_state.chat_input = ""
                    
                    # 先添加用戶消息到會話中
                    from datetime import datetime
                    user_message = {
                        'type': 'user_message',
                        'content': user_input,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # 立即將用戶消息添加到對話歷史
                    rag_system.conversation_manager.add_message(
                        st.session_state.conversation_session_id, 
                        "user_message", 
                        user_input
                    )
                    
                    # 設置剛發送消息的標記
                    st.session_state.just_sent_message = True
                    st.session_state.processing_ai_response = False
                    
                    # 重新載入頁面顯示用戶消息
                    st.rerun()
        
        # 清空聊天記錄
        st.divider()
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🗑️ 清空聊天", type="secondary"):
                rag_system.clear_conversation(st.session_state.conversation_session_id)
                st.session_state.conversation_session_id = rag_system.create_conversation_session()
                st.success("聊天記錄已清空！")
                st.rerun()
    
    with tab2:
        st.header("對話記錄")
        
        # 會話管理
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.session_state.conversation_session_id:
                st.info(f"當前會話ID: {st.session_state.conversation_session_id[:8]}...")
        with col2:
            if st.button("🆕 開始新對話"):
                st.session_state.conversation_session_id = rag_system.create_conversation_session()
                st.success("已開始新的對話會話！")
                st.rerun()
        
        # 顯示對話歷史
        if st.session_state.conversation_session_id:
            conversation_history = rag_system.get_conversation_history(st.session_state.conversation_session_id)
            
            if conversation_history and conversation_history.get('messages'):
                st.subheader("📜 對話歷史")
                
                messages = conversation_history['messages']
                for i, message in enumerate(messages):
                    timestamp = message.get('timestamp', '')
                    if timestamp:
                        time_str = timestamp.split('T')[1][:8] if 'T' in timestamp else timestamp
                    else:
                        time_str = ''
                    
                    if message['type'] in ['user_query', 'user_message']:
                        with st.container():
                            icon = "🙋" if message['type'] == 'user_query' else "💬"
                            label = "用戶查詢" if message['type'] == 'user_query' else "用戶消息"
                            st.markdown(f"**{icon} {label}** `{time_str}`")
                            st.markdown(f"> {message['content']}")
                    
                    elif message['type'] in ['system_response', 'ai_response']:
                        with st.container():
                            icon = "🤖" if message['type'] == 'system_response' else "🤖"
                            label = "AI推薦" if message['type'] == 'system_response' else "AI回應"
                            st.markdown(f"**{icon} {label}** `{time_str}`")
                            with st.expander("查看內容", expanded=True):
                                st.markdown(message['content'])
                                
                                # 顯示推薦的課程
                                if message.get('courses'):
                                    st.write("**相關課程：**")
                                    for course in message['courses'][:3]:  # 只顯示前3個
                                        st.write(f"• {course['title']} ({course['category']})")
                    
                    elif message['type'] == 'user_feedback':
                        with st.container():
                            st.markdown(f"**💬 用戶反饋** `{time_str}`")
                            st.markdown(f"> {message['content']}")
                    
                    st.divider()
                
                # 會話統計
                if st.checkbox("顯示會話統計"):
                    stats = {
                        "總消息數": len(messages),
                        "用戶消息": len([m for m in messages if m['type'] in ['user_query', 'user_message']]),
                        "AI回應": len([m for m in messages if m['type'] in ['system_response', 'ai_response']]),
                        "用戶反饋": len([m for m in messages if m['type'] == 'user_feedback']),
                    }
                    
                    if conversation_history.get('user_preferences'):
                        stats["用戶偏好"] = len(conversation_history['user_preferences'])
                    
                    if conversation_history.get('rejected_courses'):
                        stats["拒絕課程"] = len(conversation_history['rejected_courses'])
                    
                    for key, value in stats.items():
                        st.metric(key, value)
            else:
                st.info("尚無對話記錄，開始搜尋課程來建立對話歷史吧！")
        
        # 清空對話按鈕
        if st.button("🗑️ 清空對話歷史", type="secondary"):
            if st.session_state.conversation_session_id:
                rag_system.clear_conversation(st.session_state.conversation_session_id)
                st.success("對話歷史已清空！")
                st.rerun()
    
    with tab3:
        st.header("瀏覽所有課程")
        
        # 類別選擇
        categories = rag_system.get_all_categories()
        selected_category = st.selectbox("選擇課程類別", ["全部"] + categories)
        
        # 顯示數量選擇
        col1, col2 = st.columns([2, 1])
        with col1:
            show_all = st.checkbox("顯示該類別的所有課程", value=True)
        with col2:
            if not show_all:
                max_courses = st.number_input("最多顯示課程數", min_value=1, max_value=50, value=10)
            else:
                max_courses = None
        
        if selected_category and selected_category != "全部":
            with st.spinner("載入課程中..."):
                courses = rag_system.get_courses_by_category(selected_category, limit=max_courses)
                
                if courses:
                    if show_all:
                        st.success(f"找到 {len(courses)} 個 **{selected_category}** 類別的所有課程：")
                    else:
                        st.info(f"顯示 {len(courses)} 個 **{selected_category}** 課程（最多 {max_courses} 個）：")
                    
                    # 添加搜尋功能
                    if len(courses) > 5:
                        search_term = st.text_input("🔍 在此類別中搜尋課程", placeholder="輸入課程名稱或關鍵字...")
                        if search_term:
                            filtered_courses = [
                                course for course in courses 
                                if search_term.lower() in course['title'].lower() or 
                                   search_term.lower() in course['description'].lower()
                            ]
                            if filtered_courses:
                                st.write(f"搜尋到 {len(filtered_courses)} 個包含「{search_term}」的課程：")
                                courses = filtered_courses
                            else:
                                st.warning(f"沒有找到包含「{search_term}」的課程")
                                courses = []
                    
                    # 顯示課程
                    for i, course in enumerate(courses, 1):
                        with st.expander(f"{i}. {course['title']} ({course['category']})", expanded=False):
                            display_course_card(course, show_similarity=False)
                else:
                    st.info("此類別暫無課程資料")
        else:
            st.info("請選擇一個課程類別來瀏覽相關課程")
    
    with tab4:
        st.header("關於系統")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 系統特色")
            st.write("""
            - **聊天室界面**: 像與朋友聊天一樣與AI互動
            - **對話記憶**: AI會記住完整的對話歷史，保持連貫性
            - **智能判斷**: 自動判斷是課程查詢還是一般聊天
            - **精準推薦**: 使用RAG技術確保推薦的課程真實存在
            - **上下文理解**: 基於對話歷史提供更貼切的回應
            - **無幻覺**: 只推薦資料庫中確實存在的課程
            - **繁體中文**: 完全支援繁體中文對話
            - **即時互動**: 流暢的即時聊天體驗
            """)
            
        with col2:
            st.subheader("⚙️ 技術架構")
            st.write(f"""
            - **LLM模型**: {stats.get('model_name', 'gpt-5-mini')}
            - **嵌入模型**: {stats.get('embedding_model', 'sentence-transformers')}
            - **向量數據庫**: ChromaDB
            - **檢索增強**: RAG (Retrieval-Augmented Generation)
            - **使用者界面**: Streamlit
            """)
        
        st.subheader("📝 使用說明")
        st.write("""
        1. **設定API金鑰**: 在側邊欄輸入您的OpenAI API金鑰
        2. **開始聊天**: 在AI聊天室頁面開始與AI對話
        3. **自然對話**: 可以隨意聊天或詢問課程相關問題
        4. **智能推薦**: 當您提到課程需求時，AI會自動推薦合適的課程
        5. **持續對話**: AI記住所有對話內容，可以持續深入討論
        6. **查看歷史**: 在對話記錄頁面查看完整的聊天歷史
        7. **瀏覽課程**: 也可以直接按類別瀏覽所有課程
        """)
        
        st.subheader("💡 對話範例")
        st.write("""
        **一般聊天：**
        - "你好！"
        - "今天天氣如何？"
        - "你能做什麼？"
        
        **課程相關：**
        - "我想要減肥的課程"
        - "適合初學者的瑜珈"
        - "有什麼運動課程推薦？"
        - "可以放鬆身心的課程"
        
        **持續對話：**
        - "剛才推薦的課程時間不合適"
        - "有沒有週末的課程？"
        - "還有其他選擇嗎？"
        """)

if __name__ == "__main__":
    main() 
