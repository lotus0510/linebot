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

notion_sdk = server.NotionSDK()

app = Flask(__name__)

# 從環境變數讀取 channel token 與 secret
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# 正確建立 Configuration 與 ApiClient
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(configuration)

# 用 ApiClient 建立 MessagingApi（這才是正確的用法）
line_bot_api = MessagingApi(api_client)

# 建立 webhook parser
parser = WebhookParser(LINE_CHANNEL_SECRET)

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        events = parser.parse(body, signature)
    except Exception:
        abort(400)

    for event in events:
        if isinstance(event, MessageEvent):
            event_queue.put(event)
    return "OK", 200


@app.route("/healthz")
def healthz():
    return "OK", 200




def process_event():
    while True:
        data_dict = {}
        ai_dict={}
        process = ProcessText()
        try:
            event = event_queue.get()
            process.classify(event)
            data_dict = process.data_dict
            print("-"*100)
            print("傳送給AI...")
            
            try:
                # 確認gemini 已啟用response_mime_type="application/json"
                ai_dict = json.loads(server.gemini(data_dict["prompt"]))
                data_dict["ai_response"] = ai_dict["ai_response"]
                print("-"*100)
                print("AI Response:\n", data_dict["ai_response"])
            except Exception as e:
                print("-"*100)
                print(f"錯誤報告-ai_response: {e}")
                data_dict["ai_response"] = "AI回覆錯誤"
            
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=data_dict["ai_response"])]
                )
            )
        
            try:
                print("-"*100)
                print("Saving to Notion...")
                notion_sdk.notion_start(name = ai_dict["article_title"],tag = ai_dict["tag"], content = ai_dict["ai_response"])
            except Exception as e:
                print("-"*100)
                print(f"其他錯誤 無法儲存到Notion: {e}")
                
        
        except Exception as e:
            print(f"Error getting event from queue: {e}")
            print("-"*100)
            print(ai_dict)

            continue


if __name__ == "__main__":
    import os
    threading.Thread(target=process_event, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
    