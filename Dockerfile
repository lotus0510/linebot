# 基底映像
FROM python:3.10-slim
WORKDIR /app

# 安裝套件
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# 用 Gunicorn 為 WSGI server
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]
