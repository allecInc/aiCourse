# 🤖 AI課程推薦機器人

基於RAG (Retrieval-Augmented Generation) 技術的智能課程推薦系統，使用 GPT-5-mini 模型，確保推薦結果精準且無幻覺。

## ✨ 系統特色

- **🎯 精準推薦**: 使用RAG技術確保推薦的課程真實存在於資料庫中
- **🚫 無幻覺**: 絕不虛構或推薦不存在的課程
- **🔍 智能檢索**: 基於語意搜索找到最相關的課程
- **🇹🇼 繁體中文支援**: 完全支援繁體中文查詢和回應
- **⚡ 即時回應**: 快速提供個人化課程建議
- **📱 友好界面**: 使用Streamlit提供直觀的網頁界面

## 🏗️ 技術架構

```
用戶查詢 → 向量化 → 向量檢索 → 相關課程 → GPT-5-mini → 個性化推薦
```

### 核心組件

- **LLM模型**: GPT-5-mini
- **嵌入模型**: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- **向量數據庫**: ChromaDB
- **檢索增強**: RAG (Retrieval-Augmented Generation)
- **使用者界面**: Streamlit
- **資料處理**: pandas, numpy

## 📋 系統需求

- Python 3.8+
- OpenAI API 金鑰
- SQL Server（提供課程資料）與 ODBC Driver 17（或相容版本）
- 至少 2GB RAM
- 可連線外網（OpenAI）與可連線到 SQL Server

## 🚀 快速開始

以下是如何設定並在本機執行此專案的步驟。

### 1. 安裝依賴套件

首先，安裝 `requirements.txt` 中列出的所有 Python 套件。建議使用 `python3 -m pip` 以確保您使用的是正確的 Python 環境。

```bash
python3 -m pip install -r requirements.txt
```

**注意**: 如果在執行下一步時遇到關於 `huggingface-hub` 的 `ImportError`，請嘗試更新 `sentence-transformers` 套件：
```bash
python3 -m pip install --upgrade sentence-transformers
```

### 2. 設定環境變數（OpenAI 與 SQL Server）

您需要一個 OpenAI API 金鑰，以及 SQL Server 連線資訊。

1. 在專案根目錄建立 `.env` 檔案。
2. 在 `.env` 檔案中加入以下內容，替換為您的實際值：

```
OPENAI_API_KEY=your_openai_api_key_here
DB_DRIVER={ODBC Driver 17 for SQL Server}
DB_SERVER=your_server.database.windows.net
DB_DATABASE=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
DB_TABLE=courses
```

### 3. 初始化向量資料庫

執行以下指令來處理課程資料、生成向量嵌入，並建立本地向量資料庫。

```bash
python3 setup_database.py
```

### 4. 啟動應用程式

執行以下腳本來同時啟動後端 API 伺服器和前端 Streamlit 應用程式：

```bash
python3 start_all_services.py
```

### 5. 開始使用

服務啟動後，您會在終端機看到以下資訊：

- **API 服務**: `http://localhost:8000`
- **網頁介面**: `http://localhost:8501`

