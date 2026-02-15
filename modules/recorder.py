import threading
import csv
import os
import queue  # <--- 必須引入這個
from datetime import datetime

class Recorder(threading.Thread):
    def __init__(self, symbol="TMF"):
        super().__init__()
        self.symbol = symbol
        self.running = True
        
        # [修改 1] 自己擁有一個信箱 (不再依賴外部 EventBus)
        self.queue = queue.Queue()
        
        # 準備 CSV 檔案路徑
        self.date_str = datetime.now().strftime("%Y-%m-%d")
        self.file_dir = f"data/{self.date_str}"
        os.makedirs(self.file_dir, exist_ok=True)
        self.file_path = f"{self.file_dir}/{self.symbol}_tick.csv"
        
        # 初始化 CSV
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Time", "Price", "Volume"])

    # [修改 2] 新增這個方法，讓 Engine 可以呼叫
    def put(self, tick):
        self.queue.put(tick)

    def run(self):
        print(f"💾 [Tick錄影機] 啟動！(存檔: {self.file_path})")
        
        with open(self.file_path, 'a', newline='', buffering=1) as f:
            writer = csv.writer(f)
            
            while self.running:
                try:
                    # [修改 3] 從自己的 Queue 拿資料
                    tick = self.queue.get()
                    
                    if tick is None: # 毒藥丸
                        break
                    
                    # 解析資料
                    ts = tick.datetime.strftime("%H:%M:%S.%f")[:-3]
                    price = float(tick.close)
                    volume = int(tick.volume)
                    
                    writer.writerow([ts, price, volume])
                    
                except Exception as e:
                    print(f"❌ [Tick錄影機錯誤] {e}")
        
        print("💾 [Tick錄影機] 已下班。")

    def stop(self):
        self.running = False
        self.queue.put(None)

# --- BarRecorder 保持不變，但為了完整性我也貼在這裡 ---

class BarRecorder(threading.Thread):
    def __init__(self, symbol="TMF", interval="1min"):
        super().__init__()
        self.symbol = symbol
        self.interval = interval
        self.running = True
        self.queue = queue.Queue()
        
        self.date_str = datetime.now().strftime("%Y-%m-%d")
        self.file_dir = f"data/{self.date_str}"
        os.makedirs(self.file_dir, exist_ok=True)
        self.file_path = f"{self.file_dir}/{self.symbol}_{self.interval}.csv"
        
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Time", "Open", "High", "Low", "Close", "Volume", "MA5", "MA20"])

    def put(self, bar):
        self.queue.put(bar)

    def run(self):
        print(f"🕯 [K線書記官] 啟動！(存檔: {self.file_path})")
        
        with open(self.file_path, 'a', newline='', buffering=1) as f:
            writer = csv.writer(f)
            
            while self.running:
                try:
                    bar = self.queue.get()
                    if bar is None: break

                    t_str = bar['dt'].strftime("%H:%M")
                    o = bar['open']
                    h = bar['high']
                    l = bar['low']
                    c = bar['close']
                    v = bar['volume']
                    
                    ma5 = f"{bar['ma5']:.2f}" if bar.get('ma5') else ""
                    ma20 = f"{bar['ma20']:.2f}" if bar.get('ma20') else ""
                    
                    writer.writerow([t_str, o, h, l, c, v, ma5, ma20])
                    
                except Exception as e:
                    print(f"❌ [K線存檔錯誤] {e}")
        
        print(f"🕯 [K線書記官] ({self.interval}) 已下班。")

    def stop(self):
        self.running = False
        self.queue.put(None)