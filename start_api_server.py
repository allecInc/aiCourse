#!/usr/bin/env python3
"""
AI課程推薦API服務啟動腳本
"""

import os
import sys
import logging
import uvicorn
from pathlib import Path

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_environment():
    """檢查運行環境"""
    logger.info("正在檢查運行環境...")
    
    # 檢查Python版本
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        logger.error("需要Python 3.8或更高版本")
        return False
    
    logger.info(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 檢查必要檔案
    required_files = [
        "api_server.py",
        "config.py", 
        "rag_system.py",
        "vector_store.py",
        "course_processor.py",
        "AI課程.json"
    ]
    
    missing_files = []
    for file_name in required_files:
        if not Path(file_name).exists():
            missing_files.append(file_name)
    
    if missing_files:
        logger.error(f"缺少必要檔案: {missing_files}")
        return False
    
    logger.info("✅ 環境檢查通過")
    return True

def check_dependencies():
    """檢查依賴包"""
    logger.info("正在檢查依賴包...")
    
    required_packages = [
        "fastapi",
        "uvicorn", 
        "pydantic",
        "openai",
        "chromadb",
        "sentence_transformers",
        "pandas",
        "numpy"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"缺少依賴包: {missing_packages}")
        logger.info("請運行: pip install -r requirements.txt")
        return False
    
    logger.info("✅ 依賴包檢查通過")
    return True

def setup_environment():
    """設定環境變數"""
    logger.info("正在設定環境...")
    
    # 檢查.env檔案
    env_file = Path(".env")
    if env_file.exists():
        logger.info("發現.env檔案，載入環境變數")
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            logger.warning("python-dotenv未安裝，無法載入.env檔案")
    
    # 檢查OpenAI API密鑰
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("⚠️  未設定OPENAI_API_KEY環境變數")
        logger.info("您可以:")
        logger.info("1. 在.env檔案中設定: OPENAI_API_KEY=your-key-here")
        logger.info("2. 或在API請求中直接提供api_key參數")
    else:
        logger.info("✅ 發現OpenAI API密鑰")
    
    return True

def main():
    """主函數"""
    print("🚀 正在啟動AI課程推薦API服務...")
    print("="*60)
    
    # 環境檢查
    if not check_environment():
        sys.exit(1)
    
    if not check_dependencies():
        sys.exit(1)
        
    if not setup_environment():
        sys.exit(1)
    
    print("="*60)
    print("✅ 所有檢查通過，正在啟動API服務...")
    print("📚 API文檔: http://localhost:8000/docs")
    print("🔍 健康檢查: http://localhost:8000/health") 
    print("🛑 按Ctrl+C停止服務")
    print("="*60)
    
    try:
        # 啟動API服務
        uvicorn.run(
            "api_server:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("收到停止信號，正在關閉服務...")
    except Exception as e:
        logger.error(f"啟動API服務失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 