import requests, json, os, dotenv, datetime, re
from newspaper import Article

from google import genai
from google.genai.types import GenerateContentConfig

from notion_client import Client

dotenv.load_dotenv()

# 使用絕對路徑讀取配置文件
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
data_file_path = os.path.join(current_dir, "data.json")

try:
    with open(data_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"警告：找不到配置文件 {data_file_path}，使用默認配置")
    data = {
        "url": [],
        "prompt": {
            "url": "將以下文章作摘要,不要回答其他任何東西 \n",
            "summary": "幫我將文章做摘要整理: \n"
        }
    }


    

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
    連接 Google Gemini API，增加錯誤處理和重試機制
    """
    ai_format = {
        "tag": [{"name": "value"}, {"name": "value"}, {"name": "value"}],
        "article_title": "value",
        "ai_response": "value"
    }
    
    # 檢查 API key
    api_key = os.environ.get("gemini_api")
    if not api_key:
        raise ValueError("缺少 gemini_api 環境變數")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            client = genai.Client(api_key=api_key)
            cfg = GenerateContentConfig(
                system_instruction=[
                    "你是一位小狐狸，只用繁體中文回覆。",
                    f"請用特定的格式回傳給我喔\n請不要加上```，只需純 JSON 格式\n{json.dumps(ai_format, ensure_ascii=False)}",
                    "可以調用basic_info 獲取基本資訊喔",
                    "如果我給你文章的話記得幫我做簡短的摘要整理喔",
                    "若不確定，請說「我不確定，建議查閱來源」。"
                ],
                temperature=0.5,
                top_p=0.9,
                response_mime_type="application/json",
            )
            
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=prompt,
                config=cfg
            )
            
            if response and response.text:
                return response.text
            else:
                raise ValueError("Gemini API 返回空回應")
                
        except Exception as e:
            print(f"Gemini API 調用失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                # 最後一次嘗試失敗，返回錯誤格式的回應
                error_response = {
                    "tag": [{"name": "錯誤"}],
                    "article_title": "API錯誤",
                    "ai_response": f"抱歉，AI服務暫時不可用。錯誤：{str(e)}"
                }
                return json.dumps(error_response, ensure_ascii=False)
            
            # 等待後重試
            import time
            time.sleep(1 * (attempt + 1))


class NotionSDK():
    def __init__(self):
        # 檢查必要的環境變數
        notion_api = os.environ.get("notion_api")
        notion_id = os.environ.get("notion_id")
        
        if not notion_api:
            raise ValueError("缺少 notion_api 環境變數")
        if not notion_id:
            raise ValueError("缺少 notion_id 環境變數")
            
        try:
            self.notion = Client(auth=notion_api)
            self.database_id = notion_id
            self.page_id = None
        except Exception as e:
            print(f"Notion 客戶端初始化失敗: {e}")
            raise
    def notion_start(self, name, tag: list, content):
        """啟動 Notion 頁面創建流程，增加錯誤處理"""
        try:
            self.create_page(name=name, tag=tag)
            self.add_content(content=content)
        except Exception as e:
            print(f"Notion 操作失敗: {e}")
            raise
        
        
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
        
        print(f"收到消息: {event.message.text}")
        
        if self.re_text(event.message.text):
            print("識別為 URL 類型")
            self.type_url()
        else:
            print("識別為摘要類型")
            self.type_summary()
        
        self.process_prompt()
        print(f"最終 prompt: {self.data_dict.get('prompt', 'None')[:100]}...")
        
        
    
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
        """處理 URL 文章解析，增加錯誤處理和超時機制"""
        try:
            yt_pattern = r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/[^\s]+'
            if re.match(yt_pattern, self.data_dict["value"]):
                print("這是youtube網址，暫時不處理")
                self.data_dict["original_value"] = "YouTube 連結暫不支援解析，請提供文字內容。"
                return None
            
            # 增加超時和錯誤處理
            article = Article(
                self.data_dict["value"], 
                browser_user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # 設置超時
            article.download()
            article.parse()
            
            if article.text and len(article.text.strip()) > 50:
                print(f"URL解析成功，文章長度: {len(article.text)} 字符")
                # 限制文章長度避免超過 API 限制
                max_length = 8000
                if len(article.text) > max_length:
                    article_text = article.text[:max_length] + "...(文章過長，已截斷)"
                else:
                    article_text = article.text
                    
                self.data_dict["original_value"] = article_text
                return article_text
            else:
                print("該網站內容為空或過短")
                self.data_dict["original_value"] = "無法解析該網站內容，請檢查網址是否正確。"
                return None
                
        except Exception as e:
            print(f"URL解析錯誤: {e}")
            self.data_dict["original_value"] = f"網站解析失敗: {str(e)}"
            return None
        
    def text_summary(self):
        """處理文字摘要類型的資料"""
        self.data_dict["type"] = "summary"
        self.data_dict["original_value"] = self.data_dict["message"]
        print(f"設置摘要類型，原始內容: {self.data_dict['original_value'][:50]}...")
    
    
    
    
    def process_prompt(self):
        """處理提示詞生成，使用全局 data 變數"""
        try:
            message_type = self.data_dict.get("type", "summary")
            print(f"處理提示詞，消息類型: {message_type}")
            
            if message_type == "url":
                print("提取url提示詞中")
                prompt = data["prompt"]["url"]
                original_value = self.data_dict.get("original_value", "")
                self.data_dict["prompt"] = prompt + original_value
            elif message_type == "summary":
                print("提取摘要提示詞中")
                prompt = data["prompt"]["summary"]
                original_value = self.data_dict.get("original_value", self.data_dict["message"])
                self.data_dict["prompt"] = prompt + original_value
            else:
                print("未知的消息類型，使用默認摘要處理")
                prompt = data["prompt"]["summary"]
                original_value = self.data_dict.get("original_value", self.data_dict["message"])
                self.data_dict["prompt"] = prompt + original_value
                
            print(f"生成的提示詞長度: {len(self.data_dict['prompt'])}")
        except Exception as e:
            print(f"提示詞處理錯誤: {e}")
            # 使用默認提示詞
            fallback_content = self.data_dict.get("original_value", self.data_dict.get("message", "無內容"))
            self.data_dict["prompt"] = "請幫我整理以下內容：\n" + fallback_content
            print(f"使用默認提示詞，長度: {len(self.data_dict['prompt'])}")

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
    
    
