import json
import pandas as pd
from typing import List, Dict, Any
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CourseProcessor:
    """課程數據處理器 - 處理和準備課程數據用於RAG系統"""
    
    def __init__(self, course_file_path: str):
        self.course_file_path = course_file_path
        self.courses_data = []
        
    def load_courses(self) -> List[Dict[str, Any]]:
        """載入課程數據"""
        try:
            with open(self.course_file_path, 'r', encoding='utf-8') as file:
                self.courses_data = json.load(file)
            logger.info(f"成功載入 {len(self.courses_data)} 筆課程數據")
            return self.courses_data
        except Exception as e:
            logger.error(f"載入課程數據失敗: {e}")
            return []
    
    def clean_and_process_courses(self) -> List[Dict[str, Any]]:
        """清理和處理課程數據"""
        if not self.courses_data:
            self.load_courses()
        
        processed_courses = []
        
        for course in self.courses_data:
            # 只保留有意義的非空值
            processed_course = {}
            
            # 基本資訊
            processed_course['項次'] = course.get('項次', '')
            processed_course['大類'] = course.get('大類', '').strip()
            processed_course['課程名稱'] = course.get('課程名稱', '').strip()
            processed_course['課程介紹'] = course.get('課程介紹', '').strip()
            
            # 其他資訊（如果存在且非空）
            for key in ['授課教室', '課程代碼', '授課教師', '年齡限制', 
                       '上課週次', '上課時間', '課程費用', '體驗費用', 
                       '開班人數', '滿班人數']:
                value = course.get(key)
                if value is not None and str(value).strip():
                    processed_course[key] = str(value).strip()
            
            # 確保必要欄位不為空
            if processed_course['課程名稱'] and processed_course['課程介紹']:
                processed_courses.append(processed_course)
        
        logger.info(f"處理完成，有效課程數量: {len(processed_courses)}")
        return processed_courses
    
    def create_searchable_text(self, course: Dict[str, Any]) -> str:
        """為每個課程創建可搜尋的文本內容"""
        searchable_parts = []
        
        # 課程名稱
        if course.get('課程名稱'):
            searchable_parts.append(f"課程名稱: {course['課程名稱']}")
        
        # 課程類別
        if course.get('大類'):
            searchable_parts.append(f"類別: {course['大類']}")
            
            # 添加類別相關關鍵詞以提高語義匹配
            category_keywords = self._get_category_keywords(course['大類'])
            if category_keywords:
                searchable_parts.append(f"相關關鍵詞: {category_keywords}")
        
        # 課程介紹
        if course.get('課程介紹'):
            searchable_parts.append(f"介紹: {course['課程介紹']}")
        
        # 其他詳細資訊
        additional_info = []
        for key in ['授課教師', '年齡限制', '上課時間', '課程費用', '體驗費用']:
            if course.get(key):
                additional_info.append(f"{key}: {course[key]}")
        
        if additional_info:
            searchable_parts.append("詳細資訊: " + ", ".join(additional_info))
        
        return "\n".join(searchable_parts)
    
    def _get_category_keywords(self, category: str) -> str:
        """根據課程類別添加相關關鍵詞，提高語義匹配率"""
        keyword_mapping = {
            'SG　泳訓團體': '游泳 泳訓 游泳課程 泳池 水中運動 游泳教學 泳技 水性 戲水',
            'A　有氧系列': '有氧運動 燃脂 減肥 心肺 塑身 雕塑 體適能',
            'B　舞蹈系列': '舞蹈 跳舞 律動 舞步 音樂 節奏',
            'C　瑜珈系列': '瑜珈 瑜伽 伸展 放鬆 冥想 體位法 柔軟度',
            'D　飛輪系列': '飛輪 單車 腳踏車 心肺訓練 燃脂',
            'E　武術系列': '武術 太極 氣功 功夫 武功 防身術',
            'F　專業運動': '專業運動 體適能 肌力 訓練 健身',
            'G　幼兒/兒童系列': '幼兒 兒童 小孩 孩子 親子 兒童課程 幼兒課程',
            'H　空中瑜珈': '空中瑜珈 空中 懸吊 反重力',
            'J　肌力系列': '肌力 重訓 肌肉 力量 訓練',
            'K　水中運動': '水中運動 水中 水療 水中健身',
            'O　球類團體': '球類 團體運動 球類運動 羽球 桌球 網球',
            'DV　潛水系列': '潛水 深潛 水肺潛水 自由潛水'
        }
        
        return keyword_mapping.get(category, '')
    
    def get_course_categories(self) -> List[str]:
        """獲取所有課程類別"""
        if not self.courses_data:
            self.load_courses()
        
        categories = set()
        for course in self.courses_data:
            if course.get('大類'):
                categories.add(course['大類'].strip())
        
        return sorted(list(categories))
    
    def get_courses_by_category(self, category: str) -> List[Dict[str, Any]]:
        """根據類別獲取課程"""
        processed_courses = self.clean_and_process_courses()
        return [course for course in processed_courses 
                if course.get('大類', '').strip() == category.strip()]
    
    def prepare_for_vectorization(self) -> List[Dict[str, Any]]:
        """準備課程數據用於向量化"""
        processed_courses = self.clean_and_process_courses()
        
        vectorization_data = []
        for i, course in enumerate(processed_courses):
            vector_item = {
                'id': str(i),
                'course_id': course.get('項次', i),
                'title': course.get('課程名稱', ''),
                'category': course.get('大類', ''),
                'description': course.get('課程介紹', ''),
                'searchable_text': self.create_searchable_text(course),
                'metadata': course  # 保留完整的課程資訊
            }
            vectorization_data.append(vector_item)
        
        return vectorization_data 