#!/usr/bin/env python3
"""
同時啟動API服務和Streamlit網頁服務的腳本
"""

import os
import sys
import time
import subprocess
import signal
import logging
from pathlib import Path
import threading
from typing import List, Optional

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServiceManager:
    """服務管理器"""
    
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.running = True
        
    def check_environment(self) -> bool:
        """檢查運行環境"""
        logger.info("正在檢查運行環境...")
        
        # 檢查必要檔案
        required_files = [
            "api_server.py",
            "streamlit_app.py",
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
        
        # 檢查依賴包
        required_packages = ["fastapi", "uvicorn", "streamlit", "openai", "chromadb"]
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
        
        logger.info("✅ 環境檢查通過")
        return True
    
    def start_api_service(self) -> Optional[subprocess.Popen]:
        """啟動API服務"""
        try:
            logger.info("正在啟動API服務...")
            
            # 使用uvicorn啟動FastAPI
            cmd = [
                sys.executable, "-m", "uvicorn",
                "api_server:app",
                "--host", "0.0.0.0",
                "--port", "8000",
                "--reload"
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.processes.append(process)
            logger.info("✅ API服務已啟動 (http://localhost:8000)")
            logger.info("📚 API文檔: http://localhost:8000/docs")
            
            return process
            
        except Exception as e:
            logger.error(f"啟動API服務失敗: {e}")
            return None
    
    def start_streamlit_service(self) -> Optional[subprocess.Popen]:
        """啟動Streamlit服務"""
        try:
            logger.info("正在啟動Streamlit網頁服務...")
            
            # 使用streamlit run啟動
            cmd = [
                sys.executable, "-m", "streamlit", "run",
                "streamlit_app.py",
                "--server.port", "8501",
                "--server.address", "0.0.0.0",
                "--server.headless", "true"
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.processes.append(process)
            logger.info("✅ Streamlit服務已啟動 (http://localhost:8501)")
            
            return process
            
        except Exception as e:
            logger.error(f"啟動Streamlit服務失敗: {e}")
            return None
    
    def monitor_process(self, process: subprocess.Popen, service_name: str):
        """監控進程輸出"""
        def read_output(pipe, prefix):
            try:
                for line in iter(pipe.readline, ''):
                    if line.strip() and self.running:
                        print(f"[{prefix}] {line.strip()}")
                    if not self.running:
                        break
            except:
                pass
        
        # 創建線程來讀取stdout和stderr
        if process.stdout:
            threading.Thread(
                target=read_output, 
                args=(process.stdout, f"{service_name}-OUT"),
                daemon=True
            ).start()
        
        if process.stderr:
            threading.Thread(
                target=read_output, 
                args=(process.stderr, f"{service_name}-ERR"),
                daemon=True
            ).start()
    
    def wait_for_services(self):
        """等待服務啟動"""
        logger.info("等待服務啟動中...")
        time.sleep(3)
        
        # 檢查API服務
        try:
            import requests
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ API服務健康檢查通過")
            else:
                logger.warning("⚠️  API服務可能還在初始化中")
        except Exception as e:
            logger.warning(f"⚠️  API服務檢查失敗: {e}")
        
        # 檢查Streamlit服務
        try:
            import requests
            response = requests.get("http://localhost:8501", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Streamlit服務檢查通過")
            else:
                logger.warning("⚠️  Streamlit服務可能還在初始化中")
        except Exception as e:
            logger.warning(f"⚠️  Streamlit服務檢查失敗: {e}")
    
    def setup_signal_handlers(self):
        """設定信號處理器"""
        def signal_handler(signum, frame):
            logger.info("收到停止信號，正在關閉所有服務...")
            self.stop_all_services()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def stop_all_services(self):
        """停止所有服務"""
        self.running = False
        
        for process in self.processes:
            try:
                logger.info(f"正在停止進程 {process.pid}...")
                process.terminate()
                
                # 等待進程結束
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"進程 {process.pid} 未能正常結束，強制終止...")
                    process.kill()
                    
            except Exception as e:
                logger.error(f"停止進程時發生錯誤: {e}")
        
        logger.info("所有服務已停止")
    
    def run(self):
        """運行所有服務"""
        try:
            # 環境檢查
            if not self.check_environment():
                sys.exit(1)
            
            # 設定信號處理器
            self.setup_signal_handlers()
            
            print("🚀 正在啟動所有服務...")
            print("="*70)
            
            # 啟動API服務
            api_process = self.start_api_service()
            if api_process:
                self.monitor_process(api_process, "API")
            
            # 等待一下再啟動Streamlit
            time.sleep(2)
            
            # 啟動Streamlit服務
            streamlit_process = self.start_streamlit_service()
            if streamlit_process:
                self.monitor_process(streamlit_process, "Streamlit")
            
            # 等待服務啟動
            self.wait_for_services()
            
            print("="*70)
            print("✅ 所有服務已啟動!")
            print("🌐 服務網址:")
            print("   • API服務:        http://localhost:8000")
            print("   • API文檔:        http://localhost:8000/docs")
            print("   • 網頁介面:       http://localhost:8501")
            print("   • 健康檢查:       http://localhost:8000/health")
            print("="*70)
            print("🛑 按 Ctrl+C 停止所有服務")
            print("="*70)
            
            # 保持運行
            while self.running:
                time.sleep(1)
                
                # 檢查進程是否還活著
                for process in self.processes[:]:  # 創建副本來避免修改問題
                    if process.poll() is not None:  # 進程已結束
                        logger.error(f"進程 {process.pid} 意外結束")
                        self.processes.remove(process)
                
                # 如果所有進程都結束了，退出
                if not self.processes:
                    logger.error("所有服務都已停止")
                    break
                    
        except KeyboardInterrupt:
            logger.info("收到中斷信號...")
        except Exception as e:
            logger.error(f"運行時發生錯誤: {e}")
        finally:
            self.stop_all_services()

def main():
    """主函數"""
    print("🤖 AI課程推薦系統 - 服務啟動器")
    print("同時啟動API服務 (FastAPI) 和網頁服務 (Streamlit)")
    print()
    
    # 檢查命令行參數
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h']:
            print("使用方法:")
            print("  python start_all_services.py        # 啟動所有服務")
            print("  python start_all_services.py -h     # 顯示幫助")
            print()
            print("服務端口:")
            print("  • API服務:     http://localhost:8000")
            print("  • 網頁服務:    http://localhost:8501")
            return
    
    manager = ServiceManager()
    manager.run()

if __name__ == "__main__":
    main() 