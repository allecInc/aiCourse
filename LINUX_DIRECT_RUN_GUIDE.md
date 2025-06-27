# 🐧 Linux 系統直接運行指南

是的！Linux 系統完全可以直接使用 `streamlit run streamlit_app.py` 來運行應用程式。以下是詳細的設定和運行指南。

## 🤔 Docker vs 直接運行

### Docker 的優勢：
- ✅ 環境隔離，避免版本衝突
- ✅ 包含所有依賴，一鍵部署
- ✅ 易於橫向擴展和管理
- ✅ 跨平台一致性

### 直接運行的優勢：
- ✅ 更快的啟動速度
- ✅ 直接存取系統資源
- ✅ 更容易除錯和開發
- ✅ 不需要 Docker 環境

## 🚀 Linux 直接運行步驟

### 1. 系統準備

```bash
# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝 Python 3.11+ 和相關工具
sudo apt install python3 python3-pip python3-venv git curl -y

# 檢查 Python 版本
python3 --version
```

### 2. 建立虛擬環境（推薦）

```bash
# 進入專案目錄
cd /path/to/aiSuggestCourse

# 建立虛擬環境
python3 -m venv venv

# 啟動虛擬環境
source venv/bin/activate

# 升級 pip
pip install --upgrade pip setuptools wheel
```

### 3. 安裝相依套件

```bash
# 使用修復版本的需求檔案
pip install -r requirements_fixed.txt

# 或者手動安裝關鍵套件
pip install streamlit==1.32.0
pip install openai==1.12.0
pip install chromadb==0.4.22
pip install sentence-transformers==2.7.0
pip install "huggingface_hub>=0.23.0,<1.0.0"
pip install "transformers>=4.36.0"
pip install pandas numpy python-dotenv tiktoken
```

### 4. 環境變數設定

建立 `.env` 檔案：
```bash
# 複製環境變數範本
cp .env.example .env

# 編輯環境變數
nano .env
```

在 `.env` 檔案中設定：
```env
OPENAI_API_KEY=your_openai_api_key_here
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
VECTOR_DB_PATH=./chroma_db
COLLECTION_NAME=course_collection
COURSE_DATA_PATH=./AI課程.json
```

### 5. 初始化資料庫（首次運行）

```bash
# 執行資料庫設定腳本
python setup_database.py

# 或者手動初始化
python -c "
from rag_system import RAGSystem
from config import Config

config = Config()
rag = RAGSystem(config)
print('✅ 系統初始化完成')
rag.initialize_knowledge_base()
print('✅ 知識庫建立完成')
"
```

### 6. 直接運行應用程式

```bash
# 基本運行
streamlit run streamlit_app.py

# 指定 IP 和端口（適用於伺服器）
streamlit run streamlit_app.py --server.address=0.0.0.0 --server.port=8501

# 背景運行
nohup streamlit run streamlit_app.py --server.address=0.0.0.0 --server.port=8501 > streamlit.log 2>&1 &
```

## 🔧 Linux 專用的啟動腳本

建立一個便利的啟動腳本：

```bash
# 創建啟動腳本
cat > start_streamlit.sh << 'EOF'
#!/bin/bash

# AI課程推薦系統 - Linux 直接運行腳本

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 啟動 AI課程推薦系統${NC}"

# 檢查虛擬環境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  未找到虛擬環境，建立中...${NC}"
    python3 -m venv venv
fi

# 啟動虛擬環境
echo -e "${BLUE}📦 啟動虛擬環境...${NC}"
source venv/bin/activate

# 檢查依賴
echo -e "${BLUE}🔍 檢查依賴套件...${NC}"
if ! pip show streamlit > /dev/null 2>&1; then
    echo -e "${YELLOW}📥 安裝依賴套件...${NC}"
    pip install -r requirements_fixed.txt
fi

# 檢查環境變數
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  未找到 .env 檔案，請設定 OPENAI_API_KEY${NC}"
fi

# 檢查資料檔案
if [ ! -f "AI課程.json" ]; then
    echo -e "${RED}❌ 未找到課程資料檔案 AI課程.json${NC}"
    exit 1
fi

# 初始化知識庫（如果需要）
if [ ! -d "chroma_db" ]; then
    echo -e "${BLUE}🔧 初始化知識庫...${NC}"
    python setup_database.py
fi

# 獲取 IP 位址
LOCAL_IP=$(hostname -I | awk '{print $1}')

echo -e "${GREEN}✅ 系統檢查完成${NC}"
echo -e "${BLUE}🌐 啟動 Streamlit 應用程式...${NC}"
echo -e "${GREEN}   本地存取: http://localhost:8501${NC}"
echo -e "${GREEN}   內網存取: http://${LOCAL_IP}:8501${NC}"
echo ""

# 啟動 Streamlit
streamlit run streamlit_app.py --server.address=0.0.0.0 --server.port=8501
EOF

# 給腳本執行權限
chmod +x start_streamlit.sh
```

## 🛠️ 故障排除

### 常見問題和解決方案：

1. **Python 版本問題**：
   ```bash
   # 安裝特定版本的 Python
   sudo apt install python3.11 python3.11-venv python3.11-pip
   python3.11 -m venv venv
   ```

2. **套件安裝失敗**：
   ```bash
   # 安裝編譯依賴
   sudo apt install build-essential python3-dev
   pip install --upgrade pip setuptools wheel
   ```

3. **huggingface_hub 問題**：
   ```bash
   # 手動修復 huggingface_hub
   pip uninstall huggingface_hub sentence-transformers transformers -y
   pip install "huggingface_hub>=0.23.0" "transformers>=4.36.0" "sentence-transformers==2.7.0"
   ```

4. **權限問題**：
   ```bash
   # 確保檔案權限正確
   chmod -R 755 .
   chown -R $USER:$USER .
   ```

5. **防火牆問題**：
   ```bash
   # 開放 8501 端口
   sudo ufw allow 8501/tcp
   ```

## 📊 效能比較

| 方式 | 啟動時間 | 記憶體使用 | CPU 使用 | 維護複雜度 |
|------|----------|------------|----------|------------|
| 直接運行 | ~5-10秒 | 較低 | 較低 | 低 |
| Docker | ~20-30秒 | 較高 | 較高 | 中 |

## 🔄 服務管理

### 使用 systemd 管理服務（適用於生產環境）：

```bash
# 創建服務檔案
sudo tee /etc/systemd/system/ai-course-recommend.service > /dev/null << EOF
[Unit]
Description=AI Course Recommendation System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/streamlit run streamlit_app.py --server.address=0.0.0.0 --server.port=8501
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 啟用並啟動服務
sudo systemctl daemon-reload
sudo systemctl enable ai-course-recommend
sudo systemctl start ai-course-recommend

# 檢查狀態
sudo systemctl status ai-course-recommend
```

## 📝 總結

**推薦使用方式：**
- **開發/測試**：直接運行 → 更快速、容易除錯
- **生產部署**：Docker → 更穩定、易管理
- **個人使用**：直接運行 → 資源消耗少

直接運行完全沒問題，只要正確安裝依賴套件即可！ 