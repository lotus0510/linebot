import requests, json, os, dotenv, time, re
from newspaper import Article
from newspaper.article import ArticleException
from google import genai
from google.genai.types import GenerateContentConfig
from pydantic import BaseModel, Field


from notion_client import Client
import datetime
dotenv.load_dotenv()
with open("data.json", "r") as f:
    data = json.load(f)

def timeit(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print("-"*100)
        print(f"Function: {func.__name__} 花費時間 {end_time - start_time} 秒")
        return result
    return wrapper
    
    

class SlotItem(BaseModel):
    name: str = Field(description="參數名稱")
    value: str = Field(description="參數值")

class Intent(BaseModel):
    intent: str = Field(description="使用者意圖")
    slot: list[SlotItem] = Field(description="參數陣列")
    
def translate_text_v2(text, target_lang, api_key, source_lang=None):
    url = "https://translation.googleapis.com/language/translate/v2"
    params = {
        "q": text,
        "target": target_lang,
        "key": api_key
    }

    if source_lang:
        params["source"] = source_lang

    response = requests.post(url, params=params)
    result = response.json()

    if 'error' in result:
        print("⚠️ API 錯誤：", result['error']['message'])
        return None

    translated = result["data"]["translations"][0]["translatedText"]
    print(f"翻譯結果：{translated}")
    return translated


class NotionSDK():
    def __init__(self):
        
        self.notion = Client(auth=os.environ["notion_api"])
        self.database_id = os.environ["notion_id"]
        self.page_id = None
        
        
    def notion_start(self,name,tag:list,content):
        """
        傳入name,tag,content
        name: 文章名稱
        tag: 文章標籤
        content: 文章內容
        """
        self.create_page(name = name, tag = tag)
        self.add_content(content=content)
        
        
    def create_page(self, name, tag:list):
        """ columns = [名稱,日期,標籤]
        tag必須為[{},{},{}] → {"name": value} """
        new_page = self.notion.pages.create(
            parent={"database_id": self.database_id},
            properties={
                "名稱": {"title": [{"text": {"content": name}}]},
                "日期": {"date": {"start": datetime.datetime.now().strftime("%Y-%m-%d")}},
                "標籤": {"multi_select": tag},
            }
        )
        self.page_id = new_page["id"]
        print("已建立Notion頁面")
        return self.page_id
    def add_content(self,content):
        self.notion.blocks.children.append(
            block_id=self.page_id,
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"text": {"content": content}}]}
            }]
            )
        print("已將內容添加到Notion頁面")

class ProcessText():
    def __init__(self):
        pass
        
        pass
    def classify(self,event):
        """
        傳入line-event
        """
        
        # 建立event_dict
        self.event_dict = {
            "type": event.type,
            "reply_token": event.reply_token,
            "source_type": event.source.type,
            "source": event.source.user_id,
            "timestamp": event.timestamp,
            "message": event.message.text,
            "message_type": event.message.type,
            "message_id": event.message.id,
            "message_text": event.message.text,
            "extend": {}
        }
        self.data_dict = {
            "message_text" : event.message.text,
            "status": "success",
        }
        
    
        
        if self.data_dict["message_text"]:
            self.re_text(text = self.data_dict["message_text"])
        else:
            print("❌ 訊息為空")
            return None
        
        if self.data_dict["type"] == "url":
            self.type_url()
        else:
            # 待處理
            pass
        
        if self.data_dict["status"] == "success":
            self.process_prompt()
        else:
            print("❌ 程序出錯")
            return None

        
        
        
    
    def re_text(self, text):
        """
        解析文字內是否包含網址
        """
        url_pattern = r'(https?://[^\s]+)'
        match = re.search(url_pattern, text)
        if match:
            print("這是url")
            url = match.group(0)
            self.data_dict["type"] = "url"
            self.data_dict["value"] = url
        else:
            print("這不是url")
            return None    
    
    
    
    def type_url(self):
        """
        處理url類型的資料
        """
        self.url_article()
    
    def type_summary(self):
        print("這是摘要類型的資料")
        self.text_summary()
        pass
    
    
    def url_article(self):
        
        yt_pattern = r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/[^\s]+'
        if self.data_dict["value"] == yt_pattern:
            print("這是youtube網址，暫時不處理")
            return None
        print("解析url資料中")
        try:
            article = Article(self.data_dict["value"], browser_user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            article.download()
            article.parse()
            self.data_dict["original_value"] = repr(article.text)
        except ArticleException as e:
            print(f"解析失敗: {e}")
            self.data_dict["status"] ="fail"

        
    def text_summary(self):
        # 待處理
        self.data_dict["type"] = "summary"
        self.data_dict["original_value"] = self.data_dict["message"]
        pass
    
    
    
    
    def process_prompt(self):
        with open("data.json", "r") as f:
            data = json.load(f)
        
        if self.data_dict["type"] == "url" and self.data_dict["original_value"] != None:
            print("提取url提示詞中")
            prompt = data["prompt"]["format"]
            self.data_dict["prompt"] = prompt + self.data_dict["original_value"]
            print("提取提示詞成功")
        
        elif self.data_dict["type"] == "summary":
            print("提取摘要提示詞中")
            prompt = data["prompt"]["summary"]
            self.data_dict["prompt"] = prompt + self.data_dict["original_value"]
        else:
            print("!"*100)
            pass

class Gemini():
    def __init__(self):
        self.ai_format = {
        "tag": [{"name": "value"},{"name": "value"},{"name": "value"}],
        "article_title": "value",
        "ai_response": "value"
        }
        # system_instruction 必須以list形式
        self.system_prompt=[
            "你是一位小狐狸，只用繁體中文回覆。",
            "如果我給你文章的話記得幫我做簡短的摘要整理喔",
            "若不確定，請說「我不確定，建議查閱來源」。"
        ]
        self.client = genai.Client(api_key=os.environ["gemini_api"])
        
        
    def gemini(self,prompt):
        """
        連接 Google Gemini API
        """
        cfg = GenerateContentConfig(
            system_instruction=self.system_prompt,
            temperature=0.5,
            top_p=0.9,
            tools=[self.basic_info]
        )
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=cfg
        )
        return response.text
    def basic_info(self):
        """
        這是一個可以獲取基本資訊的工具，例如時間
        """
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    # def gemini_classify(self,prompt):
    #     """
    #     這是一個可以分類的工具，例如分類文章
    #     """
    #     cfg = GenerateContentConfig(
    #         system_instruction=["請為以下做分類 看他屬於哪一類的訊息","目前有[文章暨url分析,聊天,翻譯,行程安排,個人花費紀錄,其他]、"],
    #         temperature=0.5,
    #         top_p=0.9,
    #         response_mime_type="application/json",
    #         response_schema=Intent
                        
    #     )
    #     response = self.client.models.generate_content(
    #         model="gemini-2.5-flash",
    #         contents=prompt,
    #         config=cfg
    #     )
    #     return response.parsed
    
    
        
        
    
    
    


    

if __name__ == "__main__":
    pass


    
    