在您的瀏覽器中開啟 **[http://localhost:8501](http://localhost:8501)** 即可開始與 AI 課程推薦系統互動！

## 🐳 使用 Docker 部署 (推薦)

對於追求環境一致性和快速部署的使用者，強烈推薦使用 Docker。這可以免去手動安裝 Python、ODBC 驅動程式和依賴套件的繁瑣步驟。

### 事前準備

- **Docker Desktop**: 請先在您的電腦上安裝 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。

### 執行步驟

1.  **設定環境變數**:
    與手動安裝一樣，請先建立 `.env` 檔案，並填入您的 OpenAI API 金鑰與 SQL Server 連線資訊。

2.  **初始化向量資料庫**:
    在專案根目錄執行：
    ```bash
    docker-compose run --rm api python setup_database.py
    ```

3.  **啟動所有服務**:
    接著，執行以下指令來建置映像檔並啟動所有服務：
    ```bash
    docker-compose up --build
    ```
    首次執行會需要幾分鐘來下載並設定環境。未來若無修改 `Dockerfile`，可直接使用 `docker-compose up` 啟動。

4.  **開始使用**:
    服務啟動後，在您的瀏覽器中開啟 **[http://localhost:8501](http://localhost:8501)** 即可開始互動。

5.  **停止服務**:
    回到執行指令的終端機，按下 `Ctrl + C`，然後可執行 `docker-compose down` 來清除容器。

## 📚 使用範例

### 查詢範例

- "我想要減肥的課程"
- "適合初學者的瑜珈"
- "高強度的有氧運動"
- "可以放鬆身心的課程"
- "游泳教學課程"
- "球類運動課程"

### 系統回應範例

```
🤖 AI推薦

根據您想要「減肥燃脂課程」的需求，我為您推薦以下課程：

⭐ 強烈推薦：燃脂活力有氧
• 類別：A 有氧系列
• 推薦理由：這是最符合您需求的課程！高強度節奏搭配超嗨音樂，每小時狂燒600大卡，是專門為想要快速燃脂的人設計的課程。

⭐ 次推薦：爆汗有氧+肌力體態雕塑
• 類別：A 有氧系列  
• 推薦理由：結合了超高強度有氧與肌力訓練，每堂課燃燒700大卡，不僅能快速甩肉，還能打造緊實線條。
```

## ⚙️ 配置說明

### config.py 主要參數

- `MODEL_NAME`: GPT 模型名稱（預設: "gpt-5-mini"）
- `RETRIEVAL_K`: 檢索課程數量（預設: 5）
- `SIMILARITY_THRESHOLD`: 相似度閾值（預設: 0.7）
- `EMBEDDING_MODEL`: 嵌入模型（預設: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"）

### 可調整參數

在Streamlit界面的側邊欄中，您可以調整：
- 檢索課程數量 (1-10)
- 相似度閾值 (0.0-1.0)

## 📁 專案結構

```
aiCourse/
├── requirements.txt       # Python 依賴
├── config.py              # 配置（模型/DB/檢索）
├── course_processor.py    # 從 SQL Server 載入/處理課程
├── vector_store.py        # 向量資料庫（ChromaDB）
├── rag_system.py          # RAG 核心與對話邏輯
├── streamlit_app.py       # Streamlit 應用
├── api_server.py          # FastAPI 服務
├── setup_database.py      # 向量庫初始化腳本（從 SQL 載入）
├── 服務啟動指南.md        # 啟動說明
└── chroma_db/             # ChromaDB 資料（持久化）
```

注意：倉庫內的 `AI課程.json` 僅作為舊版範例資料，當前版本的初始化流程與檢索均以 SQL Server 為主，不會讀取該檔案。

## 🔧 開發指南

### 自定義課程數據

請直接更新 SQL Server 中的相關課程資料表（例如 `wk00/wk01/wk02/wk03eee/wk05`），然後執行：

```bash
python setup_database.py
```

系統會重新向量化並建立本地 ChromaDB。

### 添加新功能

主要模組說明：

- **CourseProcessor**: 處理課程數據
- **VectorStore**: 管理向量數據庫
- **RAGSystem**: RAG核心邏輯
- **StreamlitApp**: 用戶界面

### API使用

```python
from rag_system import RAGSystem

# 初始化系統
rag = RAGSystem()
rag.initialize_knowledge_base()

# 獲取推薦
result = rag.get_course_recommendation("我想要減肥的課程")
print(result['recommendation'])
```

## 🐛 常見問題

### Q: 初始化失敗怎麼辦？
A: 
1. 檢查 SQL Server 連線環境變數與資料庫帳密是否正確
2. 檢查到 SQL Server 的網路連線（防火牆/ACL/VPN）
3. 確認有足夠的磁碟空間
4. 查看終端錯誤輸出/日誌

### Q: 找不到相關課程？
A: 
1. 嘗試更廣泛的關鍵字
2. 降低相似度閾值
3. 增加檢索課程數量
4. 確認 SQL Server 中確有相應課程

### Q: OpenAI API錯誤？
A: 
1. 確認API金鑰正確
2. 檢查API額度
3. 確認網路連接正常

### Q: 系統運行緩慢？
A: 
1. 檢查系統記憶體使用量
2. 減少檢索課程數量
3. 考慮使用更輕量的嵌入模型

## 📈 性能優化

- 使用 `@st.cache_resource` 快取RAG系統初始化
- ChromaDB使用持久化儲存避免重複載入
- 批次處理向量化操作
- 合理設定相似度閾值過濾無關結果

## 🔒 安全性

- API金鑰使用安全輸入框
- 不在日誌中記錄敏感資訊
- 限制查詢長度防止濫用
- 使用環境變數管理敏感配置

## 📄 授權

本專案採用 MIT 授權條款。

## 🤝 貢獻

歡迎提交 Issues 和 Pull Requests！

## 📞 聯絡資訊

如有問題或建議，請通過以下方式聯絡：
- 建立 GitHub Issue
- 發送郵件至 [您的郵箱]

---

**🎉 開始使用AI課程推薦機器人，找到最適合您的課程！** 
