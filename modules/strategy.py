import os
import csv
from datetime import datetime
from config.settings import Settings

class Strategy:
    def __init__(self, bot, trader=None):
        self.bot = bot
        self.trader = trader
        self.position = 0          # 目前持倉總數 (多單為正，空單為負)
        self.entry_price = 0.0     # 成本價
        self.is_trading_active = True 
        
        # 指標記憶 (用於判斷交叉)
        self.prev_ma5 = None
        self.prev_ma20 = None
        
        # 損益統計
        self.total_profit = 0.0
        self.trade_count = 0
        
        # CSV 初始化
        self.date_str = datetime.now().strftime("%Y-%m-%d")
        self.file_dir = f"data/{self.date_str}"
        os.makedirs(self.file_dir, exist_ok=True)
        file_name = "trades_DRY_RUN.csv" if Settings.DRY_RUN else "trades_LIVE.csv"
        self.file_path = f"{self.file_dir}/{file_name}"
        
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Time", "Mode", "Action", "Price", "Profit", "Total_Profit", "Note"])

    def on_bar(self, bar):
        """策略核心邏輯：雙均線交叉判斷"""
        if not self.is_trading_active:
            if bar.get('ma5') and bar.get('ma20'):
                self.prev_ma5 = bar['ma5']
                self.prev_ma20 = bar['ma20']
            return

        # 確保有指標數據
        curr_ma5 = bar.get('ma5')
        curr_ma20 = bar.get('ma20')
        if curr_ma5 is None or curr_ma20 is None:
            return

        close_price = bar['close']
        time_str = bar['dt'].strftime("%H:%M")

        if self.prev_ma5 is not None and self.prev_ma20 is not None:
            # 🔥 黃金交叉 (MA5 往上穿過 MA20)
            if self.prev_ma5 < self.prev_ma20 and curr_ma5 > curr_ma20:
                if self.position == 0:
                    self.buy(close_price, time_str, "黃金交叉")
                elif self.position < 0:
                    self.cover(close_price, time_str, "黃金交叉(平空)")

            # 🔥 死亡交叉 (MA5 往下穿過 MA20)
            elif self.prev_ma5 > self.prev_ma20 and curr_ma5 < curr_ma20:
                if self.position == 0:
                    self.sell(close_price, time_str, "死亡交叉")
                elif self.position > 0:
                    self.sell_offset(close_price, time_str, "死亡交叉(平多)")

        # 更新記憶，供下一根 K 線比較
        self.prev_ma5 = curr_ma5
        self.prev_ma20 = curr_ma20

    # ==========================================
    # 下單執行動作
    # ==========================================

    def buy(self, price, time, note=""):
        price = float(price)
        # 🟢 邏輯加強：如果原本有空單 (position < 0)，這筆買入就是平倉動作
        if self.position < 0:
            profit = float(self.entry_price) - price
            self.total_profit += profit
            self.trade_count += 1
            msg = f"⚪ [空單平倉] {time} 價格: {price} | 損益: {profit:.0f} | 累積: {self.total_profit:.0f}"
            print(f"\n{msg}")
            self.bot.send_info("平倉通知", msg)
            self._log_trade(time, "COVER", price, profit, note)
        else:
            # 如果原本沒單或有多單，就是單純的開倉/加碼
            msg = f"🔴 [買進] {time} 價格: {price} ({note})"
            print(f"\n{msg}")
            self.bot.send_alert("策略訊號", msg)
            self._log_trade(time, "BUY", price, 0, note)

        self.position += 1  # 倉位累加
        self.entry_price = price
        
        if self.trader:
            self.trader.place_order(Settings.TARGET_CONTRACT, "Buy", 1)

    def sell(self, price, time, note=""):
        price = float(price)
        # 🟢 邏輯加強：如果原本有多單 (position > 0)，這筆賣出就是平倉動作
        if self.position > 0:
            profit = price - float(self.entry_price)
            self.total_profit += profit
            self.trade_count += 1
            msg = f"⚪ [多單平倉] {time} 價格: {price} | 損益: {profit:.0f} | 累積: {self.total_profit:.0f}"
            print(f"\n{msg}")
            self.bot.send_info("平倉通知", msg)
            self._log_trade(time, "SELL_OFFSET", price, profit, note)
        else:
            # 如果原本沒單或有空單，就是單純的開空/加碼
            msg = f"🟢 [做空] {time} 價格: {price} ({note})"
            print(f"\n{msg}")
            self.bot.send_alert("策略訊號", msg)
            self._log_trade(time, "SELL", price, 0, note)

        self.position -= 1  # 倉位累扣
        self.entry_price = price

        if self.trader:
            self.trader.place_order(Settings.TARGET_CONTRACT, "Sell", 1)

    def sell_offset(self, price, time, note=""):
        profit = float(price) - float(self.entry_price)
        self.total_profit += profit
        self.trade_count += 1
        self.position = 0 # 平倉則歸零
        msg = f"⚪ [多單平倉] {time} 價格: {price} | 損益: {profit:.0f} | 累積: {self.total_profit:.0f}"
        print(f"\n{msg}")
        self.bot.send_info("平倉通知", msg)
        self._log_trade(time, "SELL_OFFSET", price, profit, note)
        if self.trader:
            self.trader.place_order(Settings.TARGET_CONTRACT, "Sell", 1)

    def cover(self, price, time, note=""):
        profit = float(self.entry_price) - float(price)
        self.total_profit += profit
        self.trade_count += 1
        self.position = 0 # 平倉則歸零
        msg = f"⚪ [空單平倉] {time} 價格: {price} | 損益: {profit:.0f} | 累積: {self.total_profit:.0f}"
        print(f"\n{msg}")
        self.bot.send_info("平倉通知", msg)
        self._log_trade(time, "COVER", price, profit, note)
        if self.trader:
            self.trader.place_order(Settings.TARGET_CONTRACT, "Buy", 1)

    def _log_trade(self, time_str, action, price, profit, note):
        try:
            mode = "DRY_RUN" if Settings.DRY_RUN else "LIVE"
            with open(self.file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([time_str, mode, action, price, 
                                 f"{profit:.1f}" if profit != 0 else "", 
                                 f"{self.total_profit:.1f}", note])
        except Exception as e:
            print(f"❌ 紀錄 CSV 失敗: {e}")