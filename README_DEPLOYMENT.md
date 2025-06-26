# Linux部署指南 - RAG課程推薦系統

## 📋 部署前檢查清單

### 必要文件
- [ ] 所有Python文件 (*.py)
- [ ] requirements.txt
- [ ] AI課程.json
- [ ] chroma_db/ 目錄（向量數據庫）
- [ ] .env 文件（包含OpenAI API Key）

### 系統要求
- [ ] Linux伺服器（Ubuntu 18.04+, CentOS 7+）
- [ ] Python 3.8+
- [ ] 至少2GB RAM
- [ ] 至少5GB可用磁碟空間
- [ ] 網路連接（用於OpenAI API）

## 🚀 快速部署

### 方案一：直接部署
```bash
chmod +x deploy_linux.sh
./deploy_linux.sh
```

### 方案二：Docker部署
```bash
chmod +x docker-deploy.sh
./docker-deploy.sh
```

## 🔧 配置說明

### 環境變數設置
```bash
# .env 文件內容
OPENAI_API_KEY=your_actual_openai_api_key_here
```

### 防火牆設置
```bash
# Ubuntu/Debian
sudo ufw allow 8501
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8501/tcp
sudo firewall-cmd --reload
```

### SSL證書設置（生產環境）
```bash
# 使用Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 🛡️ 安全建議

1. **API Key安全**
   - 使用環境變數存儲API Key
   - 設置.env文件權限為600
   - 定期輪換API Key

2. **網路安全**
   - 使用HTTPS
   - 設置防火牆規則
   - 限制管理端口訪問

3. **系統安全**
   - 定期更新系統
   - 使用非root用戶運行服務
   - 設置日誌監控

## 📊 監控和維護

### 服務管理命令
```bash
# 直接部署
sudo systemctl status ai-course-recommender
sudo systemctl restart ai-course-recommender
sudo journalctl -u ai-course-recommender -f

# Docker部署
docker-compose ps
docker-compose logs -f
docker-compose restart
```

### 監控腳本
```bash
chmod +x monitoring.sh
./monitoring.sh
```

### 定期備份
```bash
# 備份向量數據庫
tar -czf chroma_db_backup_$(date +%Y%m%d).tar.gz chroma_db/

# 備份配置文件
cp .env .env.backup
```

## 🔍 故障排除

### 常見問題

1. **服務無法啟動**
   - 檢查Python環境
   - 確認依賴套件安裝
   - 檢查端口是否被占用

2. **無法連接OpenAI API**
   - 檢查API Key是否正確
   - 確認網路連接
   - 檢查防火牆設置

3. **向量搜索失敗**
   - 確認chroma_db目錄存在
   - 檢查資料庫權限
   - 重新初始化資料庫

### 日誌位置
- 直接部署：`journalctl -u ai-course-recommender`
- Docker部署：`docker-compose logs`
- Nginx日誌：`/var/log/nginx/`

## 📞 支援聯絡

如遇到部署問題，請提供：
- 系統信息（Linux發行版、版本）
- 錯誤日誌
- 部署方式（直接/Docker）
- 具體錯誤描述

## 🔄 更新部署

### 應用程式更新
```bash
# 直接部署
git pull
sudo systemctl restart ai-course-recommender

# Docker部署
git pull
docker-compose build
docker-compose up -d
```

### 系統維護
- 定期清理日誌文件
- 監控磁碟使用量
- 檢查系統更新
- 備份重要數據 