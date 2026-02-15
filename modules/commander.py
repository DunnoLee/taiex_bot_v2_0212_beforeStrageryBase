import threading
import time
from datetime import datetime
from config.settings import Settings

class Commander(threading.Thread):
    def __init__(self, bot, system_state, trader=None, strategy=None):
        super().__init__()
        self.bot = bot
        self.state = system_state
        self.trader = trader
        self.strategy = strategy
        self.running = True

    def _sync_strategy_position(self):
        print("🔄 [Commander] 正在執行倉位同步...")
        if not self.trader or not self.strategy: return "❌ 缺少組件"
        try:
            real_positions = self.trader.get_positions()
            total_qty = 0
            weighted_sum = 0.0
            
            # 🟢 修正：取得乾淨的大寫前三碼 (例如 TMF)
            target_prefix = Settings.TARGET_CONTRACT[:3].strip().upper()
            
            for p in real_positions:
                # 🟢 修正：使用更寬鬆的 "in" 比對，並強制轉大寫
                p_code = p['code'].strip().upper()
                
                if target_prefix in p_code:
                    qty = int(p['quantity'])
                    # 統一比對 Buy/Sell 字串
                    direction = p['direction'].strip().capitalize()
                    
                    side_qty = qty if direction == "Buy" else -qty
                    total_qty += side_qty
                    weighted_sum += (float(p['price']) * qty)
            
            avg_price = (weighted_sum / abs(total_qty)) if total_qty != 0 else 0
            
            # 強制更新策略記憶
            self.strategy.position = total_qty
            self.strategy.entry_price = avg_price
            
            # 回報文字加強
            side_text = "多單" if total_qty > 0 else ("空單" if total_qty < 0 else "空手")
            return f"✅ 同步完成！\n識別產品: {target_prefix}\n目前倉位: {side_text} {abs(total_qty)} 口\n均價: {avg_price:.0f}"
        except Exception as e:
            return f"❌ 同步失敗: {e}"

    def handle_command(self, text):
        """還原你習慣的指令處理邏輯與訊息"""
        raw_parts = text.strip().split()
        if not raw_parts: return
        cmd = raw_parts[0].lower().replace("_", "") 
        arg = raw_parts[1] if len(raw_parts) > 1 else "1"

        print(f"\n📥 [指令] 收到: {text} ... 處理中 ...")

        if cmd == "/start":
            self.bot.send_message("👋 嗨！我是你的交易指揮官。\n輸入 /help 查看指令。")

        elif cmd == "/help":
            # 還原回你原本習慣的簡約格式
            msg = ("📜 **指令清單**\n----------------\n"
                   "/status - 系統狀態\n/account - 帳戶權益\n"
                   "/stoptrade - 🛑 暫停交易\n/starttrade - 🟢 啟動交易\n"
                   "/buy [量] - 買進\n/sell [量] - 賣出\n/flatten - 全平倉\n/sync - 同步")
            self.bot.send_message(msg)

        elif cmd == "/status":
            tick = self.state.get_latest_tick()
            if tick:
                strat_status = "🟢 運作中" if self.strategy.is_trading_active else "🛑 已暫停"
                msg = (f"📊 **系統狀態**\n----------------\n🕒 時間: {tick.datetime.strftime('%H:%M:%S')}\n"
                       f"💰 現價: {tick.close}\n🤖 策略: {strat_status}\n📦 策略倉位: {self.strategy.position} 口")
                self.bot.send_message(msg)
            else:
                self.bot.send_message("⚠️ 尚未收到行情數據...")

        elif cmd == "/account":
            self.bot.send_message("⏳ 查詢中...")
            positions = self.trader.get_positions()
            pos_str = "無持倉"
            if positions:
                pos_str = "".join([f"\n👉 {p['direction']} {p['code']} x{p['quantity']} @ {p['price']:.0f}" for p in positions])
            balance = self.trader.get_account_balance()
            bal_str = f"${balance['equity']:.0f}" if balance else "無法取得"
            self.bot.send_message(f"💰 **帳戶概況**\n----------------\n💵 權益數: {bal_str}\n📦 持倉: {pos_str}")

        elif cmd == "/stoptrade":
            self.strategy.is_trading_active = False
            self.bot.send_message("🛑 **自動交易已暫停**")

        elif cmd == "/starttrade":
            sync_msg = self._sync_strategy_position()
            self.strategy.is_trading_active = True
            self.bot.send_message(f"{sync_msg}\n🚀 **自動交易已恢復**")

        elif cmd == "/sync":
            self.bot.send_message(self._sync_strategy_position())

        elif cmd in ["/buy", "/long"]:
            price = self.state.get_latest_tick().close if self.state.get_latest_tick() else 0
            for _ in range(int(arg)): self.strategy.buy(0, datetime.now().strftime("%H:%M"), "手動指令")

        elif cmd in ["/sell", "/short"]:
            price = self.state.get_latest_tick().close if self.state.get_latest_tick() else 0
            for _ in range(int(arg)): self.strategy.sell(0, datetime.now().strftime("%H:%M"), "手動指令")

        elif cmd in ["/flatten", "/closeall"]:
            price = self.state.get_latest_tick().close if self.state.get_latest_tick() else 0
            t_str = datetime.now().strftime("%H:%M")
            if self.strategy.position > 0: self.strategy.sell_offset(price, t_str, "手動全平")
            elif self.strategy.position < 0: self.strategy.cover(price, t_str, "手動全平")
            else: self.bot.send_message("✅ 目前空手")

    def run(self):
        print("🎮 [Commander] 遙控器部門已就位。")
        last_update_id = None
        while self.running:
            try:
                updates = self.bot.get_updates(offset=last_update_id)
                if updates:
                    for update in updates:
                        last_update_id = update["update_id"] + 1
                        if "message" in update and "text" in update["message"]:
                            self.handle_command(update["message"]["text"])
                time.sleep(1)
            except:
                time.sleep(5)

    def stop(self):
        print("📱 [Commander] 遙控器部門下班打卡。")
        self.running = False