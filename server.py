import requests, json, os, dotenv, time
from google import genai
from google.genai.types import GenerateContentConfig
from pydantic import BaseModel, Field
import logging


from notion_client import Client
import datetime
dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



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



class Gemini():
    def __init__(self):
        self.ai_format = {
        "tag": [{"name": "value"},{"name": "value"},{"name": "value"}],
        "article_title": "value",
        "ai_response": "value"
        }
        # system_instruction 必須以list形式
        with open("data.json", "r") as f:
            self.data = json.load(f)
        
        
        self.system_prompt=[
            "你是一位小狐狸，只用繁體中文回覆。",
            "如果我給你文章的話記得幫我做簡短的摘要整理喔",
            "若不確定，請說「我不確定，建議查閱來源」。",
            "如果遇到任何無法處理、查不到資料、亂碼、測試網址，請只回傳 'bug'，不要說明、不要解釋。",
        ]
        self.client = genai.Client(api_key=os.environ["gemini_api"])
        
        
    def gemini(self,prompt,model = "gemini-2.5-flash"):
        """
        連接 Google Gemini API
        """
        grounding_tool = genai.types.Tool(
            google_search=genai.types.GoogleSearch()
        )
        cfg = GenerateContentConfig(
            system_instruction=self.system_prompt,
            temperature=0.5,
            top_p=0.9,
            tools=[grounding_tool]
        )
        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=cfg
        )
        return response.text
    def gemini_classify(self,prompt,model = "gemini-2.5-flash-lite"):
        """
        連接 Google Gemini API
        """
        cfg = GenerateContentConfig(
            system_instruction=self.data["prompt"]["system_classify"],
            temperature=0.5,
            top_p=0.9
        )
        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=cfg
        )
        return response.text
    
gm = Gemini()

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
                
    def home(self,event):
        # 基本檔案設定
        logging.info("創建基本檔案中...")
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
        classify = self.classify()
        if classify == "article":
            # TODO 處理文章類型
            logging.info("此類型為article,開始處理")
            self.data_dict['type'] = "article"
            logging.info("處理提示詞中")
            pt =self.process_prompt()
            fpt =pt+self.data_dict["message_text"]
            logging.info("獲得json格式回應中")
            self.data_dict["ai_response"] = gm.gemini(prompt=fpt)
            return True

        elif classify == "other":
            # TODO 處理其他類型
            self.data_dict["type"] = "other"
            logging.info("此類型非article(other),暫不處理")
            return None
        else:
            # TODO 處理其他類型
            logging.warning(f"❌非定義之類型{classify}")
            self.data_dict["type"] = "unknown"
            return None
            
    def classify(self):
        """
        傳入line-event
        """

        classify = gm.gemini_classify(self.data_dict["message_text"])
        
        if classify not in ("article", "other"):
            return None
        elif classify == "article":
            return "article"
        else :
            return "other"
        
        
    def process_prompt(self):
        if self.data_dict["type"] == "article":
            with open("data.json","r")  as f:
                data = json.load(f)
            prompt = data["prompt"]["format"]
            return prompt
        else:
            # TODO 暫不處理
            pass
    
    

    


    

if __name__ == "__main__":
    pt = ProcessText()
    at = "https://www.hk01.com/%E5%8D%B3%E6%99%82%E5%9C%8B%E9%9A%9B/60229193/%E7%89%B9%E6%9C%97%E6%99%AE%E9%AB%94%E6%AA%A2%E5%A0%B1%E5%91%8A-%E7%99%BD%E5%AE%AE%E9%86%AB%E7%94%9F-%E5%81%A5%E5%BA%B7%E8%89%AF%E5%A5%BD%E9%81%A9%E4%BB%BB%E7%B8%BD%E7%B5%B1%E5%8F%8A%E8%AA%8D%E7%9F%A5%E8%A9%95%E4%BC%B0%E6%BB%BF%E5%88%86"
    pt.home()


    
    
