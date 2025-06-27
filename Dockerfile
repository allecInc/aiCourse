# 使用官方Python基礎映像
FROM python:3.13-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 複製requirements文件
COPY requirements_fixed.txt .

# 升級pip並安裝依賴
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements_fixed.txt

# 複製應用程式文件
COPY . .

# 創建chroma_db目錄（如果不存在）
RUN mkdir -p chroma_db

# 設置環境變數
ENV PYTHONPATH=/app
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_PORT=8501
ENV TRANSFORMERS_CACHE=/app/.cache/transformers
ENV HF_HOME=/app/.cache/huggingface

# 創建快取目錄
RUN mkdir -p /app/.cache/transformers /app/.cache/huggingface

# 暴露端口
EXPOSE 8501

# 設置健康檢查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# 啟動應用程式
CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"] 