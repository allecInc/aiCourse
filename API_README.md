# AI課程推薦API服務

基於RAG技術的智能課程推薦系統API版本，提供RESTful接口供第三方應用集成使用。

## 🚀 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數（可選）

創建 `.env` 檔案：
```
OPENAI_API_KEY=your-openai-api-key-here
```

### 3. 啟動API服務

```bash
python start_api_server.py
```

或直接使用uvicorn：
```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 訪問API文檔

服務啟動後，訪問以下網址：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **健康檢查**: http://localhost:8000/health

## 📋 API端點

### 基本信息

| 端點 | 方法 | 描述 |
|------|------|------|
| `/` | GET | API基本信息 |
| `/health` | GET | 健康檢查 |
| `/stats` | GET | 系統統計信息 |

### 課程相關

| 端點 | 方法 | 描述 |
|------|------|------|
| `/recommend` | POST | 智能課程推薦（使用GPT） |
| `/search` | POST | 課程搜索（僅向量檢索） |
| `/categories` | GET | 獲取所有課程類別 |
| `/categories/{category}/courses` | GET | 根據類別獲取課程 |

### 管理功能

| 端點 | 方法 | 描述 |
|------|------|------|
| `/rebuild-knowledge-base` | POST | 重建知識庫 |

## 📝 使用範例

### 1. 課程推薦

```python
import requests

# 推薦請求
response = requests.post("http://localhost:8000/recommend", json={
    "query": "我想要減肥燃脂的課程",
    "k": 5,
    "api_key": "your-openai-api-key"  # 可選，也可用環境變數
})

result = response.json()
print(result['recommendation'])
```

### 2. 課程搜索

```python
import requests

# 搜索請求
response = requests.post("http://localhost:8000/search", json={
    "query": "游泳課程",
    "k": 10
})

result = response.json()
for course in result['courses']:
    print(f"{course['title']} - 相似度: {course['similarity_score']:.3f}")
```

### 3. 獲取類別

```python
import requests

response = requests.get("http://localhost:8000/categories")
categories = response.json()
print(categories['categories'])
```

## 🔧 API客戶端

使用提供的Python客戶端：

```python
from api_client_example import CourseRecommendationAPIClient

# 初始化客戶端
client = CourseRecommendationAPIClient(
    base_url="http://localhost:8000",
    api_key="your-openai-api-key"
)

# 獲取推薦
result = client.get_recommendations("適合初學者的瑜珈課程")
print(result['recommendation'])

# 搜索課程
courses = client.search_courses("游泳", k=5)
for course in courses['courses']:
    print(course['title'])
```

## 📊 回應格式

### 課程推薦回應

```json
{
  "query": "我想要減肥燃脂的課程",
  "success": true,
  "recommendation": "根據您的需求，我為您推薦以下課程：...",
  "retrieved_courses": [
    {
      "id": "course_001",
      "title": "高強度間歇訓練",
      "category": "有氧運動",
      "description": "...",
      "similarity_score": 0.85,
      "metadata": {...}
    }
  ],
  "total_found": 5,
  "response_time": 1.23
}
```

### 課程搜索回應

```json
{
  "query": "游泳課程",
  "courses": [...],
  "total_found": 8,
  "response_time": 0.45
}
```

## ⚙️ 配置選項

### 環境變數

| 變數名 | 描述 | 預設值 |
|--------|------|--------|
| `OPENAI_API_KEY` | OpenAI API密鑰 | 無 |
| `MODEL_NAME` | OpenAI模型名稱 | gpt-4o-mini |
| `EMBEDDING_MODEL` | 嵌入模型 | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| `RETRIEVAL_K` | 預設檢索數量 | 5 |
| `SIMILARITY_THRESHOLD` | 相似度閾值 | 0.7 |

### API參數

#### 推薦請求參數

- `query` (string, 必填): 用戶查詢需求
- `k` (integer, 可選): 返回課程數量 (1-20)
- `api_key` (string, 可選): OpenAI API密鑰

#### 搜索請求參數

- `query` (string, 必填): 搜索關鍵詞
- `k` (integer, 可選): 返回課程數量 (1-50)

## 🔍 錯誤處理

API使用標準HTTP狀態碼：

| 狀態碼 | 描述 |
|--------|------|
| 200 | 成功 |
| 400 | 請求參數錯誤 |
| 500 | 服務器內部錯誤 |
| 503 | 服務不可用 |

錯誤回應格式：

```json
{
  "error": "錯誤描述",
  "status_code": 400,
  "timestamp": "2024-01-01T00:00:00"
}
```

## 🚀 部署建議

### 開發環境

```bash
python start_api_server.py
```

### 生產環境

使用Gunicorn + Nginx：

```bash
# 安裝gunicorn
pip install gunicorn

# 啟動服務
gunicorn api_server:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📈 監控與日誌

API服務包含以下監控功能：

1. **健康檢查**: `/health` 端點提供系統狀態
2. **系統統計**: `/stats` 端點提供使用統計
3. **詳細日誌**: 記錄所有請求和錯誤
4. **回應時間**: 每個請求都包含處理時間

## 🔐 安全考慮

1. **API密鑰**: 敏感信息不要硬編碼在代碼中
2. **CORS**: 生產環境中限制允許的域名
3. **速率限制**: 建議加入API請求頻率限制
4. **認證授權**: 可根據需要加入JWT等認證機制

## 📞 支援與維護

- 查看API文檔: http://localhost:8000/docs
- 健康檢查: http://localhost:8000/health
- 系統統計: http://localhost:8000/stats

## 🎯 功能特色

✅ **RESTful API**: 標準化的REST接口設計  
✅ **自動文檔**: Swagger UI和ReDoc自動生成  
✅ **類型檢查**: 使用Pydantic進行請求/回應驗證  
✅ **錯誤處理**: 完整的異常處理和錯誤回應  
✅ **CORS支援**: 跨域請求支援  
✅ **健康檢查**: 系統狀態監控  
✅ **後台任務**: 支援長時間運行的後台操作  
✅ **中文支援**: 完整的繁體中文支援  

立即開始使用AI課程推薦API，為您的應用添加智能推薦功能！ 