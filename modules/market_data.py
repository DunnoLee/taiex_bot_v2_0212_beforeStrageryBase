import os
import csv
from datetime import datetime
from config.settings import Settings

class MarketData:
    def __init__(self, api, engine, state):
        self.api = api
        self.engine = engine
        self.state = state
        self.symbol = Settings.TARGET_CONTRACT
        
        # 資料夾與檔案
        self.date_str = datetime.now().strftime("%Y-%m-%d")
        self.file_dir = f"data/{self.date_str}"
        os.makedirs(self.file_dir, exist_ok=True)
        self.file_1min = f"{self.file_dir}/{self.symbol}_1min.csv"
        self.file_5min = f"{self.file_dir}/{self.symbol}_5min.csv"
        
        for f in [self.file_1min, self.file_5min]:
            if not os.path.exists(f):
                with open(f, 'w', newline='', encoding='utf-8') as f_obj:
                    csv.writer(f_obj).writerow(["Time", "Open", "High", "Low", "Close", "Volume"])

        self.cur_1m = None
        self.cur_5m = None
        print(f"📡 [MarketData] 報價錄製官就位。")

    def connect(self):
        # 🟢 換回安靜的 v1 callback
        self.api.quote.set_on_tick_fop_v1_callback(self._on_tick_v1)
        contract = self.api.Contracts.Futures.TMF[self.symbol]
        self.api.quote.subscribe(contract, quote_type="tick")
        print(f"✅ [MarketData] 訂閱 {self.symbol} 成功。")

    def _on_tick_v1(self, exchange, tick):
        """這是最安靜的監聽方式"""
        try:
            # 💓 心跳點點
            print(".", end="", flush=True)

            # 建立內部格式
            class InternalTick:
                def __init__(self, t):
                    self.datetime = t.datetime
                    self.close = float(t.close)
                    self.volume = int(t.volume)
            
            my_tick = InternalTick(tick)
            
            # 分發
            self.state.update(my_tick)
            self.engine.process_tick(my_tick)
            self._update_bar(my_tick)
        except Exception as e:
            # 這裡不印東西，避免干擾點點
            pass

    def _update_bar(self, tick):
        # 1min 邏輯
        if self.cur_1m is None: 
            self.cur_1m = self._new_bar(tick)
        elif tick.datetime.minute != self.cur_1m['dt'].minute:
            print("") # 存檔時換行
            self._save(self.file_1min, self.cur_1m, "1min")
            self.cur_1m = self._new_bar(tick)
        else: 
            self._merge(self.cur_1m, tick)

        # 5min 邏輯
        if self.cur_5m is None: 
            self.cur_5m = self._new_bar(tick)
        elif tick.datetime.minute % 5 == 0 and tick.datetime.minute != self.cur_5m['dt'].minute:
            self._save(self.file_5min, self.cur_5m, "5min")
            self.cur_5m = self._new_bar(tick)
        else: 
            self._merge(self.cur_5m, tick)

    def _new_bar(self, t):
        return {'dt': t.datetime, 'open': t.close, 'high': t.close, 'low': t.close, 'close': t.close, 'volume': t.volume}

    def _merge(self, b, t):
        b['high'] = max(b['high'], t.close)
        b['low'] = min(b['low'], t.close)
        b['close'] = t.close
        b['volume'] += t.volume

    def _save(self, path, b, lbl):
        try:
            with open(path, 'a', newline='') as f:
                csv.writer(f).writerow([b['dt'].strftime("%Y-%m-%d %H:%M:%S"), b['open'], b['high'], b['low'], b['close'], b['volume']])
            print(f"💾 [MarketData] {lbl} 存檔 ({b['dt'].strftime('%H:%M')}) Close: {b['close']}")
        except:
            pass

    def stop(self):
        print("\n🍵 [MarketData] 報價錄製官打卡下班。")