# ——— 1️⃣ builder 階段：安裝 build-time 套件，建立 Python environment ——
FROM python:3.10-slim AS builder
WORKDIR /app
ENV PYTHONUNBUFFERED=1

# 安裝 gcc/python-dev、lxml 所需 headers（newspaper3k / lxml need libxml2-dev/libxslt-dev） :contentReference[oaicite:1]{index=1}
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      gcc libffi-dev python3-dev libxml2-dev libxslt-dev make libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# 複製 requirements 並安裝 Python 套件
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# ——— 2️⃣ runtime 階段：從 builder 拆出，只留下必要程式碼與套件 ——
FROM python:3.10-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PORT=8080

# 從 builder 複製安裝好的 site‑packages，base image 不帶 build deps
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 複製程式碼與 static 檔案（例如 data.json）
COPY app.py server.py firebase.py data.json ./

EXPOSE 8080

# Entrypoint 以 gunicorn 啟動
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers=1", "--threads=8", "--timeout", "0", "app:app"]
