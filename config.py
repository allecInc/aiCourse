import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

class Config:
    """配置類別管理應用程式設定"""
    
    # OpenAI 設定
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'your_openai_api_key_here')
    MODEL_NAME = "gpt-4.1-mini"  # GPT-4.1 mini
    
    # 向量數據庫設定
    VECTOR_DB_PATH = "./chroma_db"
    COLLECTION_NAME = "ai_courses"
    
    # 嵌入模型設定
    # 改為多語模型以提升中文檢索品質
    EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    # 檢索設定
    RETRIEVAL_K = 5  # 檢索相似課程數量
    # 提升閾值降低噪音（建議 0.6~0.8）
    SIMILARITY_THRESHOLD = 0.7

    # 觸發檢索的關鍵詞（可透過 .env 覆寫，逗號分隔）
    COURSE_TRIGGER_VERBS = os.getenv(
        'COURSE_TRIGGER_VERBS',
        '學,學習,想學,想上,想報名,想參加'
    )
    COURSE_TRIGGER_KEYWORDS = os.getenv(
        'COURSE_TRIGGER_KEYWORDS',
        '課程,課,推薦,上課,報名,訓練,瑜珈,瑜伽,有氧,游泳,健身,運動,舞蹈,拳擊,飛輪,皮拉提斯,球類,拉丁,爵士,街舞,芭蕾,伸展,核心,TRX,壺鈴,太極,氣功,設計'
    )
    COURSE_TRIGGER_TIME_SIGNALS = os.getenv(
        'COURSE_TRIGGER_TIME_SIGNALS',
        '早上,上午,中午,下午,晚上,夜間'
    )
    COURSE_TRIGGER_WEEK_SIGNALS = os.getenv(
        'COURSE_TRIGGER_WEEK_SIGNALS',
        '週,周,星期,禮拜'
    )
    
    # 課程文件路徑 (已由資料庫取代)
    COURSE_DATA_PATH = "AI課程.json"

    # SQL Server 資料庫設定 (請填入您的實際資訊)
    DB_DRIVER = os.getenv('DB_DRIVER', '{ODBC Driver 17 for SQL Server}')
    DB_SERVER = os.getenv('DB_SERVER', 'your_server.database.windows.net')
    DB_DATABASE = os.getenv('DB_DATABASE', 'your_database_name')
    DB_USER = os.getenv('DB_USER', 'your_username')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'your_password')
    DB_TABLE = os.getenv('DB_TABLE', 'courses') 
