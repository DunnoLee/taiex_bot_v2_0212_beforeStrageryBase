from datetime import datetime
import collections

class BarGenerator:

    def __init__(self, on_bar_callback):
        self.on_bar_callback = on_bar_callback
        self.current_bar = None
        
        # --- [新增] 用來存最近 N 根 K 棒的收盤價 ---
        # deque 是一個雙向佇列，maxlen=20 代表只保留最近 20 根
        self.history_closes = collections.deque(maxlen=20) 

    def update_tick(self, tick):
        # ... (這部分保持不變) ...
        price = float(tick.close)
        volume = int(tick.volume)
        tick_dt = tick.datetime
        tick_minute = tick_dt.replace(second=0, microsecond=0)

        if self.current_bar is None or tick_minute > self.current_bar['dt']:
            if self.current_bar:
                self.on_bar_close(self.current_bar)
            
            self.current_bar = {
                'dt': tick_minute,
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': volume
            }
        else:
            bar = self.current_bar
            bar['high'] = max(bar['high'], price)
            bar['low'] = min(bar['low'], price)
            bar['close'] = price
            bar['volume'] += volume

    def on_bar_close(self, bar):
        """K 棒完成時"""
        # 1. 把收盤價存入歷史紀錄
        self.history_closes.append(bar['close'])
        
        # 2. [新增] 計算 MA5 和 MA20
        ma5 = self.calculate_ma(5)
        ma20 = self.calculate_ma(20)
        
        # 3. 把指標塞進 bar 資料裡，方便後面的人用
        bar['ma5'] = ma5
        bar['ma20'] = ma20
        
        # 4. 送出去
        self.on_bar_callback(bar)

    def calculate_ma(self, n):
        """計算最近 n 根的平均值"""
        if len(self.history_closes) < n:
            return None # 資料不足
        
        # 取最後 n 筆資料
        # (這裡要注意：history_closes 是從舊到新，所以要切片取最後 n 個)
        # 但因為 deque 不支援直接切片，我們轉成 list 處理
        closes = list(self.history_closes)[-n:]
        return sum(closes) / n
    
class BarResampler:
    def __init__(self, interval, on_bar_callback):
        """
        :param interval: 要合成幾分鐘? (例如 5 代表 5分K)
        :param on_bar_callback: 合成完成後通知誰?
        """
        self.interval = interval
        self.on_bar_callback = on_bar_callback
        
        # 暫存區 (用來堆疊 1 分 K)
        self.bar_buffer = [] 

    def update_bar(self, bar_1min):
        """
        收到一根 1 分 K，嘗試合成 N 分 K
        """
        self.bar_buffer.append(bar_1min)

        # 檢查是否集滿了 N 根
        if len(self.bar_buffer) >= self.interval:
            self.generate_n_min_bar()

    def generate_n_min_bar(self):
        """把 buffer 裡的 1 分 K 融合成一根 N 分 K"""
        # 1. 取得第一根 (決定開盤價、時間)
        first_bar = self.bar_buffer[0]
        # 2. 取得最後一根 (決定收盤價)
        last_bar = self.bar_buffer[-1]

        # 3. 計算最高、最低、總量
        # (這裡用 Python 的生成式語法，極快)
        high_price = max(b['high'] for b in self.bar_buffer)
        low_price = min(b['low'] for b in self.bar_buffer)
        total_vol = sum(b['volume'] for b in self.bar_buffer)

        # 4. 組合出新的 N 分 K
        n_min_bar = {
            'dt': first_bar['dt'],      # 時間通常用這根 K 棒的開始時間
            'open': first_bar['open'],
            'high': high_price,
            'low': low_price,
            'close': last_bar['close'],
            'volume': total_vol,
            'interval': self.interval   # 標記這是幾分 K
        }

        # 5. 清空緩衝區
        self.bar_buffer.clear()

        # 6. 發送出去
        self.on_bar_callback(n_min_bar)