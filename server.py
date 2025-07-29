import requests, json, os, dotenv, datetime, re
from newspaper import Article

from google import genai
from google.genai.types import GenerateContentConfig

from notion_client import Client

dotenv.load_dotenv()
with open("data.json", "r") as f:
    data = json.load(f)


    

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

def gemini(prompt):
    """
    連接 Google Gemini API
    """
    ai_format = {
    "tag": [{"name": "value"},{"name": "value"},{"name": "value"}],
    "article_title": "value",
    "ai_response": "value"
    }
    
    client = genai.Client(api_key=os.environ["gemini_api"])
    cfg = GenerateContentConfig(
        system_instruction=[
            "你是一位小狐狸，只用繁體中文回覆。",
            f"請用特定的格式回傳給我喔\n請不要加上```，只需純 JSON 格式\n",
            ai_format,
            "可以調用basic_info 獲取基本資訊喔",
            "如果我給你文章的話記得幫我做簡短的摘要整理喔",
            "若不確定，請說「我不確定，建議查閱來源」。"
            ],
        temperature=0.5,
        top_p=0.9,
        response_mime_type="application/json",

    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=cfg
    )
    return response.text


class NotionSDK():
    def __init__(self):
        self.notion = Client(auth=os.environ["notion_api"])
        self.database_id = os.environ["notion_id"]
        self.page_id = None
    def notion_start(self,name,tag:list,content):
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
        self.data_dict={
            "user_id": event.source.user_id,
            "message": event.message.text,
        }
        
        if self.re_text(event.message.text):
            self.type_url()
        else:
            # 待處理
            self.type_summary()
            pass
        self.process_prompt()
        
        
    
    def re_text(self, text):
        url_pattern = r'(https?://[^\s]+)'
        match = re.search(url_pattern, text)
        if match:
            print("這是url")
            url = match.group(0)
            self.data_dict["type"] = "url"
            self.data_dict["value"] = url
            return url
        else:
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
        
        article = Article(self.data_dict["value"], browser_user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        article.download()
        article.parse()
        
        if article.text:
            print("url解析成功")
            self.data_dict["original_value"] = repr(article.text)
            return repr(article.text)    
        else:
            print("該網站暫時無法解析")
            return None
        
    def text_summary(self):
        # 待處理
        self.data_dict["type"] = "summary"
        self.data_dict["original_value"] = self.data_dict["message"]
        pass
    
    
    
    
    def process_prompt(self):
        with open("data.json", "r") as f:
            data = json.load(f)
        
        if self.data_dict["type"] == "url":
            print("提取url提示詞中")
            prompt = data["prompt"]["url"]
            self.data_dict["prompt"] = prompt + self.data_dict["original_value"]
        
        if self.data_dict["type"] == "summary":
            print("提取摘要提示詞中")
            prompt = data["prompt"]["summary"]
            self.data_dict["prompt"] = prompt + self.data_dict["original_value"]
        else:
            print("!"*100)

def basic_info():
    """
    這是一個獲取時間的工具
    """
    basic_info = {
        "time" :datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return basic_info
        
        
    
    
    


    

if __name__ == "__main__":

    text = '現在時間'
    print(json.loads(gemini(text)))
    
    
