from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
import os
from datetime import datetime
import uvicorn
from contextlib import asynccontextmanager

from config import Config
from rag_system import RAGSystem

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局變量
rag_system: Optional[RAGSystem] = None

# 初始化系統
@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    global rag_system
    # 啟動時初始化
    try:
        logger.info("正在初始化RAG系統...")
        config = Config()
        rag_system = RAGSystem(config)
        
        # 初始化知識庫
        rag_system.initialize_knowledge_base()
        
        logger.info("RAG系統初始化完成")
    except Exception as e:
        logger.error(f"RAG系統初始化失敗: {e}")
        raise
    
    yield
    
    # 關閉時清理
    logger.info("API服務正在關閉...")

# 創建FastAPI應用
app = FastAPI(
    title="AI課程推薦API",
    description="基於RAG技術的智能課程推薦系統API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 添加CORS中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生產環境中應該限制具體域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic 模型定義
class CourseRecommendationRequest(BaseModel):
    query: str = Field(..., description="用戶查詢需求", min_length=1, max_length=500)
    k: Optional[int] = Field(5, description="返回課程數量", ge=1, le=20)
    api_key: Optional[str] = Field(None, description="OpenAI API密鑰")

class CourseRecommendationResponse(BaseModel):
    query: str
    success: bool
    recommendation: str
    retrieved_courses: List[Dict[str, Any]]
    total_found: int
    response_time: float

class CourseSearchRequest(BaseModel):
    query: str = Field(..., description="搜索關鍵詞", min_length=1, max_length=200)
    k: Optional[int] = Field(10, description="返回課程數量", ge=1, le=50)

class CourseSearchResponse(BaseModel):
    query: str
    courses: List[Dict[str, Any]]
    total_found: int
    response_time: float

class SystemStatsResponse(BaseModel):
    total_courses: int
    total_categories: int
    categories: List[str]
    model_name: str
    embedding_model: str
    system_status: str
    last_updated: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    system_ready: bool
    services: Dict[str, str]

# API端點定義

@app.get("/", response_class=JSONResponse)
async def root():
    """根端點 - API信息"""
    return {
        "message": "歡迎使用AI課程推薦API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康檢查端點"""
    services = {
        "rag_system": "ready" if rag_system else "not_ready",
        "vector_store": "ready" if rag_system and rag_system.vector_store else "not_ready",
        "openai_client": "ready" if rag_system and rag_system.openai_client else "not_ready"
    }
    
    system_ready = all(status == "ready" for status in services.values())
    
    return HealthResponse(
        status="healthy" if system_ready else "degraded",
        timestamp=datetime.now().isoformat(),
        system_ready=system_ready,
        services=services
    )

@app.post("/recommend", response_model=CourseRecommendationResponse)
async def recommend_courses(request: CourseRecommendationRequest):
    """課程推薦端點"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG系統未就緒")
    
    start_time = datetime.now()
    
    try:
        # 如果提供了API密鑰，則更新配置
        if request.api_key:
            rag_system.config.OPENAI_API_KEY = request.api_key
            rag_system.openai_client.api_key = request.api_key
        
        # 檢查API密鑰
        if not rag_system.config.OPENAI_API_KEY:
            raise HTTPException(status_code=400, detail="請提供OpenAI API密鑰")
        
        # 獲取課程推薦
        result = rag_system.get_course_recommendation(request.query, request.k)
        
        response_time = (datetime.now() - start_time).total_seconds()
        
        return CourseRecommendationResponse(
            query=result['query'],
            success=result['success'],
            recommendation=result['recommendation'],
            retrieved_courses=result['retrieved_courses'],
            total_found=len(result['retrieved_courses']),
            response_time=response_time
        )
        
    except Exception as e:
        logger.error(f"課程推薦失敗: {e}")
        raise HTTPException(status_code=500, detail=f"推薦過程中發生錯誤: {str(e)}")

@app.post("/search", response_model=CourseSearchResponse)
async def search_courses(request: CourseSearchRequest):
    """課程搜索端點（僅向量檢索，不使用GPT）"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG系統未就緒")
    
    start_time = datetime.now()
    
    try:
        # 檢索相關課程
        courses = rag_system.retrieve_relevant_courses(request.query, request.k)
        
        response_time = (datetime.now() - start_time).total_seconds()
        
        return CourseSearchResponse(
            query=request.query,
            courses=courses,
            total_found=len(courses),
            response_time=response_time
        )
        
    except Exception as e:
        logger.error(f"課程搜索失敗: {e}")
        raise HTTPException(status_code=500, detail=f"搜索過程中發生錯誤: {str(e)}")

@app.get("/categories", response_class=JSONResponse)
async def get_categories():
    """獲取所有課程類別"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG系統未就緒")
    
    try:
        categories = rag_system.get_all_categories()
        return {
            "categories": categories,
            "total": len(categories)
        }
    except Exception as e:
        logger.error(f"獲取類別失敗: {e}")
        raise HTTPException(status_code=500, detail=f"獲取類別時發生錯誤: {str(e)}")

@app.get("/categories/{category}/courses", response_class=JSONResponse)
async def get_courses_by_category(
    category: str,
    limit: int = Query(10, description="返回課程數量", ge=1, le=100)
):
    """根據類別獲取課程"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG系統未就緒")
    
    try:
        courses = rag_system.get_courses_by_category(category)
        
        # 限制返回數量
        limited_courses = courses[:limit]
        
        return {
            "category": category,
            "courses": limited_courses,
            "total_found": len(courses),
            "returned": len(limited_courses)
        }
    except Exception as e:
        logger.error(f"根據類別獲取課程失敗: {e}")
        raise HTTPException(status_code=500, detail=f"獲取課程時發生錯誤: {str(e)}")

@app.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats():
    """獲取系統統計信息"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG系統未就緒")
    
    try:
        stats = rag_system.get_system_stats()
        
        return SystemStatsResponse(
            total_courses=stats.get('total_courses', 0),
            total_categories=stats.get('total_categories', 0),
            categories=stats.get('categories', []),
            model_name=stats.get('model_name', 'GPT-4o-mini'),
            embedding_model=stats.get('embedding_model', 'sentence-transformers'),
            system_status="ready",
            last_updated=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"獲取系統統計失敗: {e}")
        raise HTTPException(status_code=500, detail=f"獲取統計信息時發生錯誤: {str(e)}")

@app.post("/check-updates")
async def check_data_updates():
    """檢查資料更新"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG系統未就緒")
    
    try:
        result = rag_system.check_and_reload_if_updated()
        return {
            "updated": result['updated'],
            "message": result['message'],
            "timestamp": result['timestamp'],
            "status": "success"
        }
    except Exception as e:
        logger.error(f"檢查資料更新失敗: {e}")
        raise HTTPException(status_code=500, detail=f"檢查更新時發生錯誤: {str(e)}")

@app.post("/rebuild-knowledge-base")
async def rebuild_knowledge_base(background_tasks: BackgroundTasks):
    """重建知識庫（後台任務）"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG系統未就緒")
    
    def rebuild_task():
        try:
            logger.info("開始重建知識庫...")
            rag_system.initialize_knowledge_base(force_rebuild=True)
            logger.info("知識庫重建完成")
        except Exception as e:
            logger.error(f"重建知識庫失敗: {e}")
    
    background_tasks.add_task(rebuild_task)
    
    return {
        "message": "知識庫重建任務已啟動",
        "status": "processing"
    }

# 錯誤處理器
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"未處理的異常: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "內部服務器錯誤",
            "status_code": 500,
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    # 開發環境運行
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 