import time
import signal
import sys
import os
import shioaji as sj
from config.settings import Settings
from modules.market_data import MarketData
from modules.trader import Trader
from modules.strategy import Strategy
from modules.commander import Commander
from modules.notifier import TelegramBot
from core.engine import BotEngine
from core.state import SystemState
import threading

def main():
    print("🚀 [系統] 啟動中...")

    # 1. 初始化 API
    api = sj.Shioaji(simulation=False)
    print("🔐 [API] 正在進行系統登入...")
    api.login(api_key=Settings.SHIOAJI_API_KEY, secret_key=Settings.SHIOAJI_SECRET_KEY)

# 🟢 實戰模式啟動：載入憑證
    if not Settings.DRY_RUN:
        print("📜 [系統] 檢測為實戰模式，正在啟動 CA 憑證...")
        try:
            api.activate_ca(
                ca_path=Settings.SHIOAJI_CERT_PATH,
                ca_passwd=Settings.SHIOAJI_CERT_PASSWORD,
                person_id=Settings.SHIOAJI_PERSON_ID
            )
            print("✅ [系統] 憑證啟動成功！你可以正式下單了。")
        except Exception as e:
            print(f"❌ [系統] 憑證啟動失敗: {e}")
            # 安全機制：憑證失敗時，如果是實戰模式，必須強制關機
            sys.exit(1) # 憑證沒啟動就實戰是非常危險的，強制關機

    # 2. 初始化核心組件
    bot = TelegramBot()
    state = SystemState()
    trader = Trader(api=api)
    strategy = Strategy(bot=bot, trader=trader)
    engine = BotEngine(strategy=strategy)

    # 🟢 恢復：Telegram 啟動報告
    bot.send_message(f"🚀 **交易機器人已上線**\n合約：{Settings.TARGET_CONTRACT}\n模式：{'演習' if Settings.DRY_RUN else '實戰'}")

    md = MarketData(api=api, engine=engine, state=state)
    commander = Commander(bot=bot, system_state=state, trader=trader, strategy=strategy)
    
    commander.daemon = True 
    commander.start()

    # 3. 執行初始同步
    sync_msg = commander._sync_strategy_position()
    bot.send_message(f"🔄 **初始同步完成**\n{sync_msg}")

    # 4. 連線行情
    md.connect()

    print("✅ [系統] 運作中。按 Ctrl+C 可安排機器人集體下班。")
    
    # 5. 處理成交與訂單回報
    def on_order_event(order_state, message):
        try:
            state_str = str(order_state)
            # 偵測到成交事件
            if "Deal" in state_str:
                print(f"\n⚡ [系統] 偵測到成交，啟動延時同步回報...")

                def delayed_sync_report():
                    # 1. 稍微等待券商後端更新持倉列表
                    time.sleep(1.5) 
                    
                    # 2. 執行同步並取得回報字串
                    # 註：commander._sync_strategy_position() 內部已經會計算口數與均價
                    report_msg = commander._sync_strategy_position()
                    
                    # 3. 將同步後的「真實狀態」回報至 Telegram
                    bot.send_message(f"📊 **成交自動同步報告**\n{report_msg}")
                
                # 開啟背景執行緒執行，不卡住主程式
                threading.Thread(target=delayed_sync_report, daemon=True).start()
                
        except Exception as e:
            print(f"⚠️ 處理成交回報發生錯誤: {e}")

    # 綁定回報功能
    api.set_order_callback(on_order_event)
    
    # 5. 優雅退場機制
    def exit_gracefully(signum, frame):
        print("\n\n🔔 [系統] 收到下班指令，正在安排人員撤離...")
        # 🟢 恢復：Telegram 下班報告
        bot.send_message("👋 **機器人收到下班指令，正在關閉系統...**")
        try:
            md.stop()        # 報價部門回報
            commander.stop() # 指揮官部門回報
            api.logout()
            print("✅ [API] 帳號登出成功。")
            bot.send_message("💤 **系統已安全離線。下班囉！**")
        except Exception as e:
            print(f"⚠️ [系統] 關閉時發生微小異常: {e}")
            bot.send_message(f"⚠️ 關閉時有異常，請手動確認帳戶狀態。")

        os._exit(0)

    signal.signal(signal.SIGINT, exit_gracefully)
    
    while True:
        try:
            time.sleep(0.5)
        except KeyboardInterrupt:
            exit_gracefully(None, None)

if __name__ == "__main__":
    main()