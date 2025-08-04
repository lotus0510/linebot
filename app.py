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
import firebase

import os, time,json
import dotenv
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
    
    if firebase.is_saved(event.message.id):
        print("-"*100)
        print("╰(*°▽°*)╯訊息已經處理過，跳過。")
        return
    else:
        firebase.save_message_id(event.message.id)
        print("-"*100)
        print("╰(*°▽°*)╯處理新的訊息-寫入db。")
        
    
    
    try:
        process_text.classify(event)
        print("ai分析中")
        res =gemini.gemini(process_text.data_dict["prompt"])
        res_json = json.loads(res)
        text = "寫入notion成功"
    except Exception as e:
        print(f"❌ ai 出錯 \n{e}")
        text = "ai 出錯，請稍後再試"
        return
    try:
        notion.notion_start(name=res_json["title"],tag=res_json["tag"],content=res_json["content"])
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text=text)
                ]
            )
        )
    except Exception as e:
        print(f"❌ 寫入notion出錯 \n{e}")
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text=text)
                ]
            )
        )
    return 'OK' 

    
    
    
    
    
    
    
    

if __name__ == "__main__":
    app.run(debug=True, port=8080)