import csv
import time
import pandas as pd  # 記得 pip install pandas
from datetime import datetime
from modules.strategy import Strategy
from modules.mock import MockTick, MockBot, MockShioaji
from modules.trader import Trader
from core.engine import BotEngine
from config.settings import Settings

# ---------------------------------------------------------
# 🎯 設定你要回測的目標檔案
# ---------------------------------------------------------
# 選項 A: 你剛剛跑出來的熱騰騰資料 (記得改日期)
#CSV_FILE_PATH = f"data/{datetime.now().strftime('%Y-%m-%d')}/{Settings.TARGET_CONTRACT}_1min.csv"

# 選項 B: 歷史下載資料 (想測這個就把上面註解掉，打開下面)
CSV_FILE_PATH = f"data/history/{Settings.TARGET_CONTRACT}_1min_history.csv"
# ---------------------------------------------------------

def calculate_indicators(df):
    """
    [回測引擎核心] 動態計算技術指標
    這讓我們可以隨意調整參數 (例如 MA5 改 MA10)，而不需重新錄製資料
    """
    # 確保資料按時間排序
    df.sort_index(inplace=True)
    
    # 計算 MA (使用 Pandas 的 rolling 函式，速度極快)
    df['MA5'] = df['Close'].rolling(window=15).mean()#5
    df['MA20'] = df['Close'].rolling(window=150).mean()#20
    
    # 這裡也可以加 RSI, MACD, Bollinger Bands...
    # df['RSI'] = ...
    
    return df

def run_backtest():
    print(f"⏳ [回測] 正在讀取: {CSV_FILE_PATH}")

    # 1. 讀取 CSV 並清洗資料
    try:
        # 使用 Pandas 讀取
        df = pd.read_csv(CSV_FILE_PATH)
        
        # 統一欄位名稱 (首字大寫)，處理不同來源的格式差異
        # 錄製的可能是 'close', 下載的可能是 'Close'
        df.columns = [c.capitalize() for c in df.columns]
        
        # 處理時間欄位
        df['Time'] = pd.to_datetime(df['Time'])
        df.set_index('Time', inplace=True) # 設為索引方便計算
        
    except FileNotFoundError:
        print(f"❌ 找不到檔案: {CSV_FILE_PATH}")
        print("💡 提示: 如果是剛跑 main.py，可能資料還沒寫入 (要等 1 分鐘)")
        return
    except Exception as e:
        print(f"❌ 讀取錯誤: {e}")
        return

    print(f"📊 原始資料: {len(df)} 筆")

    # 2. 動態計算指標
    df = calculate_indicators(df)
    
    # 去除因為計算指標產生的 NaN (例如前 20 筆算不出 MA20)
    df.dropna(inplace=True)
    print(f"✅ 指標計算完成，有效資料: {len(df)} 筆")

    # 3. 初始化模擬環境
    mock_bot = MockBot()
    fake_api = MockShioaji()
    
    # 使用 MockAPI 的 Trader
    real_trader = Trader(api=fake_api)
    
    # 初始化策略
    strategy = Strategy(bot=mock_bot, trader=real_trader)
    
    # 4. 開始回放 (逐 K 線模擬)
    print("▶️ 開始回測...")
    start_time = time.time()
    
    for current_time, row in df.iterrows():
        # 建構 Bar 資料 (符合 Strategy.on_bar 的格式)
        bar = {
            'dt': current_time.to_pydatetime(),
            'open': float(row['Open']),
            'high': float(row['High']),
            'low': float(row['Low']),
            'close': float(row['Close']),
            'volume': int(row['Volume']),
            'ma5': float(row['MA5']),   # 這裡是用算的！
            'ma20': float(row['MA20'])  # 這裡是用算的！
        }
        
        # 呼叫策略
        strategy.on_bar(bar)

    end_time = time.time()

    # 5. 顯示績效
    # 呼叫同一支檔案裡的績效計算函式 (如果你有把 calculate_performance 貼進來的話)
    # calculate_performance(strategy) 
    
    # 這裡簡單印出最終結果
    print(f"\n⚡ 回測耗時: {end_time - start_time:.2f} 秒")
    print("════════════════════════════════════")
    print(f"💰 最終策略損益: {strategy.total_profit:.0f} 點")
    print(f"🎲 交易次數: {strategy.trade_count}")
    print("════════════════════════════════════")
    print(f"📝 詳細交易紀錄已存至: {strategy.file_path}")

if __name__ == "__main__":
    # 強制開啟下單邏輯測試
    Settings.DRY_RUN = False 
    run_backtest()
    Settings.DRY_RUN = True