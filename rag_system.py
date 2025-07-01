import openai
from typing import List, Dict, Any, Optional
import logging
import os
import time
from datetime import datetime
from config import Config
from vector_store import VectorStore
from course_processor import CourseProcessor
from conversation_manager import ConversationManager

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
        self.conversation_manager = ConversationManager()  # 新增對話管理器
        self.last_data_file_mtime = None  # 記錄資料檔案的最後修改時間
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
    
    def initialize_knowledge_base(self, force_rebuild: bool = False, check_updates: bool = True):
        """初始化知識庫"""
        try:
            # 檢查資料檔案是否更新
            if check_updates and self._should_update_data():
                logger.info("檢測到資料檔案已更新，重新建立知識庫...")
                force_rebuild = True
            
            # 檢查是否已有數據
            stats = self.vector_store.get_collection_stats()
            
            # 如果集合有錯誤或資料為空，強制重建
            if stats.get('total_courses', 0) == 0:
                logger.info("知識庫為空或有錯誤，需要重建...")
                force_rebuild = True
            elif not force_rebuild:
                logger.info(f"知識庫已存在，包含 {stats['total_courses']} 筆課程")
                # 更新檔案修改時間記錄
                self._update_file_mtime()
                return
            
            # 重新建立知識庫
            logger.info("開始建立知識庫...")
            
            # 處理課程數據
            courses_data = self.course_processor.prepare_for_vectorization()
            
            if force_rebuild:
                self.vector_store.reset_collection()
            
            # 添加到向量數據庫
            self.vector_store.add_courses(courses_data)
            
            # 更新檔案修改時間記錄
            self._update_file_mtime()
            
            logger.info("知識庫建立完成")
            
        except Exception as e:
            logger.error(f"初始化知識庫失敗: {e}")
            raise
    
    def retrieve_relevant_courses(self, query: str, k: int = None) -> List[Dict[str, Any]]:
        """檢索相關課程"""
        try:
            k = k or self.config.RETRIEVAL_K
            relevant_courses = self.vector_store.search_similar_courses(query, k)
            
            # 如果返回空結果且可能是集合錯誤，嘗試重建
            if not relevant_courses:
                logger.info("檢索結果為空，檢查是否需要重建知識庫...")
                stats = self.vector_store.get_collection_stats()
                if stats.get('total_courses', 0) == 0:
                    logger.info("知識庫似乎有問題，嘗試重建...")
                    try:
                        self.initialize_knowledge_base(force_rebuild=True, check_updates=False)
                        # 重新嘗試檢索
                        relevant_courses = self.vector_store.search_similar_courses(query, k)
                    except Exception as rebuild_error:
                        logger.error(f"重建知識庫失敗: {rebuild_error}")
                        # 如果重建失敗，返回空結果但不崩潰
            
            # 記錄檢索結果
            logger.info(f"檢索到 {len(relevant_courses)} 個相關課程")
            for course in relevant_courses:
                logger.debug(f"課程: {course['title']}, 相似度: {course['similarity_score']:.3f}")
            
            return relevant_courses
            
        except Exception as e:
            logger.error(f"檢索相關課程失敗: {e}")
            # 如果出現集合不存在的錯誤，嘗試重建
            if "does not exists" in str(e) or "Collection" in str(e):
                logger.info("檢測到集合錯誤，嘗試重建知識庫...")
                try:
                    self.initialize_knowledge_base(force_rebuild=True, check_updates=False)
                    # 重新嘗試檢索
                    return self.vector_store.search_similar_courses(query, k)
                except Exception as rebuild_error:
                    logger.error(f"重建後仍然失敗: {rebuild_error}")
            return []
    
    def generate_course_recommendation(self, query: str, retrieved_courses: List[Dict[str, Any]], 
                                      session_id: str = None) -> str:
        """使用GPT-4.1 mini生成課程推薦，支援對話上下文"""
        try:
            if not retrieved_courses:
                return "抱歉，我找不到符合您需求的課程。請嘗試用不同的關鍵字搜尋。"
            
            # 獲取對話上下文
            context = {}
            if session_id:
                context = self.conversation_manager.get_conversation_context(session_id)
            
            # 構建系統提示
            system_prompt = """你是一個專業的課程推薦助手。基於提供的課程資訊和對話歷史，為用戶推薦最適合的課程。

重要原則：
1. 只推薦提供的課程資訊中存在的課程，絕對不能虛構或推薦不存在的課程
2. 根據用戶需求、對話歷史和課程匹配度進行排序推薦
3. 考慮用戶的偏好和之前拒絕的課程
4. 提供具體且實用的推薦理由
5. 用繁體中文回答
6. 格式要清晰，包含課程名稱、類別、介紹和推薦理由
7. 如果用戶有反饋或偏好，要特別注意避免推薦類似的不合適課程

如果沒有找到完全匹配的課程，要誠實說明，並推薦最相近的替代選項。"""

            # 構建用戶查詢上下文
            context_parts = []
            context_parts.append(f"用戶查詢: {query}\n")
            
            # 添加對話歷史和用戶偏好
            if context:
                if context.get("user_preferences"):
                    context_parts.append("用戶偏好:")
                    for pref, value in context["user_preferences"].items():
                        if value:
                            pref_name = pref.replace("_sensitive", "").replace("_", " ")
                            context_parts.append(f"  - 特別關注: {pref_name}")
                
                if context.get("rejected_courses"):
                    context_parts.append(f"用戶之前拒絕的課程: {len(context['rejected_courses'])} 個")
                
                if context.get("messages"):
                    recent_messages = context["messages"][-3:]  # 最近3條消息
                    context_parts.append("最近的對話:")
                    for msg in recent_messages:
                        if msg["type"] == "user_feedback":
                            context_parts.append(f"  - 用戶反饋: {msg['content']}")
            
            context_parts.append("\n相關課程資訊:")
            
            for i, course in enumerate(retrieved_courses, 1):
                # 檢查課程是否在拒絕列表中
                rejected = context.get("rejected_courses", [])
                status = " (用戶之前拒絕)" if course['title'] in rejected else ""
                
                context_parts.append(f"\n{i}. 課程名稱: {course['title']}{status}")
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
            user_prompt += "\n\n請根據以上課程資訊和對話歷史，為用戶提供最適合的課程推薦："
            
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
    
    def get_course_recommendation(self, query: str, k: int = None, session_id: str = None) -> Dict[str, Any]:
        """獲取課程推薦（完整流程）"""
        try:
            logger.info(f"開始處理查詢: {query}")
            
            # 如果有會話ID，使用對話上下文優化查詢
            if session_id:
                refined_query = self.conversation_manager.get_refined_query(session_id, query)
                logger.info(f"原始查詢: {query}")
                logger.info(f"優化查詢: {refined_query}")
                # 記錄用戶查詢
                self.conversation_manager.add_message(session_id, "user_query", query)
            else:
                refined_query = query
            
            # 1. 檢索相關課程
            retrieved_courses = self.retrieve_relevant_courses(refined_query, k)
            
            if not retrieved_courses:
                return {
                    'query': query,
                    'retrieved_courses': [],
                    'recommendation': "抱歉，我找不到符合您需求的課程。請嘗試用不同的關鍵字搜尋，例如：'有氧運動'、'瑜珈'、'游泳'、'球類運動'等。",
                    'success': False
                }
            
            # 2. 生成推薦
            recommendation = self.generate_course_recommendation(query, retrieved_courses, session_id)
            
            # 記錄系統回應
            if session_id:
                self.conversation_manager.add_message(
                    session_id, "system_response", recommendation, 
                    courses=retrieved_courses
                )
            
            return {
                'query': query,
                'retrieved_courses': retrieved_courses,
                'recommendation': recommendation,
                'success': True,
                'session_id': session_id
            }
            
        except Exception as e:
            logger.error(f"獲取課程推薦失敗: {e}")
            return {
                'query': query,
                'retrieved_courses': [],
                'recommendation': f"系統發生錯誤: {str(e)}",
                'success': False
            }
    
    def get_courses_by_category(self, category: str, limit: int = None) -> List[Dict[str, Any]]:
        """根據類別獲取課程"""
        try:
            courses = self.vector_store.get_courses_by_category(category, limit)
            
            # 如果返回空結果且可能是集合錯誤，嘗試重建
            if not courses:
                stats = self.vector_store.get_collection_stats()
                if stats.get('total_courses', 0) == 0:
                    logger.info("知識庫似乎有問題，嘗試重建...")
                    self.initialize_knowledge_base(force_rebuild=True, check_updates=False)
                    # 重新嘗試獲取
                    courses = self.vector_store.get_courses_by_category(category, limit)
            
            return courses
        except Exception as e:
            logger.error(f"根據類別獲取課程失敗: {e}")
            # 如果出現集合不存在的錯誤，嘗試重建
            if "does not exists" in str(e) or "Collection" in str(e):
                logger.info("檢測到集合錯誤，嘗試重建知識庫...")
                try:
                    self.initialize_knowledge_base(force_rebuild=True, check_updates=False)
                    # 重新嘗試獲取
                    return self.vector_store.get_courses_by_category(category, limit)
                except Exception as rebuild_error:
                    logger.error(f"重建後仍然失敗: {rebuild_error}")
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
            
            # 獲取資料檔案資訊
            data_file_info = self._get_data_file_info()
            
            return {
                'total_courses': vector_stats.get('total_courses', 0),
                'total_categories': len(categories),
                'categories': categories,
                'collection_name': vector_stats.get('collection_name', ''),
                'model_name': self.config.MODEL_NAME,
                'embedding_model': self.config.EMBEDDING_MODEL,
                'data_file_last_modified': data_file_info.get('last_modified', '未知'),
                'data_file_size': data_file_info.get('size', 0),
                'last_update_check': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            logger.error(f"獲取系統統計失敗: {e}")
            return {}
    
    def _should_update_data(self) -> bool:
        """檢查是否需要更新資料"""
        try:
            if not os.path.exists(self.config.COURSE_DATA_PATH):
                logger.warning(f"資料檔案不存在: {self.config.COURSE_DATA_PATH}")
                return False
            
            current_mtime = os.path.getmtime(self.config.COURSE_DATA_PATH)
            
            # 如果是第一次檢查，先檢查知識庫是否有資料
            if self.last_data_file_mtime is None:
                stats = self.vector_store.get_collection_stats()
                if stats.get('total_courses', 0) == 0:
                    # 知識庫為空，需要載入資料
                    logger.info("知識庫為空，需要載入資料")
                    self.last_data_file_mtime = current_mtime
                    return True
                else:
                    # 知識庫有資料，記錄檔案時間
                    self.last_data_file_mtime = current_mtime
                    return False
            
            # 檢查檔案是否已更新
            if current_mtime > self.last_data_file_mtime:
                logger.info(f"檔案已更新，舊時間: {datetime.fromtimestamp(self.last_data_file_mtime)}, "
                           f"新時間: {datetime.fromtimestamp(current_mtime)}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"檢查檔案更新失敗: {e}")
            return False
    
    def _update_file_mtime(self):
        """更新檔案修改時間記錄"""
        try:
            if os.path.exists(self.config.COURSE_DATA_PATH):
                self.last_data_file_mtime = os.path.getmtime(self.config.COURSE_DATA_PATH)
                logger.debug(f"更新檔案修改時間記錄: {datetime.fromtimestamp(self.last_data_file_mtime)}")
        except Exception as e:
            logger.error(f"更新檔案修改時間失敗: {e}")
    
    def _get_data_file_info(self) -> Dict[str, Any]:
        """獲取資料檔案資訊"""
        try:
            if not os.path.exists(self.config.COURSE_DATA_PATH):
                return {'last_modified': '檔案不存在', 'size': 0}
            
            mtime = os.path.getmtime(self.config.COURSE_DATA_PATH)
            size = os.path.getsize(self.config.COURSE_DATA_PATH)
            
            return {
                'last_modified': datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
                'size': f"{size / 1024:.1f} KB"
            }
        except Exception as e:
            logger.error(f"獲取檔案資訊失敗: {e}")
            return {'last_modified': '錯誤', 'size': 0}
    
    def check_and_reload_if_updated(self) -> Dict[str, Any]:
        """檢查並重新載入更新的資料"""
        try:
            if self._should_update_data():
                logger.info("檢測到資料更新，開始重新載入...")
                self.initialize_knowledge_base(force_rebuild=True, check_updates=False)
                return {
                    'updated': True,
                    'message': '資料已成功更新',
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                return {
                    'updated': False,
                    'message': '資料無更新',
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        except Exception as e:
            logger.error(f"檢查和重新載入失敗: {e}")
            return {
                'updated': False,
                'message': f'錯誤: {str(e)}',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def chat_with_user(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """聊天功能 - 處理用戶的聊天消息"""
        try:
            # 記錄用戶消息
            self.conversation_manager.add_message(session_id, "user_message", user_message)
            
            # 獲取對話上下文
            context = self.conversation_manager.get_conversation_context(session_id)
            
            # 判斷用戶是否在詢問課程相關問題
            is_course_query = self._is_course_related_query(user_message)
            
            if is_course_query:
                # 如果是課程相關查詢，使用RAG系統
                result = self.get_course_recommendation(user_message, session_id=session_id)
                ai_response = result['recommendation']
                courses = result.get('retrieved_courses', [])
            else:
                # 如果是一般聊天，使用對話功能
                ai_response = self._generate_chat_response(user_message, context)
                courses = []
            
            # 記錄AI回應
            self.conversation_manager.add_message(
                session_id, "ai_response", ai_response, courses=courses
            )
            
            return {
                'success': True,
                'ai_response': ai_response,
                'courses': courses,
                'is_course_query': is_course_query
            }
            
        except Exception as e:
            logger.error(f"聊天處理失敗: {e}")
            error_response = "抱歉，我遇到了一些問題。請稍後再試。"
            
            # 記錄錯誤回應
            self.conversation_manager.add_message(session_id, "ai_response", error_response)
            
            return {
                'success': False,
                'ai_response': error_response,
                'courses': [],
                'is_course_query': False
            }
    
    def _is_course_related_query(self, message: str) -> bool:
        """判斷消息是否與課程相關"""
        course_keywords = [
            '課程', '推薦', '學習', '教學', '訓練', '班級', '報名', '上課',
            '減肥', '瑜珈', '游泳', '健身', '運動', '舞蹈', '音樂', '繪畫',
            '語言', '電腦', '程式', '設計', '攝影', '烹飪', '手工', '才藝'
        ]
        
        return any(keyword in message for keyword in course_keywords)
    
    def _generate_chat_response(self, user_message: str, context: Dict[str, Any]) -> str:
        """生成聊天回應"""
        try:
            # 構建聊天提示
            system_prompt = """你是一個友善的AI課程推薦助手。你可以：
1. 推薦和介紹各種課程
2. 回答關於課程的問題  
3. 進行日常聊天
4. 記住對話歷史並保持連貫性

請用繁體中文回應，保持友善和專業的語調。如果用戶沒有明確要求課程推薦，可以進行一般對話，但要適時引導到課程相關話題。"""

            # 構建對話歷史
            chat_history = []
            if context.get('messages'):
                recent_messages = context['messages'][-6:]  # 最近6條消息
                for msg in recent_messages:
                    if msg['type'] == 'user_message':
                        chat_history.append(f"用戶: {msg['content']}")
                    elif msg['type'] == 'ai_response':
                        chat_history.append(f"助手: {msg['content']}")
            
            # 構建完整提示
            conversation_context = "\n".join(chat_history) if chat_history else "這是對話的開始。"
            
            user_prompt = f"""對話歷史:
{conversation_context}

用戶剛剛說: {user_message}

請根據對話歷史給出適當的回應。如果用戶在詢問課程相關問題，可以引導他們使用更具體的描述來獲得課程推薦。"""

            # 呼叫GPT
            response = self.openai_client.chat.completions.create(
                model=self.config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,
                max_tokens=800,
                top_p=0.9
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"生成聊天回應失敗: {e}")
            return "我好像有點不太明白，可以換個方式說嗎？或者告訴我您想了解什麼樣的課程？"
    
    def handle_user_feedback(self, session_id: str, feedback_content: str, 
                           feedback_type: str = "dissatisfied", 
                           rejected_courses: List[str] = None,
                           reasons: List[str] = None) -> Dict[str, Any]:
        """處理用戶反饋"""
        try:
            # 記錄反饋
            success = self.conversation_manager.add_user_feedback(
                session_id, feedback_type, feedback_content, 
                rejected_courses, reasons
            )
            
            if not success:
                return {
                    'success': False,
                    'message': '記錄反饋失敗',
                    'followup_questions': []
                }
            
            # 記錄反饋消息
            self.conversation_manager.add_message(session_id, "user_feedback", feedback_content)
            
            # 生成追問問題
            followup_questions = self.conversation_manager.generate_followup_questions(
                session_id, feedback_content
            )
            
            return {
                'success': True,
                'message': '感謝您的反饋！',
                'followup_questions': followup_questions,
                'should_ask_followup': len(followup_questions) > 0
            }
            
        except Exception as e:
            logger.error(f"處理用戶反饋失敗: {e}")
            return {
                'success': False,
                'message': f'處理反饋時發生錯誤: {str(e)}',
                'followup_questions': []
            }
    
    def create_conversation_session(self, user_id: str = None) -> str:
        """創建新的對話會話"""
        return self.conversation_manager.create_session(user_id)
    
    def get_conversation_history(self, session_id: str) -> Dict[str, Any]:
        """獲取對話歷史"""
        return self.conversation_manager.get_conversation_context(session_id)
    
    def clear_conversation(self, session_id: str):
        """清空對話歷史"""
        self.conversation_manager.clear_session(session_id) 