from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
from server import timeit
import server
import logging
import os
import dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

dotenv.load_dotenv()

gemini = server.Gemini()
process_text = server.ProcessText()
notion = server.NotionSDK()




app = Flask(__name__)

# LINE Channel 配置
CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')

# 初始化 LINE Bot API
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

line_bot_api = MessagingApi(ApiClient(configuration))



@app.route("/callback", methods=['POST'])
def callback():
    # 取得 X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # 取得 request body
    body = request.get_data(as_text=True)

    # 處理 webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
@timeit
def handle_message(event,destination = None):
    
    
    
    
    
    try:
        if server.firebase_check(event.message.id):
            logging.info("╰(*°▽°*)╯訊息已存在於db中，跳過處理。")
            return "OK"
        is_article = process_text.home(event)
        if is_article:
            logging.info("將資料儲存到notion中")
            notion.notion_start(
                name=process_text.data_dict["ai_response"]["title"],
                tag=process_text.data_dict["ai_response"]["tag"],
                content=process_text.data_dict["ai_response"]["content"]
            )
            reply_msg = "已將資料寫入Notion。"        
        else:
            logging.info("這不是文章，無法處理。")
            reply_msg = "這不是文章"
            
    except Exception as e:
        logging.error(f"發生錯誤: {e}", exc_info=True)
        reply_msg = "發生錯誤請檢查cloud run"
    line_bot_api.reply_message_with_http_info(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[
                TextMessage(text=reply_msg)
            ]
        )

    )
    return "OK"

    
    
    
    
    
    
    
    

if __name__ == "__main__":
    app.run(debug=True, port=8080)