from modules.bar_generator import BarGenerator, BarResampler

class BotEngine:
    def __init__(self, strategy, recorders=None):
        """
        :param strategy: 已經初始化的策略物件 (Strategy)
        :param recorders: (選填) 字典，包含 'tick', '1min', '5min' 的記錄器
        """
        self.strategy = strategy
        self.recorders = recorders or {} # 如果沒給，就設為空字典
        
        # --- 建立 K 線合成鏈 ---
        # 邏輯順序：Tick -> 1分K -> 5分K
        
        # 1. 準備 5分K 合成器 (等待 1分K 餵給它)
        self.resampler_5m = BarResampler(interval=5, on_bar_callback=self._on_5min_bar)
        
        # 2. 準備 1分K 生成器 (等待 Tick 餵給它)
        self.bg = BarGenerator(on_bar_callback=self._on_1min_bar)

    def process_tick(self, tick):
        """
        [入口] 外部 (API 或 回測) 只要呼叫這個方法，剩下的全自動
        """
        # 1. 如果有設定 Tick 記錄器，就存檔
        if 'tick' in self.recorders:
            self.recorders['tick'].put(tick)
            
        # 2. 餵給 1分K 生成器
        self.bg.update_tick(tick)

    def _on_1min_bar(self, bar):
        """
        [內部邏輯] 當 1 分 K 生成後的標準作業程序 (SOP)
        """
        # 1. 顯示 (你可以選擇在 main 裡面印，也可以在這裡印)
        # 為了回測乾淨，我們這裡不強制 print，讓外部自己決定
        
        # 2. 存檔 (1分K)
        if '1min' in self.recorders:
            self.recorders['1min'].put(bar)
            
        # 3. 傳給 5分K 合成器
        self.resampler_5m.update_bar(bar)
        
        # 4. 【關鍵】餵給策略大腦
        self.strategy.on_bar(bar)

    def _on_5min_bar(self, bar):
        """
        [內部邏輯] 當 5 分 K 生成後的 SOP
        """
        # 1. 存檔 (5分K)
        if '5min' in self.recorders:
            self.recorders['5min'].put(bar)
            
        # 2. (選用) 如果你有 5分K 的策略，也可以在這裡呼叫
        # self.strategy.on_5min_bar(bar)