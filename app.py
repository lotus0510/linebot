import os
import dotenv
import queue
import threading
import server

from server import ProcessText

from flask import Flask, request, abort

from linebot.v3.webhook import WebhookParser, MessageEvent
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    TextMessage,
    ReplyMessageRequest,
    PushMessageRequest,
    )
import json

dotenv.load_dotenv()
event_queue = queue.Queue()

# 延遲初始化 NotionSDK，避免在環境變數未設置時失敗
notion_sdk = None

app = Flask(__name__)

# 從環境變數讀取 channel token 與 secret
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# 延遲初始化 LINE Bot API 組件，避免在環境變數未設置時失敗
line_bot_api = None
parser = None

def init_line_bot_api():
    """初始化 LINE Bot API 組件"""
    global line_bot_api, parser
    
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
        raise ValueError("缺少 LINE_CHANNEL_ACCESS_TOKEN 或 LINE_CHANNEL_SECRET 環境變數")
    
    if line_bot_api is None:
        # 正確建立 Configuration 與 ApiClient
        configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
        api_client = ApiClient(configuration)
        
        # 用 ApiClient 建立 MessagingApi
        line_bot_api = MessagingApi(api_client)
        
        # 建立 webhook parser
        parser = WebhookParser(LINE_CHANNEL_SECRET)
        
        print("LINE Bot API 組件初始化完成")

@app.route("/callback", methods=["POST"])
def callback():
    """LINE Webhook 回調處理"""
    try:
        # 確保後台線程正在運行
        ensure_background_thread()
        
        # 確保 LINE Bot API 已初始化
        if line_bot_api is None or parser is None:
            init_line_bot_api()
        
        signature = request.headers.get("X-Line-Signature", "")
        body = request.get_data(as_text=True)
        
        events = parser.parse(body, signature)
        
        for event in events:
            if isinstance(event, MessageEvent):
                event_queue.put(event)
                print(f"事件已加入隊列，當前隊列大小: {event_queue.qsize()}")
        
        return "OK", 200
        
    except Exception as e:
        print(f"Callback 處理錯誤: {e}")
        abort(400)


@app.route("/healthz")
def healthz():
    """健康檢查端點，驗證服務狀態"""
    try:
        # 檢查必要的環境變數
        required_vars = ["LINE_CHANNEL_ACCESS_TOKEN", "LINE_CHANNEL_SECRET", "gemini_api", "notion_api", "notion_id"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            return {"status": "error", "missing_env_vars": missing_vars}, 500
        
        # 檢查 LINE Bot API 初始化狀態
        line_api_status = "ok" if LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET else "error"
        
        # 檢查隊列狀態
        queue_size = event_queue.qsize()
        
        # 檢查後台線程狀態
        thread_status = "running" if _background_thread_started else "not_started"
        
        return {
            "status": "healthy", 
            "queue_size": queue_size,
            "line_api_status": line_api_status,
            "background_thread": thread_status,
            "notion_sdk_initialized": notion_sdk is not None,
            "timestamp": str(threading.current_thread().ident)
        }, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500




def process_event():
    """後台線程處理事件隊列"""
    max_queue_size = 100  # 限制隊列大小防止記憶體溢出
    
    while True:
        data_dict = {}
        ai_dict = {}
        
        try:
            # 檢查隊列大小
            if event_queue.qsize() > max_queue_size:
                print(f"警告：隊列大小超過限制 ({max_queue_size})，清理舊事件")
                # 清理一半的舊事件
                for _ in range(max_queue_size // 2):
                    try:
                        event_queue.get_nowait()
                    except queue.Empty:
                        break
            
            # 獲取事件，設置超時避免無限等待
            event = event_queue.get(timeout=30)
            
            process = ProcessText()
            process.classify(event)
            data_dict = process.data_dict
            print("-" * 50)
            print(f"處理用戶 {data_dict.get('user_id', 'unknown')} 的消息")
            print(f"消息類型: {data_dict.get('type', 'unknown')}")
            print(f"原始內容長度: {len(data_dict.get('original_value', ''))}")
            print(f"提示詞是否生成: {'prompt' in data_dict}")
            
            # AI 處理
            try:
                print("傳送給AI...")
                ai_response_text = server.gemini(data_dict["prompt"])
                ai_dict = json.loads(ai_response_text)
                data_dict["ai_response"] = ai_dict.get("ai_response", "AI回覆格式錯誤")
                print(f"AI Response: {data_dict['ai_response'][:100]}...")
            except json.JSONDecodeError as e:
                print(f"AI回覆JSON解析錯誤: {e}")
                data_dict["ai_response"] = "AI回覆格式錯誤，請稍後再試"
                ai_dict = {"article_title": "錯誤", "tag": [], "ai_response": data_dict["ai_response"]}
            except Exception as e:
                print(f"AI處理錯誤: {e}")
                data_dict["ai_response"] = "AI服務暫時不可用，請稍後再試"
                ai_dict = {"article_title": "錯誤", "tag": [], "ai_response": data_dict["ai_response"]}
            
            # 回覆 LINE 消息
            try:
                # 確保 LINE Bot API 已初始化
                if line_bot_api is None:
                    init_line_bot_api()
                    
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=data_dict["ai_response"])]
                    )
                )
                print("LINE 消息回覆成功")
            except Exception as e:
                print(f"LINE 消息回覆失敗: {e}")
            
            # 保存到 Notion
            try:
                if ai_dict.get("article_title") and ai_dict.get("article_title") != "錯誤":
                    print("保存到 Notion...")
                    # 延遲初始化 NotionSDK
                    global notion_sdk
                    if notion_sdk is None:
                        notion_sdk = server.NotionSDK()
                    
                    notion_sdk.notion_start(
                        name=ai_dict.get("article_title", "未命名"),
                        tag=ai_dict.get("tag", []),
                        content=ai_dict.get("ai_response", "")
                    )
                    print("Notion 保存成功")
            except Exception as e:
                print(f"Notion 保存失敗: {e}")
                
        except queue.Empty:
            # 隊列為空，繼續等待
            continue
        except Exception as e:
            print(f"事件處理錯誤: {e}")
            continue


def start_background_thread():
    """啟動後台線程處理事件"""
    thread = threading.Thread(target=process_event, daemon=True)
    thread.start()
    print("後台事件處理線程已啟動")

# 確保後台線程在模組導入時就啟動（適用於 Gunicorn）
_background_thread_started = False

def ensure_background_thread():
    """確保後台線程只啟動一次"""
    global _background_thread_started
    if not _background_thread_started:
        start_background_thread()
        _background_thread_started = True

# 在模組級別啟動後台線程（Gunicorn 會執行這部分）
# 注意：這會在模組導入時立即執行，包括 Gunicorn 環境
ensure_background_thread()

if __name__ == "__main__":
    # 這部分只在直接運行 python app.py 時執行
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
    