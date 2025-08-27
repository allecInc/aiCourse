# 1. 使用官方 Python 映像檔作為基礎
FROM python:3.10-slim

# 2. 設定工作目錄
WORKDIR /app

# 3. 安裝 Microsoft ODBC Driver for SQL Server
# 這一步是讓 pyodbc 能夠在 Linux 容器中運作的關鍵
RUN apt-get update && apt-get install -y curl apt-transport-https
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN apt-get update
RUN ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc-dev

# 4. 複製依賴套件需求檔案
COPY requirements.txt .

# 5. 安裝 Python 依賴套件
RUN pip install --no-cache-dir -r requirements.txt

# 6. 複製整個專案的程式碼到工作目錄
COPY . .

# 7. 聲明容器對外開放的端口
EXPOSE 8000
EXPOSE 8501

# 注意：CMD 或 ENTRYPOINT 將在 docker-compose.yml 中定義
