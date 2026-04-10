# 使用輕量版 python
FROM python:3.11-slim 

# 設定專案目錄
WORKDIR /Code

# 安裝必要的系統套件
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    git \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*\
    sqlite3

RUN pip install --no-cache-dir --upgrade pip

# 從 GitHub 安裝 Anomalib
RUN git clone --depth 1 https://github.com/open-edge-platform/anomalib.git /anomalib_src && \
    cd /anomalib_src && \
    pip install . --no-cache-dir

# 複製套件清單並安裝
COPY requirements.txt /Code/
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案程式碼
COPY . /Code

# 設定環境變數，在 Docker logs 中即時看到輸出
ENV PYTHONUNBUFFERED=1

# 啟動 FastAPI 伺服器
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
