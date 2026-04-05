FROM python:3.11-slim

WORKDIR /Code

RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    git \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

# 1. 從 GitHub 安裝 Anomalib
RUN git clone https://github.com/open-edge-platform/anomalib.git /anomalib_src && \
    cd /anomalib_src && \
    pip install -e .

# 2. 複製套件清單並安裝
COPY requirements.txt /Code/
RUN pip install --no-cache-dir -r requirements.txt

# 3. 複製專案程式碼
COPY . /Code

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]