# 🤖 AI課程推薦機器人

基於RAG (Retrieval-Augmented Generation) 技術的智能課程推薦系統，使用GPT-4o-mini模型，確保推薦結果精準且無幻覺。

## ✨ 系統特色

- **🎯 精準推薦**: 使用RAG技術確保推薦的課程真實存在於資料庫中
- **🚫 無幻覺**: 絕不虛構或推薦不存在的課程
- **🔍 智能檢索**: 基於語意搜索找到最相關的課程
- **🇹🇼 繁體中文支援**: 完全支援繁體中文查詢和回應
- **⚡ 即時回應**: 快速提供個人化課程建議
- **📱 友好界面**: 使用Streamlit提供直觀的網頁界面

## 🏗️ 技術架構

```
用戶查詢 → 向量化 → 向量檢索 → 相關課程 → GPT-4o-mini → 個性化推薦
```

### 核心組件

- **LLM模型**: GPT-4o-mini
- **嵌入模型**: sentence-transformers/all-MiniLM-L6-v2
- **向量數據庫**: ChromaDB
- **檢索增強**: RAG (Retrieval-Augmented Generation)
- **使用者界面**: Streamlit
- **資料處理**: pandas, numpy

## 📋 系統需求

- Python 3.8+
- OpenAI API 金鑰
- 至少 2GB RAM
- 網路連接

## 🚀 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

創建 `.env` 文件或直接在系統中設定：

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. 初始化數據庫

```bash
python setup_database.py
```

### 4. 啟動應用

```bash
streamlit run streamlit_app.py
```

### 5. 開始使用

1. 在瀏覽器中打開 `http://localhost:8501`
2. 在側邊欄輸入OpenAI API金鑰
3. 在「智能推薦」頁面輸入您的需求
4. 獲得個性化的課程推薦！

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

- `MODEL_NAME`: GPT模型名稱 (預設: "gpt-4o-mini")
- `RETRIEVAL_K`: 檢索課程數量 (預設: 5)
- `SIMILARITY_THRESHOLD`: 相似度閾值 (預設: 0.7)
- `EMBEDDING_MODEL`: 嵌入模型 (預設: "sentence-transformers/all-MiniLM-L6-v2")

### 可調整參數

在Streamlit界面的側邊欄中，您可以調整：
- 檢索課程數量 (1-10)
- 相似度閾值 (0.0-1.0)

## 📁 專案結構

```
aiSuggestCourse/
├── AI課程.json              # 課程數據文件
├── requirements.txt         # Python依賴
├── config.py               # 配置文件
├── course_processor.py     # 課程數據處理
├── vector_store.py         # 向量數據庫管理
├── rag_system.py           # RAG系統核心
├── streamlit_app.py        # Streamlit應用
├── setup_database.py       # 數據庫初始化腳本
├── README.md               # 說明文件
└── chroma_db/              # ChromaDB數據庫文件夾
```

## 🔧 開發指南

### 自定義課程數據

1. 修改 `AI課程.json` 文件
2. 重新運行 `python setup_database.py`
3. 系統會自動重建向量數據庫

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
1. 確認 `AI課程.json` 文件存在
2. 檢查網路連接
3. 確認有足夠的磁碟空間
4. 查看 `setup.log` 錯誤日誌

### Q: 找不到相關課程？
A: 
1. 嘗試更廣泛的關鍵字
2. 降低相似度閾值
3. 增加檢索課程數量

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