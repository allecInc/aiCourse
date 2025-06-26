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
        config = Config()
        rag_system = RAGSystem(config)
        
        # 檢查並初始化知識庫
        with st.spinner("正在初始化知識庫..."):
            rag_system.initialize_knowledge_base()
        
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
    
    # 側邊欄
    with st.sidebar:
        st.header("⚙️ 系統設定")
        
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
        
        # 顯示所有類別
        if st.checkbox("顯示所有類別"):
            categories = stats.get('categories', [])
            for category in categories:
                st.write(f"• {category}")
    
    # 主要內容區域
    tab1, tab2, tab3 = st.tabs(["🔍 智能推薦", "📚 瀏覽課程", "ℹ️ 關於系統"])
    
    with tab1:
        st.header("智能課程推薦")
        st.write("請描述您想要的課程類型或需求，我會為您推薦最適合的課程。")
        
        # 查詢輸入
        query = st.text_input(
            "請輸入您的需求",
            placeholder="例如：我想要減肥燃脂的課程、適合初學者的瑜珈課程、能夠增強體力的運動課程...",
            key="query_input"
        )
        
        # 範例查詢按鈕
        st.write("**快速範例：**")
        col1, col2, col3, col4 = st.columns(4)
        
        example_queries = {
            "🔥 減肥燃脂": "我想要減肥燃脂的課程",
            "🧘 瑜珈放鬆": "適合初學者的瑜珈課程", 
            "🏊 游泳訓練": "游泳教學課程",
            "⚽ 球類運動": "球類運動課程"
        }
        
        # 初始化selected_example
        if 'selected_example' not in st.session_state:
            st.session_state.selected_example = None
        
        cols = [col1, col2, col3, col4]
        for i, (button_text, example_query) in enumerate(example_queries.items()):
            with cols[i]:
                if st.button(button_text, key=f"example_{i}"):
                    st.session_state.selected_example = example_query
                    st.rerun()
        
        # 如果選擇了範例，自動填入查詢框
        if st.session_state.selected_example and not query:
            query = st.session_state.selected_example
            st.session_state.selected_example = None  # 清除選擇
        
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
        
        if selected_category and selected_category != "全部":
            with st.spinner("載入課程中..."):
                courses = rag_system.get_courses_by_category(selected_category)
                
                if courses:
                    st.write(f"找到 {len(courses)} 個 {selected_category} 課程：")
                    for course in courses:
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