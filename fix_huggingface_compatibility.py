#!/usr/bin/env python3
"""
修復 huggingface_hub 版本相容性問題
解決 ImportError: cannot import name 'cached_download' 錯誤
"""

import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_and_fix_huggingface_compatibility():
    """檢查並修復 huggingface_hub 相容性問題"""
    try:
        # 首先嘗試匯入 huggingface_hub
        logger.info("檢查 huggingface_hub 版本...")
        
        try:
            import huggingface_hub
            logger.info(f"當前 huggingface_hub 版本: {huggingface_hub.__version__}")
            
            # 檢查是否有 cached_download
            if hasattr(huggingface_hub, 'cached_download'):
                logger.info("cached_download 函數存在")
            else:
                logger.warning("cached_download 函數不存在，可能需要更新版本")
                
        except ImportError as e:
            logger.error(f"無法匯入 huggingface_hub: {e}")
            return False
        
        # 檢查 sentence-transformers
        logger.info("檢查 sentence-transformers...")
        try:
            import sentence_transformers
            logger.info(f"當前 sentence-transformers 版本: {sentence_transformers.__version__}")
        except ImportError as e:
            logger.error(f"無法匯入 sentence-transformers: {e}")
            return False
        
        # 嘗試載入模型來測試相容性
        logger.info("測試模型載入...")
        try:
            from sentence_transformers import SentenceTransformer
            # 使用較小的模型進行測試
            model = SentenceTransformer('all-MiniLM-L6-v2')
            test_text = "這是一個測試文本"
            embedding = model.encode([test_text])
            logger.info(f"模型載入成功，生成向量維度: {len(embedding[0])}")
            return True
            
        except Exception as e:
            logger.error(f"模型載入失敗: {e}")
            return False
            
    except Exception as e:
        logger.error(f"檢查過程發生錯誤: {e}")
        return False

def install_compatible_versions():
    """安裝相容的版本"""
    try:
        logger.info("安裝相容的版本...")
        
        # 卸載可能衝突的包
        packages_to_uninstall = ['huggingface_hub', 'sentence-transformers', 'transformers']
        for package in packages_to_uninstall:
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', package], 
                             check=False, capture_output=True)
                logger.info(f"已卸載 {package}")
            except Exception:
                pass
        
        # 安裝指定版本
        compatible_versions = [
            'huggingface_hub>=0.23.0,<1.0.0',
            'transformers>=4.36.0',
            'sentence-transformers==2.7.0'
        ]
        
        for package in compatible_versions:
            logger.info(f"安裝 {package}...")
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', package], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"安裝 {package} 失敗: {result.stderr}")
                return False
            else:
                logger.info(f"成功安裝 {package}")
        
        return True
        
    except Exception as e:
        logger.error(f"安裝過程發生錯誤: {e}")
        return False

def main():
    """主函數"""
    logger.info("開始修復 huggingface_hub 相容性問題...")
    
    # 首先檢查當前狀態
    if check_and_fix_huggingface_compatibility():
        logger.info("✅ 當前版本相容，無需修復")
        return True
    
    # 如果檢查失敗，嘗試安裝相容版本
    logger.info("❌ 發現相容性問題，開始修復...")
    if install_compatible_versions():
        logger.info("✅ 修復完成，重新檢查...")
        if check_and_fix_huggingface_compatibility():
            logger.info("✅ 修復成功！")
            return True
        else:
            logger.error("❌ 修復後仍有問題")
            return False
    else:
        logger.error("❌ 修復失敗")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 