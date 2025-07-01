import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConversationManager:
    """對話管理器 - 負責處理對話上下文和用戶反饋"""
    
    def __init__(self):
        self.conversations = {}  # 存儲所有對話會話
        self.session_file = "conversations.json"
        self.load_conversations()
    
    def create_session(self, user_id: str = None) -> str:
        """創建新的對話會話"""
        session_id = user_id or str(uuid.uuid4())
        self.conversations[session_id] = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "messages": [],
            "user_preferences": {},
            "rejected_courses": [],  # 用戶不滿意的課程
            "preferred_features": {},  # 用戶偏好的特徵
            "feedback_history": []  # 反饋歷史
        }
        self.save_conversations()
        return session_id
    
    def add_message(self, session_id: str, message_type: str, content: str, 
                   courses: List[Dict] = None, metadata: Dict = None):
        """添加消息到對話歷史"""
        if session_id not in self.conversations:
            session_id = self.create_session(session_id)
        
        message = {
            "timestamp": datetime.now().isoformat(),
            "type": message_type,  # 'user_query', 'system_response', 'user_feedback', 'user_message', 'ai_response'
            "content": content,
            "courses": courses or [],
            "metadata": metadata or {}
        }
        
        self.conversations[session_id]["messages"].append(message)
        self.save_conversations()
        logger.info(f"會話 {session_id} 添加 {message_type} 消息")
    
    def add_user_feedback(self, session_id: str, feedback_type: str, 
                         feedback_content: str, rejected_courses: List[str] = None,
                         reasons: List[str] = None):
        """處理用戶反饋"""
        if session_id not in self.conversations:
            return False
        
        feedback = {
            "timestamp": datetime.now().isoformat(),
            "type": feedback_type,  # 'dissatisfied', 'partially_satisfied', 'satisfied'
            "content": feedback_content,
            "rejected_courses": rejected_courses or [],
            "reasons": reasons or []
        }
        
        # 更新會話的反饋歷史
        self.conversations[session_id]["feedback_history"].append(feedback)
        
        # 更新拒絕的課程列表
        if rejected_courses:
            self.conversations[session_id]["rejected_courses"].extend(rejected_courses)
        
        # 分析原因並更新偏好
        self._analyze_feedback_and_update_preferences(session_id, feedback)
        
        self.save_conversations()
        return True
    
    def _analyze_feedback_and_update_preferences(self, session_id: str, feedback: Dict):
        """分析用戶反饋並更新偏好"""
        reasons = feedback.get("reasons", [])
        preferences = self.conversations[session_id]["user_preferences"]
        
        # 根據反饋原因更新偏好
        for reason in reasons:
            if "時間" in reason:
                preferences["time_sensitive"] = True
            elif "費用" in reason or "價格" in reason:
                preferences["price_sensitive"] = True
            elif "難度" in reason or "程度" in reason:
                preferences["difficulty_sensitive"] = True
            elif "地點" in reason or "位置" in reason:
                preferences["location_sensitive"] = True
            elif "教師" in reason or "老師" in reason:
                preferences["instructor_sensitive"] = True
    
    def get_conversation_context(self, session_id: str) -> Dict[str, Any]:
        """獲取對話上下文"""
        if session_id not in self.conversations:
            return {}
        
        conversation = self.conversations[session_id]
        return {
            "messages": conversation["messages"][-10:],  # 最近10條消息
            "user_preferences": conversation["user_preferences"],
            "rejected_courses": conversation["rejected_courses"],
            "feedback_count": len(conversation["feedback_history"])
        }
    
    def generate_followup_questions(self, session_id: str, feedback_content: str) -> List[str]:
        """根據用戶反饋生成追問問題"""
        context = self.get_conversation_context(session_id)
        
        # 基本追問問題
        questions = []
        
        if "不適合" in feedback_content or "不符合" in feedback_content:
            questions.extend([
                "能告訴我具體哪方面不符合您的需求嗎？",
                "是時間安排、費用、難度程度，還是其他方面的問題？"
            ])
        
        if "時間" in feedback_content:
            questions.extend([
                "您比較偏好什麼時段的課程？",
                "是希望平日還是假日的課程？"
            ])
        
        if "費用" in feedback_content or "貴" in feedback_content:
            questions.extend([
                "您希望的課程費用大概在什麼範圍內？",
                "您是否考慮體驗課程或優惠方案？"
            ])
        
        if "難度" in feedback_content:
            questions.extend([
                "您希望的課程難度如何？初學者、進階還是專業級？",
                "您之前有相關經驗嗎？"
            ])
        
        # 如果沒有具體問題，使用通用問題
        if not questions:
            questions = [
                "能更詳細地描述您理想中的課程嗎？",
                "除了剛才推薦的課程，您還有其他特殊需求嗎？",
                "您最看重課程的哪個方面？例如教學品質、價格、時間彈性等？"
            ]
        
        return questions[:3]  # 最多返回3個問題
    
    def should_ask_followup(self, session_id: str) -> bool:
        """判斷是否應該追問"""
        if session_id not in self.conversations:
            return False
        
        feedback_history = self.conversations[session_id]["feedback_history"]
        
        # 如果沒有反饋或反饋次數少，應該追問
        if len(feedback_history) == 0:
            return False
        
        # 如果最近的反饋是不滿意的，應該追問
        latest_feedback = feedback_history[-1]
        return latest_feedback["type"] in ["dissatisfied", "partially_satisfied"]
    
    def get_refined_query(self, session_id: str, original_query: str) -> str:
        """根據對話歷史優化查詢"""
        context = self.get_conversation_context(session_id)
        
        # 基礎查詢
        refined_query = original_query
        
        # 根據用戶偏好調整查詢
        preferences = context.get("user_preferences", {})
        
        if preferences.get("time_sensitive"):
            refined_query += " 時間彈性"
        if preferences.get("price_sensitive"):
            refined_query += " 經濟實惠"
        if preferences.get("difficulty_sensitive"):
            refined_query += " 適合程度"
        
        # 排除已被拒絕的課程類型
        rejected_courses = context.get("rejected_courses", [])
        if rejected_courses:
            refined_query += f" 但不要包含已拒絕的課程類型"
        
        return refined_query
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """獲取會話統計信息"""
        if session_id not in self.conversations:
            return {}
        
        conversation = self.conversations[session_id]
        return {
            "total_messages": len(conversation["messages"]),
            "feedback_count": len(conversation["feedback_history"]),
            "rejected_courses_count": len(conversation["rejected_courses"]),
            "preferences_count": len(conversation["user_preferences"]),
            "created_at": conversation["created_at"]
        }
    
    def load_conversations(self):
        """從文件加載對話歷史"""
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                self.conversations = json.load(f)
        except FileNotFoundError:
            self.conversations = {}
        except Exception as e:
            logger.error(f"載入對話歷史失敗: {e}")
            self.conversations = {}
    
    def save_conversations(self):
        """保存對話歷史到文件"""
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存對話歷史失敗: {e}")
    
    def clear_session(self, session_id: str):
        """清空指定會話"""
        if session_id in self.conversations:
            del self.conversations[session_id]
            self.save_conversations()
    
    def get_all_sessions(self) -> List[str]:
        """獲取所有會話ID"""
        return list(self.conversations.keys()) 