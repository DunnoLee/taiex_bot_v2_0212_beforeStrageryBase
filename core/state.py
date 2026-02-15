import threading

class SystemState:
    """
    系統狀態中心 (戰情室)
    負責儲存最新的盤勢資訊，供其他模組查詢。
    """
    def __init__(self):
        self._lock = threading.Lock() # 加個鎖，避免多執行緒讀寫打架
        self.tick = None

    def update(self, tick):
        """更新最新行情"""
        with self._lock:
            self.tick = tick

    # 👇 [新增] 這就是 Commander 缺少的拼圖 👇
    def get_latest_tick(self):
        """回傳最新的 Tick 物件 (如果有的話)"""
        with self._lock:
            return self.tick