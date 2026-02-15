# modules/mock.py
from datetime import datetime

class MockTick:
    """假裝是 Shioaji 的 Tick"""
    def __init__(self, code, dt, price, volume):
        self.code = code
        self.datetime = dt
        self.close = price
        self.volume = volume

class MockBot:
    """假裝是 TelegramBot"""
    def send_message(self, text):
        print(f"🤖 [MockTG] {text}")
    def send_alert(self, title, msg):
        print(f"🚨 [MockTG 警報] {title} - {msg}")
    def send_info(self, title, msg):
        print(f"ℹ️ [MockTG 通知] {title} - {msg}")

# --- 👇 新增：假 API 相關類別 👇 ---

class MockContract:
    """假裝是合約物件"""
    def __init__(self, code):
        self.code = code
        self.name = f"Mock_{code}"

class MockShioaji:
    """
    這是一個高仿真的 Shioaji API 物件。
    目的是騙過 Trader，讓它以為自己連上了真正的交易所。
    """
    def __init__(self):
        # 1. 建立假的帳號
        self.stock_account = "Mock_Account_123"
        
        # 2. 建立假的合約結構 (Contracts.Futures.TMF[code])
        # 這是一層一層的洋蔥，為了配合 Shioaji 的語法結構
        class Futures:
            def __init__(self):
                self.TMF = {} 
                # 魔法：不管查什麼合約代號，都自動生成一個假合約回傳
                class AutoDict(dict):
                    def __missing__(self, key):
                        return MockContract(key)
                self.TMF = AutoDict()
                
        class Contracts:
            def __init__(self):
                self.Futures = Futures()
                # 如果你也做股票，這裡要加 Stocks...
                
        self.Contracts = Contracts()

    def Order(self, **kwargs):
        """假裝建立訂單 (回傳字典方便查看)"""
        return kwargs

    def place_order(self, contract, order):
        """假裝送出訂單 (這是 Trader 最後呼叫的地方)"""
        print(f"🌈 [MockAPI] 收到 API 請求！")
        print(f"    目標合約: {contract.code}")
        print(f"    訂單內容: {order}")
        
        # 回傳一個假的 Trade 物件
        class MockTrade:
            status = "Success"
            order_id = "Mock_Order_999"
            def __repr__(self): return f"<Trade {self.order_id}>"
            
        return MockTrade()
    
    # --- 👇 新增：假查詢功能 👇 ---
    def update_status(self):
        pass # 假裝更新

    def list_positions(self, account):
        """假裝回傳倉位 (預設回傳空手)"""
        return [] 
        # 如果你想測試有倉位的情況，可以回傳假的 Position 物件
    
    def account_balance(self):
        """假裝回傳權益數"""
        class MockBalance:
            equity = 1000000
            available_margin = 900000
            total_pnl = 5000
        return MockBalance()