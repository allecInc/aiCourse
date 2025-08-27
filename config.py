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
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    
    # 檢索設定
    RETRIEVAL_K = 5  # 檢索相似課程數量
    SIMILARITY_THRESHOLD = 0.1  # 相似度閾值 (設定很低以確保找到所有相關課程)
    
    # 課程文件路徑 (已由資料庫取代)
    COURSE_DATA_PATH = "AI課程.json"

    # SQL Server 資料庫設定 (請填入您的實際資訊)
    DB_DRIVER = os.getenv('DB_DRIVER', '{ODBC Driver 17 for SQL Server}')
    DB_SERVER = os.getenv('DB_SERVER', 'your_server.database.windows.net')
    DB_DATABASE = os.getenv('DB_DATABASE', 'your_database_name')
    DB_USER = os.getenv('DB_USER', 'your_username')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'your_password')
    DB_TABLE = os.getenv('DB_TABLE', 'courses') 