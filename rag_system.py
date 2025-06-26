import openai
from typing import List, Dict, Any, Optional
import logging
from config import Config
from vector_store import VectorStore
from course_processor import CourseProcessor

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGSystem:
    """RAG課程推薦系統 - 整合檢索增強生成功能"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.vector_store = None
        self.course_processor = None
        self.openai_client = None
        self.setup_system()
    
    def setup_system(self):
        """初始化RAG系統"""
        try:
            # 設定OpenAI API
            openai.api_key = self.config.OPENAI_API_KEY
            self.openai_client = openai.OpenAI(api_key=self.config.OPENAI_API_KEY)
            
            # 初始化課程處理器
            self.course_processor = CourseProcessor(self.config.COURSE_DATA_PATH)
            
            # 初始化向量數據庫
            self.vector_store = VectorStore(self.config)
            
            logger.info("RAG系統初始化完成")
            
        except Exception as e:
            logger.error(f"RAG系統初始化失敗: {e}")
            raise
    
    def initialize_knowledge_base(self, force_rebuild: bool = False):
        """初始化知識庫"""
        try:
            # 檢查是否已有數據
            stats = self.vector_store.get_collection_stats()
            if stats.get('total_courses', 0) > 0 and not force_rebuild:
                logger.info(f"知識庫已存在，包含 {stats['total_courses']} 筆課程")
                return
            
            # 重新建立知識庫
            logger.info("開始建立知識庫...")
            
            # 處理課程數據
            courses_data = self.course_processor.prepare_for_vectorization()
            
            if force_rebuild:
                self.vector_store.reset_collection()
            
            # 添加到向量數據庫
            self.vector_store.add_courses(courses_data)
            
            logger.info("知識庫建立完成")
            
        except Exception as e:
            logger.error(f"初始化知識庫失敗: {e}")
            raise
    
    def retrieve_relevant_courses(self, query: str, k: int = None) -> List[Dict[str, Any]]:
        """檢索相關課程"""
        try:
            k = k or self.config.RETRIEVAL_K
            relevant_courses = self.vector_store.search_similar_courses(query, k)
            
            # 記錄檢索結果
            logger.info(f"檢索到 {len(relevant_courses)} 個相關課程")
            for course in relevant_courses:
                logger.debug(f"課程: {course['title']}, 相似度: {course['similarity_score']:.3f}")
            
            return relevant_courses
            
        except Exception as e:
            logger.error(f"檢索相關課程失敗: {e}")
            return []
    
    def generate_course_recommendation(self, query: str, retrieved_courses: List[Dict[str, Any]]) -> str:
        """使用GPT-4.1 mini生成課程推薦"""
        try:
            if not retrieved_courses:
                return "抱歉，我找不到符合您需求的課程。請嘗試用不同的關鍵字搜尋。"
            
            # 構建系統提示
            system_prompt = """你是一個專業的課程推薦助手。基於提供的課程資訊，為用戶推薦最適合的課程。

重要原則：
1. 只推薦提供的課程資訊中存在的課程，絕對不能虛構或推薦不存在的課程
2. 根據用戶需求和課程匹配度進行排序推薦
3. 提供具體且實用的推薦理由
4. 用繁體中文回答
5. 格式要清晰，包含課程名稱、類別、介紹和推薦理由

如果沒有找到完全匹配的課程，要誠實說明，並推薦最相近的替代選項。"""

            # 構建用戶查詢上下文
            context_parts = []
            context_parts.append(f"用戶查詢: {query}\n")
            context_parts.append("相關課程資訊:")
            
            for i, course in enumerate(retrieved_courses, 1):
                context_parts.append(f"\n{i}. 課程名稱: {course['title']}")
                context_parts.append(f"   類別: {course['category']}")
                context_parts.append(f"   介紹: {course['description']}")
                context_parts.append(f"   相似度: {course['similarity_score']:.3f}")
                
                # 添加額外的元數據資訊
                metadata = course.get('metadata', {})
                additional_info = []
                for key in ['meta_授課教師', 'meta_年齡限制', 'meta_上課時間', 'meta_課程費用', 'meta_體驗費用']:
                    if key in metadata and metadata[key]:
                        field_name = key.replace('meta_', '')
                        additional_info.append(f"{field_name}: {metadata[key]}")
                
                if additional_info:
                    context_parts.append(f"   詳細資訊: {', '.join(additional_info)}")
            
            user_prompt = "\n".join(context_parts)
            user_prompt += "\n\n請根據以上課程資訊，為用戶提供最適合的課程推薦："
            
            # 呼叫GPT-4.1 mini
            response = self.openai_client.chat.completions.create(
                model=self.config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1500,
                top_p=0.9
            )
            
            recommendation = response.choices[0].message.content.strip()
            logger.info(f"生成推薦完成，長度: {len(recommendation)} 字符")
            
            return recommendation
            
        except Exception as e:
            logger.error(f"生成課程推薦失敗: {e}")
            return "抱歉，生成推薦時發生錯誤。請稍後再試。"
    
    def get_course_recommendation(self, query: str, k: int = None) -> Dict[str, Any]:
        """獲取課程推薦（完整流程）"""
        try:
            logger.info(f"開始處理查詢: {query}")
            
            # 1. 檢索相關課程
            retrieved_courses = self.retrieve_relevant_courses(query, k)
            
            if not retrieved_courses:
                return {
                    'query': query,
                    'retrieved_courses': [],
                    'recommendation': "抱歉，我找不到符合您需求的課程。請嘗試用不同的關鍵字搜尋，例如：'有氧運動'、'瑜珈'、'游泳'、'球類運動'等。",
                    'success': False
                }
            
            # 2. 生成推薦
            recommendation = self.generate_course_recommendation(query, retrieved_courses)
            
            return {
                'query': query,
                'retrieved_courses': retrieved_courses,
                'recommendation': recommendation,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"獲取課程推薦失敗: {e}")
            return {
                'query': query,
                'retrieved_courses': [],
                'recommendation': f"系統發生錯誤: {str(e)}",
                'success': False
            }
    
    def get_courses_by_category(self, category: str) -> List[Dict[str, Any]]:
        """根據類別獲取課程"""
        try:
            return self.vector_store.get_courses_by_category(category)
        except Exception as e:
            logger.error(f"根據類別獲取課程失敗: {e}")
            return []
    
    def get_all_categories(self) -> List[str]:
        """獲取所有課程類別"""
        try:
            return self.course_processor.get_course_categories()
        except Exception as e:
            logger.error(f"獲取課程類別失敗: {e}")
            return []
    
    def get_system_stats(self) -> Dict[str, Any]:
        """獲取系統統計資訊"""
        try:
            vector_stats = self.vector_store.get_collection_stats()
            categories = self.get_all_categories()
            
            return {
                'total_courses': vector_stats.get('total_courses', 0),
                'total_categories': len(categories),
                'categories': categories,
                'collection_name': vector_stats.get('collection_name', ''),
                'model_name': self.config.MODEL_NAME,
                'embedding_model': self.config.EMBEDDING_MODEL
            }
        except Exception as e:
            logger.error(f"獲取系統統計失敗: {e}")
            return {} 