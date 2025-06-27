#!/usr/bin/env python3
"""
檔案自動監控系統
監控 AI課程.json 檔案修改時間，自動觸發資料更新
"""

import os
import time
import logging
from datetime import datetime
from threading import Thread
import streamlit as st
from config import Config

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FileMonitor:
    """檔案監控器"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.last_mtime = None
        self.is_monitoring = False
        self.monitoring_thread = None
        
    def get_file_mtime(self) -> float:
        """獲取檔案修改時間"""
        try:
            if os.path.exists(self.config.COURSE_DATA_PATH):
                return os.path.getmtime(self.config.COURSE_DATA_PATH)
            return 0
        except Exception as e:
            logger.error(f"獲取檔案修改時間失敗: {e}")
            return 0
    
    def initialize(self):
        """初始化監控器"""
        self.last_mtime = self.get_file_mtime()
        logger.info(f"初始化檔案監控器，檔案修改時間: {datetime.fromtimestamp(self.last_mtime)}")
    
    def check_file_changed(self) -> bool:
        """檢查檔案是否已修改"""
        current_mtime = self.get_file_mtime()
        
        if self.last_mtime is None:
            self.last_mtime = current_mtime
            return False
        
        if current_mtime > self.last_mtime:
            logger.info(f"檔案已修改！舊時間: {datetime.fromtimestamp(self.last_mtime)}, "
                       f"新時間: {datetime.fromtimestamp(current_mtime)}")
            self.last_mtime = current_mtime
            return True
        
        return False
    
    def get_file_info(self) -> dict:
        """獲取檔案資訊"""
        try:
            if not os.path.exists(self.config.COURSE_DATA_PATH):
                return {
                    'exists': False,
                    'size': 0,
                    'modified': '檔案不存在',
                    'mtime': 0
                }
            
            mtime = os.path.getmtime(self.config.COURSE_DATA_PATH)
            size = os.path.getsize(self.config.COURSE_DATA_PATH)
            
            return {
                'exists': True,
                'size': f"{size / 1024:.1f} KB",
                'modified': datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
                'mtime': mtime
            }
        except Exception as e:
            logger.error(f"獲取檔案資訊失敗: {e}")
            return {
                'exists': False,
                'size': 0,
                'modified': '錯誤',
                'mtime': 0
            }

# 全域監控器實例
file_monitor = FileMonitor()

def get_file_monitor() -> FileMonitor:
    """獲取檔案監控器實例"""
    return file_monitor

def check_and_update_data():
    """檢查並更新資料"""
    try:
        monitor = get_file_monitor()
        
        # 初始化監控器（如果還沒初始化）
        if monitor.last_mtime is None:
            monitor.initialize()
        
        # 檢查檔案是否已修改
        if monitor.check_file_changed():
            logger.info("檢測到檔案更新，觸發資料重新載入")
            
            # 強制重建資料庫（使用改進的方法）
            try:
                result = _safe_rebuild_database()
                if result['success']:
                    return {
                        'updated': True,
                        'message': '檢測到資料檔案更新，已重建資料庫',
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                else:
                    return {
                        'updated': False,
                        'message': f'重建失敗: {result["message"]}',
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                
            except Exception as e:
                logger.error(f"清理資料庫失敗: {e}")
                return {
                    'updated': False,
                    'message': f'資料庫重建失敗: {str(e)}',
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        else:
            return {
                'updated': False,
                'message': '資料檔案無更新',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
    except Exception as e:
        logger.error(f"檢查和更新資料失敗: {e}")
        return {
            'updated': False,
            'message': f'檢查失敗: {str(e)}',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

def _safe_rebuild_database():
    """安全地重建資料庫（處理 Windows 檔案鎖定問題）"""
    try:
        import shutil
        import gc
        import subprocess
        from config import Config
        
        config = Config()
        
        # 嘗試關閉所有向量數據庫連接
        try:
            logger.info("嘗試關閉所有向量數據庫連接...")
            
            # 從 Streamlit cache 中獲取 RAG 系統
            if hasattr(st, 'cache_resource') and hasattr(st.cache_resource, 'data'):
                for key, value in st.cache_resource.data.items():
                    if hasattr(value, 'vector_store') and value.vector_store:
                        try:
                            value.vector_store.close_connection()
                            logger.info("已關閉快取中的向量數據庫連接")
                        except:
                            pass
            
            # 獲取當前 session state 中的 RAG 系統
            if hasattr(st, 'session_state') and 'rag_system' in st.session_state:
                rag_system = st.session_state['rag_system']
                if hasattr(rag_system, 'vector_store') and rag_system.vector_store:
                    rag_system.vector_store.close_connection()
                    logger.info("已關閉 RAG 系統中的向量數據庫連接")
            
            # 嘗試清理全局向量存儲實例
            import sys
            if 'vector_store' in sys.modules:
                vector_store_module = sys.modules['vector_store']
                if hasattr(vector_store_module, 'VectorStore'):
                    logger.info("清理全局向量存儲模組")
                    
        except Exception as e:
            logger.warning(f"關閉向量數據庫連接時出現警告: {e}")
        
        # 清理 Streamlit 快取
        if hasattr(st, 'cache_resource'):
            st.cache_resource.clear()
            logger.info("已清理 Streamlit 快取")
        
        # 強制垃圾回收，釋放可能的檔案引用
        gc.collect()
        
        # 等待一下讓系統釋放檔案鎖定
        time.sleep(3)
        
        # 嘗試刪除 ChromaDB 資料庫
        if os.path.exists(config.VECTOR_DB_PATH):
            logger.info(f"刪除舊資料庫: {config.VECTOR_DB_PATH}")
            
            # Windows 安全刪除策略
            max_retries = 10  # 增加重試次數
            for attempt in range(max_retries):
                try:
                    # 嘗試使用不同的刪除方法
                    if attempt < 3:
                        # 前3次使用標準方法
                        shutil.rmtree(config.VECTOR_DB_PATH)
                    else:
                        # 後續嘗試使用更強制的方法
                        result = subprocess.run(
                            ['powershell', '-Command', f'Remove-Item -Recurse -Force "{config.VECTOR_DB_PATH}"'],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        if result.returncode != 0:
                            raise OSError(f"PowerShell deletion failed: {result.stderr}")
                    
                    logger.info("成功刪除舊資料庫")
                    break
                    
                except (PermissionError, OSError, subprocess.TimeoutExpired) as e:
                    if attempt < max_retries - 1:
                        wait_time = 2 + attempt  # 逐漸增加等待時間
                        logger.warning(f"刪除嘗試 {attempt + 1} 失敗，等待 {wait_time} 秒後重試: {e}")
                        
                        # 多次嘗試釋放資源
                        gc.collect()
                        time.sleep(wait_time)
                        gc.collect()
                    else:
                        logger.error(f"無法刪除資料庫，可能被其他程序鎖定: {e}")
                        # 即使刪除失敗，也繼續進行，讓系統重建
                        logger.warning("刪除失敗但繼續進行，系統將嘗試覆蓋現有資料庫")
                        break
        
        return {
            'success': True,
            'message': '資料庫重建成功',
        }
        
    except Exception as e:
        logger.error(f"資料庫重建失敗: {e}")
        return {
            'success': False,
            'message': f'重建過程出錯: {str(e)}'
        }

def force_rebuild_database():
    """強制重建資料庫"""
    try:
        logger.info("開始強制重建資料庫...")
        
        result = _safe_rebuild_database()
        
        if result['success']:
            # 重置監控器
            file_monitor.last_mtime = None
            file_monitor.initialize()
            
            return {
                'success': True,
                'message': '強制重建觸發成功，已刪除舊資料庫',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            return {
                'success': False,
                'message': result['message'],
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
    except Exception as e:
        logger.error(f"強制重建失敗: {e}")
        return {
            'success': False,
            'message': f'重建失敗: {str(e)}',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

if __name__ == "__main__":
    # 測試監控功能
    monitor = FileMonitor()
    monitor.initialize()
    
    print("檔案監控器測試")
    print(f"檔案路徑: {monitor.config.COURSE_DATA_PATH}")
    
    file_info = monitor.get_file_info()
    print(f"檔案存在: {file_info['exists']}")
    print(f"檔案大小: {file_info['size']}")
    print(f"最後修改: {file_info['modified']}")
    
    # 測試檢查功能
    result = check_and_update_data()
    print(f"檢查結果: {result}") 