import requests
import time
from config.settings import Settings

class TelegramBot:
    def __init__(self):
        self.token = Settings.TELEGRAM_TOKEN
        self.chat_id = Settings.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, text):
        """發送一般訊息"""
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown" # 支援粗體等格式
        }
        try:
            requests.post(url, data=data, timeout=5)
        except Exception as e:
            print(f"❌ [TG發送失敗] {e}")

    def send_alert(self, title, msg):
        """發送警報 (加上警示圖示)"""
        text = f"🚨 *{title}*\n----------------\n{msg}"
        self.send_message(text)

    def send_info(self, title, msg):
        """發送通知 (加上資訊圖示)"""
        text = f"ℹ️ *{title}*\n----------------\n{msg}"
        self.send_message(text)

    # 👇 [新增] 這就是 Commander 缺少的耳朵 👇
    def get_updates(self, offset=None):
        """
        向 Telegram 伺服器查詢有沒有新訊息
        :param offset: 上次讀到的訊息 ID (避免重複讀取)
        """
        url = f"{self.base_url}/getUpdates"
        params = {
            "timeout": 10,  # Long Polling: 如果沒訊息，連線會掛著等 10 秒
            "offset": offset
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            result = resp.json()
            
            if result.get("ok"):
                return result.get("result", [])
            else:
                print(f"⚠️ [TG接收錯誤] {result}")
                return []
        except requests.exceptions.ReadTimeout:
            # 這是正常的，代表這 10 秒內沒人講話
            return []
        except Exception as e:
            print(f"❌ [TG連線失敗] {e}")
            return []