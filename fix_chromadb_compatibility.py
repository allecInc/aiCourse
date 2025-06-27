#!/usr/bin/env python3
"""
修復 ChromaDB 相容性問題
解決 Client.init() got an unexpected keyword argument 'proxies' 錯誤
"""

import subprocess
import sys
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_chromadb_compatibility():
    """修復 ChromaDB 相容性問題"""
    try:
        logger.info("🔧 開始修復 ChromaDB 相容性問題...")
        
        # 1. 卸載現有的 ChromaDB
        logger.info("卸載現有的 ChromaDB...")
        subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'chromadb'], 
                      check=False, capture_output=True)
        
        # 2. 安裝相容版本
        logger.info("安裝相容版本的 ChromaDB...")
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', 
            'chromadb>=0.4.15,<0.5.0', 
            '--no-cache-dir'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"安裝 ChromaDB 失敗: {result.stderr}")
            return False
        
        logger.info("✅ ChromaDB 安裝成功")
        
        # 3. 測試 ChromaDB 初始化
        logger.info("測試 ChromaDB 初始化...")
        try:
            import chromadb
            from chromadb.config import Settings
            
            # 測試客戶端初始化
            settings = Settings(
                anonymized_telemetry=False,
                allow_reset=True,
                persist_directory="./test_chroma"
            )
            
            client = chromadb.PersistentClient(
                path="./test_chroma",
                settings=settings
            )
            
            # 測試集合創建
            collection = client.get_or_create_collection(
                name="test_collection",
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info("✅ ChromaDB 初始化測試成功")
            
            # 清理測試文件
            client.delete_collection("test_collection")
            
            return True
            
        except Exception as e:
            logger.error(f"ChromaDB 初始化測試失敗: {e}")
            return False
        
    except Exception as e:
        logger.error(f"修復過程發生錯誤: {e}")
        return False

def test_complete_system():
    """測試完整系統功能"""
    try:
        logger.info("🧪 測試完整系統功能...")
        
        # 測試向量存儲
        from vector_store import VectorStore
        from config import Config
        
        config = Config()
        vector_store = VectorStore(config)
        
        logger.info("✅ 向量存儲初始化成功")
        
        # 測試嵌入功能
        test_text = "測試文本"
        embedding = vector_store.embed_text(test_text)
        
        if embedding:
            logger.info(f"✅ 文本嵌入成功，向量維度: {len(embedding)}")
        else:
            logger.error("❌ 文本嵌入失敗")
            return False
        
        # 測試 RAG 系統
        from rag_system import RAGSystem
        rag_system = RAGSystem(config)
        
        logger.info("✅ RAG 系統初始化成功")
        
        return True
        
    except Exception as e:
        logger.error(f"系統測試失敗: {e}")
        return False

def main():
    """主函數"""
    logger.info("🚀 開始修復 ChromaDB 相容性問題...")
    
    # 修復 ChromaDB
    if not fix_chromadb_compatibility():
        logger.error("❌ ChromaDB 修復失敗")
        return False
    
    # 測試完整系統
    if not test_complete_system():
        logger.error("❌ 系統測試失敗")
        return False
    
    logger.info("🎉 ChromaDB 相容性問題修復完成！")
    logger.info("📌 現在可以正常啟動應用程式了")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 