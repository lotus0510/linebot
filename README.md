# LINE Bot with AI Integration

這是一個整合了 Google Gemini AI 和 Notion 的 LINE Bot 專案，可以處理文章摘要和內容分析。

## 🚀 功能特色

- **LINE Bot 整合**: 接收和回覆 LINE 訊息
- **AI 文章摘要**: 使用 Google Gemini 進行文章摘要和分析
- **Notion 儲存**: 自動將處理結果儲存到 Notion 資料庫
- **URL 解析**: 支援網頁文章內容提取
- **Cloud Run 部署**: 優化的容器化部署配置

## 📋 環境需求

- Python 3.10+
- Google Cloud Platform 帳號
- LINE Developer 帳號
- Notion 整合權限
- Google Gemini API 存取權限

## 🔧 環境變數設置

在部署前需要設置以下環境變數：

```bash
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret
gemini_api=your_gemini_api_key
notion_api=your_notion_integration_token
notion_id=your_notion_database_id
```

## 🐳 本地開發

1. 安裝依賴：
```bash
pip install -r requirements.txt
```

2. 設置環境變數（創建 .env 文件）

3. 運行應用：
```bash
python app.py
```

## ☁️ Cloud Run 部署

### 自動部署（推薦）

1. Fork 此專案
2. 在 GitHub Secrets 中設置必要的環境變數
3. 更新 `.github/workflows/deploy.yml` 中的 `PROJECT_ID`
4. 推送到 main 分支觸發自動部署

### 手動部署

```bash
# 構建 Docker 映像
docker build -t gcr.io/YOUR_PROJECT_ID/line-bot-service .

# 推送到 Container Registry
docker push gcr.io/YOUR_PROJECT_ID/line-bot-service

# 部署到 Cloud Run
gcloud run deploy line-bot-service \
  --image gcr.io/YOUR_PROJECT_ID/line-bot-service \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated
```

## 🔍 健康檢查

訪問 `/healthz` 端點檢查服務狀態：

```bash
curl https://your-service-url/healthz
```

## 📚 API 端點

- `POST /callback`: LINE Webhook 回調端點
- `GET /healthz`: 健康檢查端點

## 🛠️ 故障排除

查看 [CLOUD_RUN_FIXES.md](./CLOUD_RUN_FIXES.md) 了解常見問題和解決方案。

## 📄 授權

此專案採用 MIT 授權條款。