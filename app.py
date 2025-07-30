from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import server
import time
app = Flask(__name__)
process_text = server.ProcessText()


# 你的 LINE CHANNEL ACCESS TOKEN 和 CHANNEL SECRET
LINE_CHANNEL_ACCESS_TOKEN = '你的 Channel Access Token'
LINE_CHANNEL_SECRET = '你的 Channel Secret'

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    t0 = time.time()
    
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
        
    t1 = time.time()
    print(f"Request processed in {t1 - t0:.2f} seconds")
    return 'OK'

# 簡單的 message event 處理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    
    process_text.classify(event)
    
    
    
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text)
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
