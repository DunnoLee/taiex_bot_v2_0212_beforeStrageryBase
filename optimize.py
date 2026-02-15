import pandas as pd
import numpy as np
from datetime import datetime

# ================= 設定區 =================
DATA_PATH = "data/history/TMF202602_1min_history.csv"  # 你的 K 線路徑
FRICTION_COST = 5.0        # 設定更嚴格一點：每趟進出扣 2 點 (手續費 + 滑價)
SLOPE_PERIOD = 0           # 用過去 5 分鐘的 MA 變化來判斷斜率

def run_backtest_with_filter(df, short_ma, long_ma, slope_p):
    """
    核心回測邏輯：具備長均線斜率濾網
    """
    work_df = df.copy()
    
    # 計算指標
    work_df['ma_s'] = work_df['Close'].rolling(window=short_ma).mean()
    work_df['ma_l'] = work_df['Close'].rolling(window=long_ma).mean()
    
    # 計算長均線斜率 (當前 MA_L 減掉 N 分鐘前的 MA_L)
    work_df['ma_l_slope'] = work_df['ma_l'] - work_df['ma_l'].shift(slope_p)
    
    # 紀錄前一根 K 線狀態 (避免偷看未來)
    work_df['prev_ma_s'] = work_df['ma_s'].shift(1)
    work_df['prev_ma_l'] = work_df['ma_l'].shift(1)
    
    # 移除空值
    work_df.dropna(subset=['prev_ma_s', 'prev_ma_l', 'ma_l_slope'], inplace=True)
    
    position = 0      # 1:多單, -1:空單, 0:空手
    entry_price = 0
    total_profit = 0
    trade_count = 0
    
    for _, row in work_df.iterrows():
        # --- 黃金交叉邏輯 ---
        if row['prev_ma_s'] < row['prev_ma_l'] and row['ma_s'] > row['ma_l']:
            # 💡 修正：如果 SLOPE_PERIOD 為 0，或者是斜率大於 0 才進場
            if SLOPE_PERIOD == 0 or row['ma_l_slope'] > 0:
                if position == -1: 
                    total_profit += (entry_price - row['Close']) - FRICTION_COST
                    trade_count += 1
                entry_price = row['Close']
                position = 1
                
        # --- 死亡交叉邏輯 ---
        elif row['prev_ma_s'] > row['prev_ma_l'] and row['ma_s'] < row['ma_l']:
            # 💡 修正：如果 SLOPE_PERIOD 為 0，或者是斜率小於 0 才進場
            if SLOPE_PERIOD == 0 or row['ma_l_slope'] < 0:
                if position == 1: 
                    total_profit += (row['Close'] - entry_price) - FRICTION_COST
                    trade_count += 1
                entry_price = row['Close']
                position = -1
                
    return total_profit, trade_count

# ================= 主程式 =================
if __name__ == "__main__":
    print(f"🚀 [優化器] 開始參數掃描...")
    print(f"📊 數據源: {DATA_PATH}")
    print(f"⛽ 摩擦成本: {FRICTION_COST} 點 | 斜率參考: {SLOPE_PERIOD} 分鐘\n")

    try:
        raw_df = pd.read_csv(DATA_PATH)
    except FileNotFoundError:
        print(f"❌ 找不到檔案: {DATA_PATH}，請確認路徑是否正確。")
        exit()

    all_results = []
    
    # 設定掃描範圍 (你可以根據需求調整)
    short_ma_list = [5, 10, 15, 20, 30]
    long_ma_list  = [60, 80, 100, 120, 150, 200]
    
    total_iterations = len(short_ma_list) * len(long_ma_list)
    current_it = 0

    for s in short_ma_list:
        for l in long_ma_list:
            current_it += 1
            if s >= l: continue
            
            p, c = run_backtest_with_filter(raw_df, s, l, SLOPE_PERIOD)
            
            expectancy = round(p / c, 2) if c > 0 else 0
            
            all_results.append({
                '組合(S/L)': f"{s}/{l}",
                '總損益': round(p, 1),
                '交易次數': c,
                '期望值': expectancy
            })
            
            if current_it % 5 == 0:
                print(f"⏳ 已完成 {current_it}/{total_iterations} 組...")

    # 轉換成 DataFrame 方便展示
    res_df = pd.DataFrame(all_results)
    
    # 依照總損益排序
    res_df = res_df.sort_values(by='總損益', ascending=False)

    print("\n" + "="*60)
    print("🏆 參數優化排行榜 (斜率濾網版)")
    print("="*60)
    print(res_df.head(15).to_string(index=False))