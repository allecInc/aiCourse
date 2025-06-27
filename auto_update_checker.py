#!/usr/bin/env python3
"""
自動資料更新檢查器
用於定時檢查AI課程資料是否有更新，並自動重新載入
"""

import time
import schedule
import logging
from datetime import datetime
from config import Config
from rag_system import RAGSystem

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_update.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutoUpdateChecker:
    """自動更新檢查器"""
    
    def __init__(self):
        self.config = Config()
        self.rag_system = None
        self.last_check = None
        self.setup_system()
    
    def setup_system(self):
        """初始化系統"""
        try:
            logger.info("初始化自動更新檢查器...")
            self.rag_system = RAGSystem(self.config)
            self.rag_system.initialize_knowledge_base()
            logger.info("自動更新檢查器初始化完成")
        except Exception as e:
            logger.error(f"初始化失敗: {e}")
            raise
    
    def check_and_update(self):
        """檢查並更新資料"""
        try:
            self.last_check = datetime.now()
            logger.info(f"開始檢查資料更新 - {self.last_check.strftime('%Y-%m-%d %H:%M:%S')}")
            
            result = self.rag_system.check_and_reload_if_updated()
            
            if result['updated']:
                logger.info(f"✅ 資料已更新: {result['message']}")
                # 可以在這裡添加通知邏輯，例如發送郵件或Slack訊息
                self.send_notification(f"AI課程資料已更新 - {result['message']}")
            else:
                logger.info(f"ℹ️ 無更新: {result['message']}")
            
            return result
            
        except Exception as e:
            logger.error(f"檢查更新失敗: {e}")
            return {
                'updated': False,
                'message': f'錯誤: {str(e)}',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def send_notification(self, message: str):
        """發送通知（可擴展）"""
        logger.info(f"🔔 通知: {message}")
        # 在這裡可以添加各種通知方式：
        # - 郵件通知
        # - Slack/Discord 通知
        # - 系統通知
        # - 寫入特殊日誌檔案等
    
    def get_status(self):
        """獲取檢查器狀態"""
        return {
            'last_check': self.last_check.strftime('%Y-%m-%d %H:%M:%S') if self.last_check else '從未檢查',
            'system_ready': self.rag_system is not None,
            'data_file': self.config.COURSE_DATA_PATH
        }

def main():
    """主程式"""
    logger.info("啟動自動更新檢查器")
    
    try:
        # 創建檢查器
        checker = AutoUpdateChecker()
        
        # 立即執行一次檢查
        logger.info("執行初始檢查...")
        checker.check_and_update()
        
        # 設定定時檢查排程
        # 每小時檢查一次
        schedule.every().hour.do(checker.check_and_update)
        
        # 每天早上9點檢查
        schedule.every().day.at("09:00").do(checker.check_and_update)
        
        # 每天下午2點檢查
        schedule.every().day.at("14:00").do(checker.check_and_update)
        
        # 每天晚上8點檢查
        schedule.every().day.at("20:00").do(checker.check_and_update)
        
        logger.info("排程設定完成，開始監控...")
        logger.info("檢查頻率: 每小時一次，以及每天9:00、14:00、20:00")
        
        # 運行排程器
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分鐘檢查一次排程
            
    except KeyboardInterrupt:
        logger.info("收到中斷信號，停止檢查器")
    except Exception as e:
        logger.error(f"檢查器運行錯誤: {e}")
    finally:
        logger.info("自動更新檢查器已停止")

if __name__ == "__main__":
    main() 