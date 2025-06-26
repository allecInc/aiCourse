# 🛠️ HuggingFace Hub 相容性問題修復指南

## 問題描述
在 Docker 部署到 Linux 時遇到以下錯誤：
```
ImportError: cannot import name 'cached_download' from 'huggingface_hub'
```

## 問題原因
這是由於 `huggingface_hub` 版本相容性問題導致的。在較新版本的 `huggingface_hub` 中，`cached_download` 函數已被移除或重命名為 `hf_hub_download`。

## 🔧 解決方案

### 方案一：使用修復後的檔案部署（推薦）

我已經為您修復了以下檔案：

1. **`requirements_fixed.txt`** - 更新了相容的套件版本：
   ```
   huggingface_hub>=0.23.0,<1.0.0
   transformers>=4.36.0
   sentence-transformers==2.7.0
   ```

2. **`Dockerfile`** - 改進了依賴安裝方式
3. **`docker-deploy-fixed.sh`** - 新的部署腳本（Linux/Mac 使用）

### 方案二：手動修復步驟

#### 在 Windows 上：

1. **停止現有服務**：
   ```powershell
   docker-compose down
   ```

2. **清理舊映像**（可選）：
   ```powershell
   docker system prune -f
   docker image rm aisuggestcourse-app
   ```

3. **重新建構並啟動**：
   ```powershell
   docker-compose build --no-cache
   docker-compose up -d
   ```

#### 在 Linux/Mac 上：

1. **使用修復腳本**：
   ```bash
   chmod +x docker-deploy-fixed.sh
   ./docker-deploy-fixed.sh
   ```

或手動執行：

```bash
# 停止現有服務
docker-compose down --remove-orphans

# 重新建構
docker-compose build --no-cache

# 啟動服務
docker-compose up -d
```

### 方案三：在已執行容器中修復

如果容器已在執行但有問題，可以進入容器進行修復：

```bash
# 進入容器
docker-compose exec app bash

# 更新套件
pip install --upgrade huggingface_hub>=0.23.0 transformers>=4.36.0

# 重啟應用
exit
docker-compose restart
```

## 🔍 驗證修復

### 檢查套件版本
```bash
docker-compose exec app python -c "
import huggingface_hub
import sentence_transformers
print(f'huggingface_hub: {huggingface_hub.__version__}')
print(f'sentence-transformers: {sentence_transformers.__version__}')
"
```

### 測試功能
```bash
docker-compose exec app python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
embedding = model.encode(['測試文本'])
print(f'✅ 測試成功，向量維度: {len(embedding[0])}')
"
```

## 📋 故障排除

### 如果仍然出現錯誤：

1. **檢查日誌**：
   ```bash
   docker-compose logs -f
   ```

2. **完全重置**：
   ```bash
   docker-compose down -v
   docker system prune -af
   docker-compose up --build
   ```

3. **檢查網路連接**：
   確保容器可以存取 HuggingFace Hub 下載模型

### 常見錯誤和解決方案：

| 錯誤訊息 | 解決方案 |
|----------|----------|
| `cached_download not found` | 更新 `huggingface_hub` 到 >=0.23.0 |
| `Cannot load model` | 檢查網路連接和模型名稱 |
| `Memory error` | 增加 Docker 記憶體限制 |

## 🚀 最佳實踐

1. **固定版本**：使用 `requirements_fixed.txt` 而不是 `requirements.txt`
2. **定期更新**：定期檢查並更新相容性
3. **監控日誌**：啟動後檢查應用程式日誌
4. **備份數據**：部署前備份 `chroma_db` 資料夾

## 📞 需要協助？

如果問題仍然存在，請提供：
1. 完整的錯誤日誌 (`docker-compose logs`)
2. 系統資訊 (OS, Docker 版本)
3. 使用的命令和步驟

---

**最後更新**：$(date)
**狀態**：✅ 已修復並測試 