import streamlit as st
import pandas as pd
from typing import Dict, Any
import logging
import os
from config import Config
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
            with st.expander("詳細資訊"):
                for info in additional_info:
                    st.markdown(info)
        
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
        
        # 檔案上傳功能
        st.subheader("📁 檔案上傳")
        uploaded_file = st.file_uploader(
            "上傳新的課程資料檔案",
            type=['json'],
            help="請上傳新的 AI課程.json 檔案來更新課程資料"
        )
        
        if uploaded_file is not None:
            try:
                # 讀取上傳的檔案內容
                file_content = uploaded_file.read()
                
                # 驗證JSON格式
                import json
                json_data = json.loads(file_content.decode('utf-8'))
                
                # 顯示檔案資訊
                st.success(f"✅ 檔案讀取成功")
                st.info(f"📄 檔案名稱: {uploaded_file.name}")
                st.info(f"📊 檔案大小: {len(file_content)} bytes")
                
                # 嘗試計算課程數量
                if isinstance(json_data, list):
                    course_count = len(json_data)
                    st.info(f"📚 包含課程數: {course_count}")
                elif isinstance(json_data, dict) and 'courses' in json_data:
                    course_count = len(json_data['courses'])
                    st.info(f"📚 包含課程數: {course_count}")
                else:
                    st.warning("⚠️ 無法識別課程數量，請確認檔案格式")
                
                # 替換檔案按鈕
                if st.button("🔄 替換現有檔案並重建資料庫", type="primary"):
                    try:
                        # 備份原始檔案
                        import shutil
                        from datetime import datetime
                        backup_name = f"AI課程.json.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        shutil.copy2("AI課程.json", backup_name)
                        st.info(f"✅ 原檔案已備份為: {backup_name}")
                        
                        # 寫入新檔案
                        with open("AI課程.json", "wb") as f:
                            f.write(file_content)
                        
                        st.success("✅ 檔案已成功替換")
                        
                        # 強制重建資料庫
                        with st.spinner("重建資料庫中..."):
                            from auto_file_monitor import force_rebuild_database
                            rebuild_result = force_rebuild_database()
                            
                            if rebuild_result['success']:
                                st.success("✅ 資料庫重建完成！")
                                st.balloons()  # 顯示慶祝動畫
                                st.rerun()  # 重新載入頁面
                            else:
                                st.error(f"❌ 資料庫重建失敗: {rebuild_result['message']}")
                                
                    except Exception as e:
                        st.error(f"❌ 檔案替換失敗: {e}")
                        
            except json.JSONDecodeError as e:
                st.error(f"❌ JSON格式錯誤: {e}")
            except Exception as e:
                st.error(f"❌ 檔案處理失敗: {e}")
        
        st.divider()
        
        # API金鑰設定
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=st.session_state.get('api_key', ''),
            help="請輸入您的OpenAI API金鑰"
        )
        
        if api_key:
            st.session_state['api_key'] = api_key
            # 更新配置
            rag_system.config.OPENAI_API_KEY = api_key
            rag_system.openai_client.api_key = api_key
        
        # 搜尋參數
        st.subheader("🔍 搜尋設定")
        retrieval_k = st.slider("檢索課程數量", 1, 10, 5)
        similarity_threshold = st.slider("相似度閾值", 0.0, 1.0, 0.7, 0.1)
        
        # 更新配置
        rag_system.config.RETRIEVAL_K = retrieval_k
        rag_system.config.SIMILARITY_THRESHOLD = similarity_threshold
        
        # 系統統計
        st.subheader("📊 系統統計")
        stats = rag_system.get_system_stats()
        st.metric("總課程數", stats.get('total_courses', 0))
        st.metric("課程類別數", stats.get('total_categories', 0))
        
        # 資料檔案資訊
        st.subheader("📄 資料檔案資訊")
        st.write(f"**檔案大小**: {stats.get('data_file_size', '未知')}")
        st.write(f"**最後修改**: {stats.get('data_file_last_modified', '未知')}")
        st.write(f"**最後檢查**: {stats.get('last_update_check', '未知')}")
        
        # 自動更新檢查
        from auto_file_monitor import check_and_update_data, get_file_monitor, force_rebuild_database
        
        # 手動更新按鈕
        if st.button("🔄 檢查資料更新", help="點擊檢查資料檔案是否有更新"):
            with st.spinner("檢查資料更新中..."):
                update_result = check_and_update_data()
                if update_result['updated']:
                    st.success(f"✅ {update_result['message']}")
                    st.rerun()  # 重新載入頁面
                else:
                    st.info(f"ℹ️ {update_result['message']}")
        
        # 強制重建按鈕
        if st.button("🔄 強制重建資料庫", help="強制重建資料庫並清理快取"):
            with st.spinner("重建資料庫中..."):
                rebuild_result = force_rebuild_database()
                if rebuild_result['success']:
                    st.success(f"✅ {rebuild_result['message']}")
                    st.rerun()
                else:
                    st.error(f"❌ {rebuild_result['message']}")
        
        # 顯示所有類別
        if st.checkbox("顯示所有類別"):
            categories = stats.get('categories', [])
            for category in categories:
                st.write(f"• {category}")
        
        # 快取清理選項
        st.divider()
        if st.button("🔄 清理快取並重新載入", help="如果遇到方法錯誤，點擊此按鈕清理快取"):
            st.cache_resource.clear()
            st.rerun()
    
    # 主要內容區域
    tab1, tab2, tab3 = st.tabs(["🔍 智能推薦", "📚 瀏覽課程", "ℹ️ 關於系統"])
    
    with tab1:
        st.header("智能課程推薦")
        st.write("請描述您想要的課程類型或需求，我會為您推薦最適合的課程。")
        
        # 初始化查詢狀態
        if 'query_text' not in st.session_state:
            st.session_state.query_text = ""
        
        # 範例查詢按鈕
        st.write("**快速範例：**")
        col1, col2, col3, col4 = st.columns(4)
        
        example_queries = {
            "🔥 減肥燃脂": "我想要減肥燃脂的課程",
            "🧘 瑜珈放鬆": "適合初學者的瑜珈課程", 
            "🏊 游泳訓練": "游泳教學課程",
            "⚽ 球類運動": "球類運動課程"
        }
        
        cols = [col1, col2, col3, col4]
        for i, (button_text, example_query) in enumerate(example_queries.items()):
            with cols[i]:
                if st.button(button_text, key=f"example_{i}"):
                    st.session_state.query_text = example_query
                    st.rerun()
        
        # 查詢輸入
        query = st.text_input(
            "請輸入您的需求",
            value=st.session_state.query_text,
            placeholder="例如：我想要減肥燃脂的課程、適合初學者的瑜珈課程、能夠增強體力的運動課程...",
            key="query_input"
        )
        
        # 同步session state
        if query != st.session_state.query_text:
            st.session_state.query_text = query
        
        # 搜尋按鈕
        if st.button("🔍 搜尋推薦", type="primary") and query:
            if not api_key:
                st.error("請先在側邊欄輸入OpenAI API金鑰！")
            else:
                with st.spinner("正在分析您的需求並搜尋最適合的課程..."):
                    try:
                        result = rag_system.get_course_recommendation(query, retrieval_k)
                        
                        if result['success']:
                            st.success("找到符合您需求的課程！")
                            
                            # 顯示AI推薦
                            st.subheader("🤖 AI推薦")
                            st.markdown(result['recommendation'])
                            
                            # 顯示檢索到的課程
                            if result['retrieved_courses']:
                                st.subheader("📋 相關課程詳情")
                                for course in result['retrieved_courses']:
                                    display_course_card(course)
                        else:
                            st.warning(result['recommendation'])
                            
                    except Exception as e:
                        st.error(f"搜尋過程中發生錯誤: {e}")
    
    with tab2:
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
    
    with tab3:
        st.header("關於系統")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 系統特色")
            st.write("""
            - **精準推薦**: 使用RAG技術確保推薦的課程真實存在
            - **智能檢索**: 基於語意搜索找到最相關的課程
            - **無幻覺**: 只推薦資料庫中確實存在的課程
            - **繁體中文**: 完全支援繁體中文查詢和回應
            - **即時回應**: 快速提供個人化課程建議
            """)
            
        with col2:
            st.subheader("⚙️ 技術架構")
            st.write(f"""
            - **LLM模型**: {stats.get('model_name', 'GPT-4o-mini')}
            - **嵌入模型**: {stats.get('embedding_model', 'sentence-transformers')}
            - **向量數據庫**: ChromaDB
            - **檢索增強**: RAG (Retrieval-Augmented Generation)
            - **使用者界面**: Streamlit
            """)
        
        st.subheader("📝 使用說明")
        st.write("""
        1. **設定API金鑰**: 在側邊欄輸入您的OpenAI API金鑰
        2. **描述需求**: 在智能推薦頁面輸入您想要的課程類型
        3. **查看推薦**: 系統會為您推薦最適合的課程
        4. **瀏覽課程**: 也可以直接按類別瀏覽所有課程
        """)
        
        st.subheader("💡 查詢範例")
        st.write("""
        - "我想要減肥的課程"
        - "適合初學者的瑜珈"
        - "高強度的有氧運動"
        - "可以放鬆身心的課程"
        - "游泳教學"
        - "球類運動課程"
        """)

if __name__ == "__main__":
    main() 