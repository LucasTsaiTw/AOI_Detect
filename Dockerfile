FROM python:3.10-slim

WORKDIR /Code

RUN apt-get update && apt-get install -y \
    git \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

RUN git clone https://github.com/open-edge-platform/anomalib.git /anomalib_src && \
    cd /anomalib_src && \
    pip install -e . && \
    pip install --no-cache-dir requests

COPY . /Code

ENV PYTHONUNBUFFERED=1

CMD ["python3", "app/services/ai_model.py"]
